package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const maxBody = 16 * 1024

type API struct {
	store  LogStore
	sender Sender
	logger *log.Logger
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	// 1. Endpoint /api/notify
	if path == "/api/notify" {
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", "POST, OPTIONS")
			failure(w, http.StatusMethodNotAllowed, "Phương thức không được hỗ trợ")
			return
		}
		a.notify(w, r)
		return
	}

	// 2. Endpoint /api/notify/logs
	if path == "/api/notify/logs" {
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		switch r.Method {
		case http.MethodGet:
			a.logs(w, r)
		case http.MethodPost:
			a.createLog(w, r)
		default:
			w.Header().Set("Allow", "GET, POST, OPTIONS")
			failure(w, http.StatusMethodNotAllowed, "Phương thức không được hỗ trợ")
		}
		return
	}

	// 3. Endpoint /api/notify/logs/{id}
	if strings.HasPrefix(path, "/api/notify/logs/") {
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		idStr := strings.TrimPrefix(path, "/api/notify/logs/")
		// Đảm bảo không chứa dấu / phụ
		if strings.Contains(idStr, "/") {
			failure(w, http.StatusNotFound, "Không tìm thấy endpoint")
			return
		}

		id, err := strconv.ParseInt(idStr, 10, 64)
		if err != nil || id <= 0 {
			failure(w, http.StatusBadRequest, "ID phải là số nguyên dương")
			return
		}

		switch r.Method {
		case http.MethodGet:
			a.getLog(w, r, id)
		case http.MethodPut, http.MethodPatch:
			a.updateLog(w, r, id)
		case http.MethodDelete:
			a.deleteLog(w, r, id)
		default:
			w.Header().Set("Allow", "GET, PUT, PATCH, DELETE, OPTIONS")
			failure(w, http.StatusMethodNotAllowed, "Phương thức không được hỗ trợ")
		}
		return
	}

	failure(w, http.StatusNotFound, "Không tìm thấy endpoint")
}

func (a *API) notify(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBody)
	body, err := io.ReadAll(r.Body)
	if err != nil {
		var large *http.MaxBytesError
		if errors.As(err, &large) {
			failure(w, http.StatusRequestEntityTooLarge, "Body vượt quá 16 KiB")
		} else {
			failure(w, http.StatusBadRequest, "Không thể đọc body")
		}
		return
	}
	if !utf8.Valid(body) || !strings.HasPrefix(strings.TrimSpace(string(body)), "{") {
		failure(w, http.StatusBadRequest, "Body phải là một JSON object")
		return
	}
	var input NotifyRequest
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&input); err != nil {
		failure(w, http.StatusBadRequest, "JSON không hợp lệ hoặc có trường không được hỗ trợ")
		return
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF {
		failure(w, http.StatusBadRequest, "Body chỉ được chứa một JSON object")
		return
	}
	input.Username = strings.TrimSpace(input.Username)
	input.Channel = strings.ToUpper(strings.TrimSpace(input.Channel))
	if input.BookingID <= 0 || input.BookingID > 2147483647 {
		failure(w, http.StatusBadRequest, "bookingId phải là số nguyên dương trong phạm vi INT MySQL")
		return
	}
	if input.Username == "" || utf8.RuneCountInString(input.Username) > 50 {
		failure(w, http.StatusBadRequest, "username phải có từ 1 đến 50 ký tự Unicode")
		return
	}
	if input.Channel != "EMAIL" && input.Channel != "SMS" {
		failure(w, http.StatusBadRequest, "channel phải là EMAIL hoặc SMS")
		return
	}
	n := NotificationLog{
		BookingID: input.BookingID,
		Username:  input.Username,
		Channel:   input.Channel,
		Message:   composeMessage(input.BookingID),
		SentAt:    time.Now().UTC().Truncate(time.Second),
	}
	if err = a.sender.Send(r.Context(), n); err != nil {
		a.logger.Print("Gửi giả lập thất bại")
		failure(w, http.StatusInternalServerError, "Không thể xử lý thông báo")
		return
	}
	id, err := a.store.Insert(r.Context(), n)
	if err != nil {
		a.logger.Print("Lưu nhật ký thất bại")
		failure(w, http.StatusInternalServerError, "Không thể lưu nhật ký thông báo")
		return
	}
	success(w, NotifyResponse{id, n.BookingID, n.Username, n.Channel, "SIMULATED", n.Message, n.SentAt})
}

func (a *API) logs(w http.ResponseWriter, r *http.Request) {
	logs, err := a.store.List(r.Context())
	if err != nil {
		a.logger.Print("Đọc nhật ký thất bại")
		failure(w, http.StatusInternalServerError, "Không thể đọc nhật ký thông báo")
		return
	}
	if logs == nil {
		logs = make([]NotificationLog, 0)
	}

	// Hỗ trợ lọc theo query params nếu có (?bookingId=, ?username=, ?channel=)
	q := r.URL.Query()
	bookingIdStr := q.Get("bookingId")
	username := strings.TrimSpace(q.Get("username"))
	channel := strings.ToUpper(strings.TrimSpace(q.Get("channel")))

	if bookingIdStr != "" || username != "" || channel != "" {
		filtered := make([]NotificationLog, 0)
		var bId int64
		if bookingIdStr != "" {
			bId, _ = strconv.ParseInt(bookingIdStr, 10, 64)
		}
		for _, l := range logs {
			if bId > 0 && l.BookingID != bId {
				continue
			}
			if username != "" && !strings.EqualFold(l.Username, username) {
				continue
			}
			if channel != "" && l.Channel != channel {
				continue
			}
			filtered = append(filtered, l)
		}
		logs = filtered
	}

	success(w, logs)
}

func (a *API) getLog(w http.ResponseWriter, r *http.Request, id int64) {
	logItem, err := a.store.Get(r.Context(), id)
	if err != nil {
		a.logger.Printf("Lỗi truy vấn nhật ký #%d: %v", id, err)
		failure(w, http.StatusInternalServerError, "Không thể truy vấn nhật ký thông báo")
		return
	}
	if logItem == nil {
		failure(w, http.StatusNotFound, "Không tìm thấy nhật ký thông báo")
		return
	}
	success(w, logItem)
}

func (a *API) createLog(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBody)
	body, err := io.ReadAll(r.Body)
	if err != nil {
		failure(w, http.StatusBadRequest, "Không thể đọc body")
		return
	}
	var input CreateLogRequest
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&input); err != nil {
		failure(w, http.StatusBadRequest, "JSON không hợp lệ hoặc có trường không được hỗ trợ")
		return
	}

	input.Username = strings.TrimSpace(input.Username)
	input.Channel = strings.ToUpper(strings.TrimSpace(input.Channel))
	input.Message = strings.TrimSpace(input.Message)

	if input.BookingID <= 0 || input.BookingID > 2147483647 {
		failure(w, http.StatusBadRequest, "bookingId phải là số nguyên dương trong phạm vi INT MySQL")
		return
	}
	if input.Username == "" || utf8.RuneCountInString(input.Username) > 50 {
		failure(w, http.StatusBadRequest, "username phải có từ 1 đến 50 ký tự Unicode")
		return
	}
	if input.Channel != "EMAIL" && input.Channel != "SMS" {
		failure(w, http.StatusBadRequest, "channel phải là EMAIL hoặc SMS")
		return
	}
	if input.Message == "" {
		input.Message = composeMessage(input.BookingID)
	} else if utf8.RuneCountInString(input.Message) > 255 {
		failure(w, http.StatusBadRequest, "message tối đa 255 ký tự")
		return
	}

	n := NotificationLog{
		BookingID: input.BookingID,
		Username:  input.Username,
		Channel:   input.Channel,
		Message:   input.Message,
		SentAt:    time.Now().UTC().Truncate(time.Second),
	}

	id, err := a.store.Insert(r.Context(), n)
	if err != nil {
		a.logger.Printf("Tạo nhật ký thất bại: %v", err)
		failure(w, http.StatusInternalServerError, "Không thể lưu nhật ký thông báo")
		return
	}
	n.ID = id
	writeJSON(w, http.StatusCreated, struct {
		Status string          `json:"status"`
		Data   NotificationLog `json:"data"`
	}{"success", n})
}

func (a *API) updateLog(w http.ResponseWriter, r *http.Request, id int64) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBody)
	body, err := io.ReadAll(r.Body)
	if err != nil {
		failure(w, http.StatusBadRequest, "Không thể đọc body")
		return
	}
	var input UpdateLogRequest
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&input); err != nil {
		failure(w, http.StatusBadRequest, "JSON không hợp lệ hoặc có trường không được hỗ trợ")
		return
	}

	if input.Username != nil {
		trimmed := strings.TrimSpace(*input.Username)
		if trimmed == "" || utf8.RuneCountInString(trimmed) > 50 {
			failure(w, http.StatusBadRequest, "username phải có từ 1 đến 50 ký tự Unicode")
			return
		}
		input.Username = &trimmed
	}

	if input.Channel != nil {
		upper := strings.ToUpper(strings.TrimSpace(*input.Channel))
		if upper != "EMAIL" && upper != "SMS" {
			failure(w, http.StatusBadRequest, "channel phải là EMAIL hoặc SMS")
			return
		}
		input.Channel = &upper
	}

	if input.BookingID != nil {
		if *input.BookingID <= 0 || *input.BookingID > 2147483647 {
			failure(w, http.StatusBadRequest, "bookingId phải là số nguyên dương trong phạm vi INT MySQL")
			return
		}
	}

	if input.Message != nil {
		trimmed := strings.TrimSpace(*input.Message)
		if trimmed == "" || utf8.RuneCountInString(trimmed) > 255 {
			failure(w, http.StatusBadRequest, "message không được rỗng và tối đa 255 ký tự")
			return
		}
		input.Message = &trimmed
	}

	updated, err := a.store.Update(r.Context(), id, input)
	if err != nil {
		a.logger.Printf("Cập nhật nhật ký #%d thất bại: %v", id, err)
		failure(w, http.StatusInternalServerError, "Không thể cập nhật nhật ký thông báo")
		return
	}
	if updated == nil {
		failure(w, http.StatusNotFound, "Không tìm thấy nhật ký thông báo để cập nhật")
		return
	}
	success(w, updated)
}

func (a *API) deleteLog(w http.ResponseWriter, r *http.Request, id int64) {
	err := a.store.Delete(r.Context(), id)
	if errors.Is(err, sql.ErrNoRows) {
		failure(w, http.StatusNotFound, "Không tìm thấy nhật ký thông báo để xóa")
		return
	}
	if err != nil {
		a.logger.Printf("Xóa nhật ký #%d thất bại: %v", id, err)
		failure(w, http.StatusInternalServerError, "Không thể xóa nhật ký thông báo")
		return
	}
	success(w, map[string]any{
		"id":      id,
		"deleted": true,
		"message": "Đã xóa nhật ký thông báo thành công",
	})
}

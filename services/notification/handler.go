package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
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
	var method string
	switch r.URL.Path {
	case "/api/notify":
		method = "POST"
	case "/api/notify/logs":
		method = "GET"
	default:
		failure(w, 404, "Không tìm thấy endpoint")
		return
	}
	if r.Method == "OPTIONS" {
		w.WriteHeader(204)
		return
	}
	if r.Method != method {
		w.Header().Set("Allow", method+", OPTIONS")
		failure(w, 405, "Phương thức không được hỗ trợ")
		return
	}
	if method == "GET" {
		a.logs(w, r)
		return
	}
	a.notify(w, r)
}
func (a *API) notify(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBody)
	body, err := io.ReadAll(r.Body)
	if err != nil {
		var large *http.MaxBytesError
		if errors.As(err, &large) {
			failure(w, 413, "Body vượt quá 16 KiB")
		} else {
			failure(w, 400, "Không thể đọc body")
		}
		return
	}
	if !utf8.Valid(body) || !strings.HasPrefix(strings.TrimSpace(string(body)), "{") {
		failure(w, 400, "Body phải là một JSON object")
		return
	}
	var input NotifyRequest
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&input); err != nil {
		failure(w, 400, "JSON không hợp lệ hoặc có trường không được hỗ trợ")
		return
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF {
		failure(w, 400, "Body chỉ được chứa một JSON object")
		return
	}
	input.Username = strings.TrimSpace(input.Username)
	input.Channel = strings.ToUpper(strings.TrimSpace(input.Channel))
	if input.BookingID <= 0 || input.BookingID > 2147483647 {
		failure(w, 400, "bookingId phải là số nguyên dương trong phạm vi INT MySQL")
		return
	}
	if input.Username == "" || utf8.RuneCountInString(input.Username) > 50 {
		failure(w, 400, "username phải có từ 1 đến 50 ký tự Unicode")
		return
	}
	if input.Channel != "EMAIL" && input.Channel != "SMS" {
		failure(w, 400, "channel phải là EMAIL hoặc SMS")
		return
	}
	n := NotificationLog{BookingID: input.BookingID, Username: input.Username, Channel: input.Channel, Message: composeMessage(input.BookingID), SentAt: time.Now().UTC().Truncate(time.Second)}
	if err = a.sender.Send(r.Context(), n); err != nil {
		a.logger.Print("Gửi giả lập thất bại")
		failure(w, 500, "Không thể xử lý thông báo")
		return
	}
	id, err := a.store.Insert(r.Context(), n)
	if err != nil {
		a.logger.Print("Lưu nhật ký thất bại")
		failure(w, 500, "Không thể lưu nhật ký thông báo")
		return
	}
	success(w, NotifyResponse{id, n.BookingID, n.Username, n.Channel, "SIMULATED", n.Message, n.SentAt})
}
func (a *API) logs(w http.ResponseWriter, r *http.Request) {
	logs, err := a.store.List(r.Context())
	if err != nil {
		a.logger.Print("Đọc nhật ký thất bại")
		failure(w, 500, "Không thể đọc nhật ký thông báo")
		return
	}
	if logs == nil {
		logs = make([]NotificationLog, 0)
	}
	success(w, logs)
}

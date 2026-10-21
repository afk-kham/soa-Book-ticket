package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type fakeStore struct {
	items   []NotificationLog
	err     error
	inserts int
}

func (s *fakeStore) Insert(_ context.Context, n NotificationLog) (int64, error) {
	s.inserts++
	n.ID = int64(len(s.items) + 1)
	s.items = append(s.items, n)
	return n.ID, s.err
}

func (s *fakeStore) List(context.Context) ([]NotificationLog, error) {
	return s.items, s.err
}

func (s *fakeStore) Get(_ context.Context, id int64) (*NotificationLog, error) {
	if s.err != nil {
		return nil, s.err
	}
	for _, item := range s.items {
		if item.ID == id {
			return &item, nil
		}
	}
	return nil, nil
}

func (s *fakeStore) Update(_ context.Context, id int64, req UpdateLogRequest) (*NotificationLog, error) {
	if s.err != nil {
		return nil, s.err
	}
	for i, item := range s.items {
		if item.ID == id {
			if req.Username != nil {
				item.Username = *req.Username
			}
			if req.Channel != nil {
				item.Channel = *req.Channel
			}
			if req.Message != nil {
				item.Message = *req.Message
			}
			if req.BookingID != nil {
				item.BookingID = *req.BookingID
			}
			s.items[i] = item
			return &item, nil
		}
	}
	return nil, nil
}

func (s *fakeStore) Delete(_ context.Context, id int64) error {
	if s.err != nil {
		return s.err
	}
	for i, item := range s.items {
		if item.ID == id {
			s.items = append(s.items[:i], s.items[i+1:]...)
			return nil
		}
	}
	return sql.ErrNoRows
}

type fakeSender struct {
	calls int
	err   error
}

func (s *fakeSender) Send(context.Context, NotificationLog) error {
	s.calls++
	return s.err
}

func testAPI(s *fakeStore, sender *fakeSender) http.Handler {
	logger := log.New(io.Discard, "", 0)
	return middleware(&API{s, sender, logger}, logger)
}

func request(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	h.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	return w
}

func checkCORS(t *testing.T, w *httptest.ResponseRecorder) {
	t.Helper()
	for key, value := range map[string]string{
		"Access-Control-Allow-Origin":  "*",
		"Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
		"Access-Control-Allow-Headers": "Content-Type, Authorization",
	} {
		if w.Header().Get(key) != value {
			t.Errorf("%s expected %s, got %s", key, value, w.Header().Get(key))
		}
	}
	if w.Header().Get("Access-Control-Allow-Credentials") != "" {
		t.Fatal("credentials")
	}
}

func TestNotifyValid(t *testing.T) {
	s := &fakeStore{}
	sender := &fakeSender{}
	w := request(testAPI(s, sender), "POST", "/api/notify", `{"username":"  người dùng  ","bookingId":3,"channel":" email "}`)
	var res struct {
		Status string
		Data   NotifyResponse
	}
	if err := json.Unmarshal(w.Body.Bytes(), &res); err != nil {
		t.Fatal(err)
	}
	if w.Code != 200 || res.Status != "success" || res.Data.NotificationID != 1 || res.Data.BookingID != 3 || res.Data.Username != "người dùng" || res.Data.Channel != "EMAIL" || res.Data.DeliveryStatus != "SIMULATED" || res.Data.Message != "Đặt vé thành công cho đơn #3" || res.Data.SentAt.IsZero() || sender.calls != 1 || s.inserts != 1 {
		t.Fatalf("unexpected: %d %s", w.Code, w.Body.String())
	}
	if res.Data.SentAt.Location() != time.UTC || res.Data.SentAt.Nanosecond() != 0 {
		t.Fatal("expected UTC seconds")
	}
}

func TestInvalidBodies(t *testing.T) {
	cases := []struct {
		name, body string
		code       int
	}{
		{"empty", "", 400}, {"null", "null", 400}, {"array", "[]", 400}, {"broken", "{", 400}, {"trailing", `{"username":"u","bookingId":1,"channel":"EMAIL"} {}`, 400},
		{"zero", `{"username":"u","bookingId":0,"channel":"EMAIL"}`, 400}, {"negative", `{"username":"u","bookingId":-1,"channel":"EMAIL"}`, 400},
		{"fraction", `{"username":"u","bookingId":1.5,"channel":"EMAIL"}`, 400}, {"overflow", `{"username":"u","bookingId":2147483648,"channel":"EMAIL"}`, 400},
		{"blank", `{"username":"  ","bookingId":1,"channel":"EMAIL"}`, 400}, {"long", `{"username":"` + strings.Repeat("ệ", 51) + `","bookingId":1,"channel":"EMAIL"}`, 400},
		{"channel", `{"username":"u","bookingId":1,"channel":"PUSH"}`, 400}, {"message", `{"username":"u","bookingId":1,"channel":"EMAIL","message":"custom"}`, 400},
		{"oversized", strings.Repeat(" ", maxBody+1), 413}, {"invalidUTF8", "{\"username\":\"" + string([]byte{255}) + "\"}", 400},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := &fakeStore{}
			sender := &fakeSender{}
			w := request(testAPI(s, sender), "POST", "/api/notify", tc.body)
			if w.Code != tc.code || !strings.Contains(w.Body.String(), `"status":"error"`) || s.inserts != 0 || sender.calls != 0 {
				t.Fatalf("%d %s", w.Code, w.Body.String())
			}
			checkCORS(t, w)
		})
	}
}

func TestRoutes(t *testing.T) {
	for _, tc := range []struct {
		method, path string
		code         int
		allow        string
	}{
		{"GET", "/api/notify", 405, "POST, OPTIONS"},
		{"HEAD", "/api/notify/logs", 405, "GET, POST, OPTIONS"},
		{"GET", "/missing", 404, ""},
		{"POST", "/api/notify/", 404, ""},
		{"GET", "/api/notify/logs/other", 400, ""},
		{"OPTIONS", "/missing", 404, ""},
		{"OPTIONS", "/api/notify", 204, ""},
		{"OPTIONS", "/api/notify/logs", 204, ""},
		{"OPTIONS", "/api/notify/logs/1", 204, ""},
	} {
		t.Run(tc.method+tc.path, func(t *testing.T) {
			w := request(testAPI(&fakeStore{}, &fakeSender{}), tc.method, tc.path, "")
			if w.Code != tc.code || (tc.allow != "" && w.Header().Get("Allow") != tc.allow) {
				t.Fatalf("%d %s (allow: %s)", w.Code, w.Body.String(), w.Header().Get("Allow"))
			}
			checkCORS(t, w)
			if tc.code == 204 {
				if w.Body.Len() != 0 {
					t.Fatal("OPTIONS body")
				}
			} else if w.Header().Get("Content-Type") != "application/json; charset=utf-8" {
				t.Fatal("content type")
			}
		})
	}
}

func TestCRUDLogs(t *testing.T) {
	s := &fakeStore{
		items: []NotificationLog{
			{ID: 1, BookingID: 10, Username: "user1", Channel: "EMAIL", Message: "Msg 1", SentAt: time.Now().UTC()},
		},
	}
	sender := &fakeSender{}
	api := testAPI(s, sender)

	// 1. GET /api/notify/logs
	w := request(api, "GET", "/api/notify/logs", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"username":"user1"`) {
		t.Fatalf("List logs failed: %d %s", w.Code, w.Body.String())
	}

	// 2. GET /api/notify/logs/1
	w = request(api, "GET", "/api/notify/logs/1", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"id":1`) {
		t.Fatalf("Get log 1 failed: %d %s", w.Code, w.Body.String())
	}

	// 3. GET /api/notify/logs/999 (Not found)
	w = request(api, "GET", "/api/notify/logs/999", "")
	if w.Code != 404 {
		t.Fatalf("Expected 404 for missing log: %d %s", w.Code, w.Body.String())
	}

	// 4. POST /api/notify/logs (Create log directly)
	w = request(api, "POST", "/api/notify/logs", `{"username":"user2","bookingId":20,"channel":"SMS","message":"Xin chao"}`)
	if w.Code != 201 || !strings.Contains(w.Body.String(), `"username":"user2"`) {
		t.Fatalf("Create log failed: %d %s", w.Code, w.Body.String())
	}

	// 5. PUT /api/notify/logs/1 (Update log)
	w = request(api, "PUT", "/api/notify/logs/1", `{"message":"Updated message","channel":"SMS"}`)
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"message":"Updated message"`) || !strings.Contains(w.Body.String(), `"channel":"SMS"`) {
		t.Fatalf("Update log failed: %d %s", w.Code, w.Body.String())
	}

	// 6. DELETE /api/notify/logs/1 (Delete log)
	w = request(api, "DELETE", "/api/notify/logs/1", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"deleted":true`) {
		t.Fatalf("Delete log failed: %d %s", w.Code, w.Body.String())
	}

	// 7. GET /api/notify/logs/1 after delete -> 404
	w = request(api, "GET", "/api/notify/logs/1", "")
	if w.Code != 404 {
		t.Fatalf("Expected 404 after delete: %d %s", w.Code, w.Body.String())
	}
}

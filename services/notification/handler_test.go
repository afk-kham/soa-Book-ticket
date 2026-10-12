package main

import (
	"context"
	"encoding/json"
	"errors"
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
	s.items = append(s.items, n)
	return 2, s.err
}
func (s *fakeStore) List(context.Context) ([]NotificationLog, error) { return s.items, s.err }

type fakeSender struct {
	calls int
	err   error
}

func (s *fakeSender) Send(context.Context, NotificationLog) error { s.calls++; return s.err }
func testAPI(s *fakeStore, sender *fakeSender) http.Handler {
	logger := log.New(io.Discard, "", 0)
	return middleware(&API{s, sender, logger}, logger)
}
func request(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	h.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	return w
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
	if w.Code != 200 || res.Status != "success" || res.Data.NotificationID != 2 || res.Data.BookingID != 3 || res.Data.Username != "người dùng" || res.Data.Channel != "EMAIL" || res.Data.DeliveryStatus != "SIMULATED" || res.Data.Message != "Đặt vé thành công cho đơn #3" || res.Data.SentAt.IsZero() || sender.calls != 1 || s.inserts != 1 {
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
func checkCORS(t *testing.T, w *httptest.ResponseRecorder) {
	t.Helper()
	for key, value := range map[string]string{"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization"} {
		if w.Header().Get(key) != value {
			t.Errorf("%s", key)
		}
	}
	if w.Header().Get("Access-Control-Allow-Credentials") != "" {
		t.Fatal("credentials")
	}
}
func TestRoutes(t *testing.T) {
	for _, tc := range []struct {
		method, path string
		code         int
		allow        string
	}{
		{"GET", "/api/notify", 405, "POST, OPTIONS"}, {"POST", "/api/notify/logs", 405, "GET, OPTIONS"}, {"HEAD", "/api/notify/logs", 405, "GET, OPTIONS"},
		{"GET", "/missing", 404, ""}, {"POST", "/api/notify/", 404, ""}, {"GET", "/api/notify/logs/other", 404, ""}, {"OPTIONS", "/missing", 404, ""},
		{"OPTIONS", "/api/notify", 204, ""}, {"OPTIONS", "/api/notify/logs", 204, ""},
	} {
		t.Run(tc.method+tc.path, func(t *testing.T) {
			w := request(testAPI(&fakeStore{}, &fakeSender{}), tc.method, tc.path, "")
			if w.Code != tc.code || w.Header().Get("Allow") != tc.allow {
				t.Fatalf("%d %s", w.Code, w.Body.String())
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
func TestLogs(t *testing.T) {
	for _, items := range [][]NotificationLog{nil, {{ID: 1, BookingID: 1, Username: "user1", Channel: "EMAIL", Message: composeMessage(1), SentAt: time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)}}} {
		w := request(testAPI(&fakeStore{items: items}, &fakeSender{}), "GET", "/api/notify/logs", "")
		checkCORS(t, w)
		if w.Code != 200 {
			t.Fatal(w.Body.String())
		}
		if items == nil && !strings.Contains(w.Body.String(), `"data":[]`) {
			t.Fatal(w.Body.String())
		}
		var res struct{ Data []NotificationLog }
		if err := json.Unmarshal(w.Body.Bytes(), &res); err != nil {
			t.Fatal(err)
		}
		if len(res.Data) != len(items) {
			t.Fatal("log count")
		}
	}
}
func TestFailures(t *testing.T) {
	for _, method := range []string{"GET", "POST"} {
		s := &fakeStore{err: errors.New("secret database error")}
		path := "/api/notify"
		if method == "GET" {
			path += "/logs"
		}
		w := request(testAPI(s, &fakeSender{}), method, path, `{"username":"u","bookingId":1,"channel":"SMS"}`)
		if w.Code != 500 || strings.Contains(w.Body.String(), "success") || strings.Contains(w.Body.String(), "secret") {
			t.Fatal(w.Body.String())
		}
		checkCORS(t, w)
	}
	s := &fakeStore{}
	w := request(testAPI(s, &fakeSender{err: errors.New("failed")}), "POST", "/api/notify", `{"username":"u","bookingId":1,"channel":"SMS"}`)
	if w.Code != 500 || s.inserts != 0 {
		t.Fatal("sender failure must stop insert")
	}
}

package main

import (
	"encoding/json"
	"net/http"
)

func writeJSON(w http.ResponseWriter, code int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(value)
}
func success(w http.ResponseWriter, data any) {
	writeJSON(w, 200, struct {
		Status string `json:"status"`
		Data   any    `json:"data"`
	}{"success", data})
}

// errorCode ánh xạ mã HTTP sang mã lỗi máy đọc được, dùng chung cho cả 6 service (API_CONTRACT.md).
func errorCode(status int) string {
	switch status {
	case 400:
		return "VALIDATION_ERROR"
	case 404:
		return "NOT_FOUND"
	case 405:
		return "METHOD_NOT_ALLOWED"
	case 413:
		return "PAYLOAD_TOO_LARGE"
	}
	if status >= 500 {
		return "INTERNAL_ERROR"
	}
	return "ERROR"
}
func failure(w http.ResponseWriter, code int, message string) {
	writeJSON(w, code, struct {
		Status  string `json:"status"`
		Code    string `json:"code"`
		Message string `json:"message"`
	}{"error", errorCode(code), message})
}

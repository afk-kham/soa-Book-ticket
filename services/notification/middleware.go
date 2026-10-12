package main

import (
	"log"
	"net/http"
	"time"
)

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(code int) {
	if w.status == 0 {
		w.status = code
		w.ResponseWriter.WriteHeader(code)
	}
}
func (w *statusWriter) Write(b []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(200)
	}
	return w.ResponseWriter.Write(b)
}
func middleware(next http.Handler, logger *log.Logger) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w}
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		defer func() {
			if recover() != nil {
				if sw.status == 0 {
					failure(sw, 500, "Lỗi nội bộ")
				}
				logger.Print("HTTP handler panic")
			}
			if sw.status == 0 {
				sw.status = 200
			}
			logger.Printf("method=%s path=%q status=%d duration=%s", r.Method, r.URL.Path, sw.status, time.Since(start))
		}()
		next.ServeHTTP(sw, r)
	})
}

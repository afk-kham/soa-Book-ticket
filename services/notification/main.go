package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"
)

func run() error {
	c, err := loadConfig()
	if err != nil {
		return err
	}
	db, err := openDB(c)
	if err != nil {
		return errors.New("không thể kết nối MySQL: kiểm tra DB_HOST/DB_PORT/DB_NAME, tài khoản và dịch vụ DB")
	}
	defer db.Close()
	logger := log.New(os.Stdout, "notification ", log.LstdFlags)
	api := &API{&MySQLStore{db}, ConsoleSender{logger}, logger}
	server := &http.Server{Addr: c.HTTPAddr, Handler: middleware(api, logger), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	done := make(chan error, 1)
	go func() { done <- server.ListenAndServe() }()
	logger.Printf("API lắng nghe %s", c.HTTPAddr)
	select {
	case err := <-done:
		if !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	case <-ctx.Done():
		shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdown); err != nil {
			_ = server.Close()
			return err
		}
		if err := <-done; !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	}
	return nil
}
func main() {
	if err := run(); err != nil {
		log.Print(err)
		os.Exit(1)
	}
}

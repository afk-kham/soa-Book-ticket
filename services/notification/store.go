package main

import (
	"context"
	"database/sql"
	"github.com/go-sql-driver/mysql"
	"net"
	"time"
)

const dbTimeout = 5 * time.Second

type LogStore interface {
	Insert(context.Context, NotificationLog) (int64, error)
	List(context.Context) ([]NotificationLog, error)
}
type MySQLStore struct{ db *sql.DB }

func openDB(c Config) (*sql.DB, error) {
	cfg := mysql.NewConfig()
	cfg.User, cfg.Passwd, cfg.Net, cfg.Addr, cfg.DBName = c.DBUser, c.DBPassword, "tcp", net.JoinHostPort(c.DBHost, c.DBPort), c.DBName
	cfg.ParseTime, cfg.Loc = true, time.UTC
	cfg.Params = map[string]string{"charset": "utf8mb4", "time_zone": "'+00:00'"}
	cfg.Timeout, cfg.ReadTimeout, cfg.WriteTimeout = dbTimeout, dbTimeout, dbTimeout
	db, err := sql.Open("mysql", cfg.FormatDSN())
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(3 * time.Minute)
	ctx, cancel := context.WithTimeout(context.Background(), dbTimeout)
	defer cancel()
	if err = db.PingContext(ctx); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}
func (s *MySQLStore) Insert(ctx context.Context, n NotificationLog) (int64, error) {
	ctx, cancel := context.WithTimeout(ctx, dbTimeout)
	defer cancel()
	result, err := s.db.ExecContext(ctx, "INSERT INTO notification_logs (booking_id,username,channel,message,sent_at) VALUES (?,?,?,?,?)", n.BookingID, n.Username, n.Channel, n.Message, n.SentAt)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}
func (s *MySQLStore) List(ctx context.Context) ([]NotificationLog, error) {
	ctx, cancel := context.WithTimeout(ctx, dbTimeout)
	defer cancel()
	rows, err := s.db.QueryContext(ctx, "SELECT id,booking_id,username,channel,message,sent_at FROM notification_logs ORDER BY sent_at DESC,id DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	logs := make([]NotificationLog, 0)
	for rows.Next() {
		var n NotificationLog
		if err := rows.Scan(&n.ID, &n.BookingID, &n.Username, &n.Channel, &n.Message, &n.SentAt); err != nil {
			return nil, err
		}
		logs = append(logs, n)
	}
	return logs, rows.Err()
}

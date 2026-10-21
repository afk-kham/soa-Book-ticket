package main

import (
	"context"
	"database/sql"
	"errors"
	"net"
	"time"

	"github.com/go-sql-driver/mysql"
)

const dbTimeout = 5 * time.Second

type LogStore interface {
	Insert(context.Context, NotificationLog) (int64, error)
	List(context.Context) ([]NotificationLog, error)
	Get(context.Context, int64) (*NotificationLog, error)
	Update(context.Context, int64, UpdateLogRequest) (*NotificationLog, error)
	Delete(context.Context, int64) error
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
	result, err := s.db.ExecContext(ctx, "INSERT INTO notification_logs (booking_id,username,channel,message,sent_at) VALUES (?,?,?,?,?)",
		n.BookingID, n.Username, n.Channel, n.Message, n.SentAt)
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

func (s *MySQLStore) Get(ctx context.Context, id int64) (*NotificationLog, error) {
	ctx, cancel := context.WithTimeout(ctx, dbTimeout)
	defer cancel()
	var n NotificationLog
	err := s.db.QueryRowContext(ctx, "SELECT id,booking_id,username,channel,message,sent_at FROM notification_logs WHERE id = ?", id).
		Scan(&n.ID, &n.BookingID, &n.Username, &n.Channel, &n.Message, &n.SentAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &n, nil
}

func (s *MySQLStore) Update(ctx context.Context, id int64, req UpdateLogRequest) (*NotificationLog, error) {
	ctx, cancel := context.WithTimeout(ctx, dbTimeout)
	defer cancel()

	existing, err := s.Get(ctx, id)
	if err != nil {
		return nil, err
	}
	if existing == nil {
		return nil, nil
	}

	if req.Username != nil {
		existing.Username = *req.Username
	}
	if req.BookingID != nil {
		existing.BookingID = *req.BookingID
	}
	if req.Channel != nil {
		existing.Channel = *req.Channel
	}
	if req.Message != nil {
		existing.Message = *req.Message
	}

	_, err = s.db.ExecContext(ctx, "UPDATE notification_logs SET booking_id=?, username=?, channel=?, message=? WHERE id=?",
		existing.BookingID, existing.Username, existing.Channel, existing.Message, id)
	if err != nil {
		return nil, err
	}
	return existing, nil
}

func (s *MySQLStore) Delete(ctx context.Context, id int64) error {
	ctx, cancel := context.WithTimeout(ctx, dbTimeout)
	defer cancel()
	res, err := s.db.ExecContext(ctx, "DELETE FROM notification_logs WHERE id = ?", id)
	if err != nil {
		return err
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}

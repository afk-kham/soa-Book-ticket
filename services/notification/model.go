package main

import "time"

type NotifyRequest struct {
	Username  string `json:"username"`
	BookingID int64  `json:"bookingId"`
	Channel   string `json:"channel"`
}
type NotificationLog struct {
	ID        int64     `json:"id"`
	BookingID int64     `json:"bookingId"`
	Username  string    `json:"username"`
	Channel   string    `json:"channel"`
	Message   string    `json:"message"`
	SentAt    time.Time `json:"sentAt"`
}
type NotifyResponse struct {
	NotificationID int64     `json:"notificationId"`
	BookingID      int64     `json:"bookingId"`
	Username       string    `json:"username"`
	Channel        string    `json:"channel"`
	DeliveryStatus string    `json:"deliveryStatus"`
	Message        string    `json:"message"`
	SentAt         time.Time `json:"sentAt"`
}

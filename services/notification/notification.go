package main

import (
	"context"
	"fmt"
	"log"
)

type Sender interface {
	Send(context.Context, NotificationLog) error
}
type ConsoleSender struct{ logger *log.Logger }

func (s ConsoleSender) Send(ctx context.Context, n NotificationLog) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	s.logger.Printf("SIMULATED channel=%s username=%q bookingId=%d message=%q", n.Channel, n.Username, n.BookingID, n.Message)
	return nil
}
func composeMessage(id int64) string { return fmt.Sprintf("Đặt vé thành công cho đơn #%d", id) }

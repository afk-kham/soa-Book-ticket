package main

import "testing"

func TestConfig(t *testing.T) {
	for k, v := range map[string]string{"HTTP_ADDR": "0.0.0.0:5006", "DB_HOST": "127.0.0.1", "DB_PORT": "3306", "DB_NAME": "notification_db", "DB_USER": "test", "DB_PASSWORD": ""} {
		t.Setenv(k, v)
	}
	if _, err := loadConfig(); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct{ k, v string }{{"HTTP_ADDR", "bad"}, {"HTTP_ADDR", "localhost:0"}, {"DB_PORT", "65536"}, {"DB_PORT", "x"}, {"DB_HOST", " "}, {"DB_NAME", ""}, {"DB_USER", ""}} {
		t.Run(tc.k+tc.v, func(t *testing.T) {
			t.Setenv(tc.k, tc.v)
			if _, err := loadConfig(); err == nil {
				t.Fatal("expected validation error")
			}
		})
	}
}

// Chạy: mongosh seed/payment_db.js
use('payment_db');
db.transactions.drop();
db.transactions.insertMany([
  { bookingId: 1, amount: 180000, method: 'MOMO',  status: 'PAID',   paidAt: new Date('2026-10-01T10:01:00Z') },
  { bookingId: 2, amount: 85000,  method: 'VNPAY', status: 'FAILED', paidAt: new Date('2026-10-01T11:01:00Z') }
]);

"use strict";
// CÔNG CỤ TEST (không phải code sản phẩm): chạy Payment Service với "collection" trong bộ nhớ,
// dùng khi máy chưa cài MongoDB mà vẫn muốn chạy bộ test tích hợp.  node tests/integration/tools/payment_in_memory.js
const { createApp } = require("../../../services/payment/payment_service");
const docs = []; let n = 0;
const match = (d, f) => Object.entries(f).every(([k, v]) => d[k] === v);
const collection = {
  async insertOne(doc) { const _id = `mem${++n}`; docs.push({ ...doc, _id }); return { insertedId: _id }; },
  async findOne(f) { return docs.find(d => match(d, f)) || null; },
  find(f) { const r = docs.filter(d => match(d, f)).sort((a, b) => b.paidAt - a.paidAt); return { sort() { return this; }, async toArray() { return r; } }; },
};
// dữ liệu mẫu chung (khớp database/payment/seed.js)
docs.push({ _id: "seed1", bookingId: 1, amount: 180000, method: "MOMO", status: "PAID", paidAt: new Date("2026-10-01T10:01:00Z") });
docs.push({ _id: "seed2", bookingId: 2, amount: 85000, method: "VNPAY", status: "FAILED", paidAt: new Date("2026-10-01T11:01:00Z") });
const port = Number(process.env.PORT || 5005);
createApp(collection).listen(port, "0.0.0.0", () => console.log(`[IN-MEMORY] Payment Service tại :${port} (không dùng MongoDB)`));

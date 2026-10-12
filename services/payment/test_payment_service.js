"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizeTransaction, validateShape } = require("./payment_service");
test("valid PAID transaction uses numeric bookingId", () => { const t = normalizeTransaction({ bookingId: 3, amount: 180000, method: "momo" }); assert.equal(t.bookingId, 3); assert.equal(typeof t.bookingId, "number"); assert.equal(t.method, "MOMO"); assert.equal(t.status, "PAID"); assert.ok(t.paidAt instanceof Date); });
test("zero or negative amount is FAILED", () => { assert.equal(normalizeTransaction({ bookingId: 4, amount: 0, method: "MOMO" }).status, "FAILED"); assert.equal(normalizeTransaction({ bookingId: 5, amount: -1, method: "CASH" }).status, "FAILED"); });
test("unknown method is FAILED", () => { const t = normalizeTransaction({ bookingId: 6, amount: 100000, method: "BANK" }); assert.equal(t.status, "FAILED"); assert.equal(t.method, "BANK"); });
test("shape validation rejects malformed fields", () => { assert.match(validateShape({ bookingId: "3", amount: 1, method: "MOMO" }), /bookingId/); assert.match(validateShape({ bookingId: 3, method: "MOMO" }), /amount/); assert.match(validateShape({ bookingId: 3, amount: 1 }), /method/); assert.equal(validateShape({ bookingId: 3, amount: 1, method: "MOMO" }), null); });

// ---- Kiểm thử HTTP của hợp đồng chung (dùng collection giả trong bộ nhớ, không cần MongoDB) ----
function fakeCollection() {
  const docs = []; let n = 0;
  const match = (d, f) => Object.entries(f).every(([k, v]) => d[k] === v);
  return {
    async insertOne(doc) { const _id = `id${++n}`; docs.push({ ...doc, _id }); return { insertedId: _id }; },
    async findOne(f) { return docs.find(d => match(d, f)) || null; },
    find(f) { const r = docs.filter(d => match(d, f)); return { sort() { return this; }, async toArray() { return r; } }; },
  };
}
async function withServer(fn) {
  const { createApp } = require("./payment_service");
  const server = createApp(fakeCollection());
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  try { await fn(base); } finally { await new Promise(r => server.close(r)); }
}
const post = (base, body) => fetch(base + "/api/payment", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

test("POST /api/payment dùng envelope chung và trả id (không _id)", () => withServer(async base => {
  const res = await post(base, { bookingId: 7, amount: 180000, method: "momo" });
  assert.equal(res.status, 201);
  const j = await res.json();
  assert.equal(j.status, "success");
  assert.equal(j.data.status, "PAID");
  assert.equal(j.data.bookingId, 7);
  assert.ok(j.data.id); assert.equal(j.data._id, undefined);
}));

test("thanh toán trùng một đơn đã PAID bị từ chối 409", () => withServer(async base => {
  await post(base, { bookingId: 8, amount: 90000, method: "CASH" });
  const res = await post(base, { bookingId: 8, amount: 90000, method: "CASH" });
  assert.equal(res.status, 409);
  const j = await res.json();
  assert.equal(j.status, "error"); assert.equal(j.code, "ALREADY_PAID");
}));

test("giao dịch FAILED vẫn được lưu (201) và cho phép thử lại", () => withServer(async base => {
  const r1 = await post(base, { bookingId: 9, amount: 0, method: "MOMO" });
  assert.equal(r1.status, 201); assert.equal((await r1.json()).data.status, "FAILED");
  const r2 = await post(base, { bookingId: 9, amount: 90000, method: "MOMO" });
  assert.equal(r2.status, 201); assert.equal((await r2.json()).data.status, "PAID");
}));

test("GET /api/payment?bookingId= lọc đúng và lỗi trả code", () => withServer(async base => {
  await post(base, { bookingId: 1, amount: 1, method: "CASH" });
  await post(base, { bookingId: 2, amount: 1, method: "CASH" });
  const ok = await (await fetch(base + "/api/payment?bookingId=2")).json();
  assert.equal(ok.data.length, 1); assert.equal(ok.data[0].bookingId, 2);
  const bad = await fetch(base + "/api/payment?bookingId=abc");
  assert.equal(bad.status, 400); assert.equal((await bad.json()).code, "VALIDATION_ERROR");
  assert.equal((await fetch(base + "/api/nope")).status, 404);
}));

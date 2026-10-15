"use strict";
const fs = require("fs");
const path_ = require("path");
(function loadDotenv() {
  const file = path_.join(__dirname, ".env");
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#") || !t.includes("=")) continue;
    const i = t.indexOf("=");
    const k = t.slice(0, i).trim();
    if (process.env[k] === undefined) process.env[k] = t.slice(i + 1).trim().replace(/^["']|["']$/g, "");
  }
})();
const http = require("http");
const { MongoClient } = require("mongodb");
const PORT = Number(process.env.PORT || 5005);
const HOST = process.env.HOST || "0.0.0.0";
const MONGO_URI = process.env.MONGO_URI || "mongodb://127.0.0.1:27017";
const DB_NAME = process.env.MONGO_DB || "payment_db";
// BANK_TRANSFER: chuyển khoản ngân hàng qua mã VietQR; CASH giữ lại để tương thích (Admin bán tại quầy)
const ALLOWED_METHODS = new Set(["BANK_TRANSFER", "MOMO", "VNPAY", "CASH"]);
const MAX_BODY_BYTES = 1024 * 1024;
function corsHeaders() { return { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type,Authorization", "Access-Control-Max-Age": "86400" }; }
function sendJson(res, statusCode, payload) { const body = JSON.stringify(payload); res.writeHead(statusCode, { ...corsHeaders(), "Content-Type": "application/json; charset=utf-8", "Content-Length": Buffer.byteLength(body) }); res.end(body); }
const ERROR_CODES = { 400: "VALIDATION_ERROR", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 500: "INTERNAL_ERROR" };
function sendError(res, statusCode, message, code) { sendJson(res, statusCode, { status: "error", code: code || ERROR_CODES[statusCode] || "ERROR", message }); }
function sendSuccess(res, statusCode, data) { sendJson(res, statusCode, { status: "success", data }); }
function readJsonBody(req) { return new Promise((resolve, reject) => { let raw = "", bytes = 0; req.setEncoding("utf8"); req.on("data", chunk => { bytes += Buffer.byteLength(chunk); if (bytes > MAX_BODY_BYTES) { reject(Object.assign(new Error("Request body quá lớn"), { statusCode: 413 })); req.destroy(); return; } raw += chunk; }); req.on("end", () => { try { resolve(JSON.parse(raw)); } catch (_) { reject(Object.assign(new Error("JSON không hợp lệ"), { statusCode: 400 })); } }); req.on("error", reject); }); }
function validateShape(input) { if (!input || typeof input !== "object" || Array.isArray(input)) return "Body phải là một object JSON"; if (!Number.isInteger(input.bookingId) || input.bookingId <= 0) return "bookingId phải là số nguyên dương"; if (typeof input.amount !== "number" || !Number.isFinite(input.amount)) return "amount phải là số"; if (typeof input.method !== "string" || input.method.trim() === "") return "method là bắt buộc"; return null; }
function normalizeTransaction(input) { const method = String(input.method).trim().toUpperCase(); return { bookingId: Number(input.bookingId), amount: Number(input.amount), method, status: input.amount > 0 && ALLOWED_METHODS.has(method) ? "PAID" : "FAILED", paidAt: new Date() }; }
function serializeTransaction(doc) { const { _id, ...rest } = doc; return { id: _id ? String(_id) : undefined, ...rest, paidAt: doc.paidAt instanceof Date ? doc.paidAt.toISOString() : doc.paidAt }; }
function createApp(collection) {
  return http.createServer(async (req, res) => {
    if (req.method === "OPTIONS") { res.writeHead(204, corsHeaders()); return res.end(); }
    const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (path === "/api/payment" && req.method === "POST") {
        const input = await readJsonBody(req);
        const shapeError = validateShape(input);
        if (shapeError) return sendError(res, 400, shapeError);
        // Chống thanh toán trùng: đơn đã PAID thì không nhận thêm giao dịch (Duplicate request)
        const paid = await collection.findOne({ bookingId: Number(input.bookingId), status: "PAID" });
        if (paid) return sendError(res, 409, `Đơn #${input.bookingId} đã được thanh toán`, "ALREADY_PAID");
        const transaction = normalizeTransaction(input);
        const result = await collection.insertOne(transaction);
        // FAILED vẫn được lưu và trả 201: giao dịch đã được ghi nhận, Booking đọc data.status để quyết định PAID/CANCELLED
        return sendSuccess(res, 201, serializeTransaction({ ...transaction, _id: result.insertedId }));
      }
      if (path === "/api/payment" && req.method === "GET") {
        const filter = {};
        const bid = url.searchParams.get("bookingId");
        if (bid !== null) {
          if (!/^\d+$/.test(bid) || Number(bid) <= 0) return sendError(res, 400, "bookingId phải là số nguyên dương");
          filter.bookingId = Number(bid);
        }
        const transactions = await collection.find(filter).sort({ paidAt: -1 }).toArray();
        return sendSuccess(res, 200, transactions.map(serializeTransaction));
      }
      if (path === "/health" && req.method === "GET") return sendSuccess(res, 200, { service: "payment-service", port: PORT });
      if (path === "/api/payment") { res.setHeader("Allow", "GET, POST, OPTIONS"); return sendError(res, 405, "Phương thức không được hỗ trợ"); }
      return sendError(res, 404, "Không tìm thấy endpoint");
    } catch (error) {
      console.error("[payment-service] request error:", error);
      return sendError(res, error.statusCode || 500, error.statusCode ? error.message : "Lỗi máy chủ nội bộ");
    }
  });
}
async function start() { const client = new MongoClient(MONGO_URI); await client.connect(); const collection = client.db(DB_NAME).collection("transactions"); await collection.createIndex({ bookingId: 1 }); const server = createApp(collection); server.listen(PORT, HOST, () => console.log(`Payment Service đang chạy tại http://${HOST}:${PORT}`)); const shutdown = signal => { console.log(`Nhận ${signal}, đang đóng Payment Service...`); server.close(async () => { await client.close(); process.exit(0); }); }; process.once("SIGINT", () => shutdown("SIGINT")); process.once("SIGTERM", () => shutdown("SIGTERM")); return { server, client }; }
if (require.main === module) start().catch(error => { console.error("Không thể khởi động Payment Service:", error.message); process.exit(1); });
module.exports = { ALLOWED_METHODS, createApp, normalizeTransaction, validateShape };

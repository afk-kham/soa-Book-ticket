"""Repository SQLite cho bảng transactions. Không chứa quy tắc nghiệp vụ."""
from typing import Optional

from app.db.connection import get_connection
from app.entities import PaymentTransaction


def _entity(row) -> PaymentTransaction:
    return PaymentTransaction(
        id=int(row["id"]),
        booking_id=int(row["booking_id"]),
        amount=int(row["amount"]),
        method=str(row["method"]),
        status=str(row["status"]),
        paid_at=str(row["paid_at"]),
    )


def create_transaction(
    transaction: PaymentTransaction,
) -> tuple[Optional[PaymentTransaction], bool]:
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            paid = conn.execute(
                "SELECT 1 FROM transactions "
                "WHERE booking_id = ? AND status = 'PAID' LIMIT 1",
                (transaction.booking_id,),
            ).fetchone()
            if paid:
                conn.rollback()
                return None, True

            conn.execute(
                "INSERT INTO transactions "
                "(booking_id, amount, method, status, paid_at) VALUES (?, ?, ?, ?, ?)",
                (
                    transaction.booking_id,
                    transaction.amount,
                    transaction.method,
                    transaction.status,
                    transaction.paid_at,
                ),
            )
            row = conn.execute(
                "SELECT id, booking_id, amount, method, status, paid_at "
                "FROM transactions WHERE rowid = last_insert_rowid()"
            ).fetchone()
            conn.commit()
            return _entity(row), False
        except Exception:
            conn.rollback()
            raise


def list_transactions(booking_id: Optional[int] = None):
    sql = "SELECT id, booking_id, amount, method, status, paid_at FROM transactions"
    params = ()
    if booking_id is not None:
        sql += " WHERE booking_id = ?"
        params = (booking_id,)
    sql += " ORDER BY paid_at DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_entity(row) for row in rows]

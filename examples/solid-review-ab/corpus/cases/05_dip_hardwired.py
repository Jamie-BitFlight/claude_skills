# CASE: DIP violations — direct instantiation (DIP-1), concrete class dependency (DIP-2),
# I/O import in policy (DIP-3).
# SYSTEMATIC MISS (DIP-3 subtle): NotificationService.send_alert imports and calls
# smtplib directly inside a business method. The smtp call is one line in a ten-line
# method, so cheap reviewers often focus on the other violations and miss this one.
from __future__ import annotations

import json
import smtplib
import sqlite3
from email.message import EmailMessage
from pathlib import Path


# VIOLATION DIP-1: OrderService directly instantiates SqliteOrderRepository
# (a concrete low-level dependency) inside __init__ — no injection seam.
class SqliteOrderRepository:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)

    def save(self, order: dict) -> None:
        cur = self._conn.cursor()
        cur.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(order),))
        self._conn.commit()


class OrderService:
    def __init__(self) -> None:
        # Hard-coded construction — no injection seam; impossible to substitute
        # a test double or alternative store without editing this class.
        self._repo = SqliteOrderRepository("/var/data/orders.db")

    def place_order(self, customer_id: str, items: list[str]) -> None:
        order = {"customer": customer_id, "items": items}
        self._repo.save(order)


# VIOLATION DIP-2: InvoiceGenerator depends on PdfPrinter — a concrete class —
# where it should depend on an abstraction (e.g., a Printer protocol).
class PdfPrinter:
    def print_document(self, content: str) -> bytes:
        # Concrete PDF rendering — not an abstraction
        return content.encode("utf-8")


class InvoiceGenerator:
    def __init__(self) -> None:
        # Depends on PdfPrinter directly — locked to one output format
        self._printer = PdfPrinter()

    def generate(self, invoice_data: dict) -> bytes:
        content = "\n".join(f"{k}: {v}" for k, v in invoice_data.items())
        return self._printer.print_document(content)


# SYSTEMATIC MISS — DIP-3 (subtle I/O import in business policy):
# NotificationService.send_alert contains real business logic (building the message,
# deciding recipients) but also directly imports and calls smtplib — an I/O transport.
# This hides the violation inside what looks like a notification helper.
# Cheap reviewers flag DIP-1 and DIP-2 above but miss this one.
class NotificationService:
    def __init__(self, smtp_host: str, admin_email: str) -> None:
        self._smtp_host = smtp_host
        self._admin_email = admin_email

    def send_alert(self, subject: str, body: str) -> None:
        # Business logic: build the message
        msg = EmailMessage()
        msg["Subject"] = f"[ALERT] {subject}"
        msg["From"] = "system@example.com"
        msg["To"] = self._admin_email
        msg.set_content(body)
        # DIP-3 violation: policy unit (NotificationService) calls smtplib directly.
        # Changing to a push notification or queue would require editing this class.
        with smtplib.SMTP(self._smtp_host) as server:
            server.send_message(msg)


# Supporting module-level helpers (clean — no SOLID violations)
def read_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

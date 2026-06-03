# CASE: mixed violations — SRP-1 (god object), OCP-1 (type dispatch), DIP-1 (hard construction),
# ISP-2 (broad client), plus one DECOY (legitimate Facade resembling a god object).
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


# VIOLATION SRP-1: ReportManager handles data loading, transformation, persistence,
# and email dispatch — four unrelated reasons to change.
class ReportManager:
    def __init__(self, db_path: str, output_dir: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._output_dir = Path(output_dir)

    def load_sales(self) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM sales")
        return [{"id": row[0], "amount": row[1]} for row in cur.fetchall()]

    def compute_totals(self, rows: list[dict]) -> dict:
        total = sum(float(r["amount"]) for r in rows)
        return {"count": len(rows), "total": total}

    # VIOLATION OCP-1: format selection by type tag — adding CSV or PDF requires
    # editing this closed function body.
    def format_report(self, summary: dict, fmt: str) -> str:
        if fmt == "json":
            return json.dumps(summary)
        elif fmt == "text":
            return "\n".join(f"{k}: {v}" for k, v in summary.items())
        elif fmt == "html":
            rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in summary.items())
            return f"<table>{rows}</table>"
        else:
            raise ValueError(f"Unknown format: {fmt}")

    def save_report(self, content: str, filename: str) -> None:
        (self._output_dir / filename).write_text(content, encoding="utf-8")

    def send_report_email(self, to: str, content: str) -> None:
        # DIP-1: directly imports and uses smtplib (would be flagged separately as DIP-3)
        import smtplib  # noqa: PLC0415
        from email.message import EmailMessage  # noqa: PLC0415

        msg = EmailMessage()
        msg["Subject"] = "Monthly Report"
        msg["From"] = "reports@example.com"
        msg["To"] = to
        msg.set_content(content)
        with smtplib.SMTP("localhost") as s:
            s.send_message(msg)


# VIOLATION DIP-1: Pipeline hard-wires a concrete ReportManager
# instead of depending on an abstraction.
class Pipeline:
    def __init__(self) -> None:
        # Hard-coded construction — no injection seam
        self._manager = ReportManager("/var/db/sales.db", "/var/reports/")

    def run(self, fmt: str, recipient: str) -> None:
        rows = self._manager.load_sales()
        summary = self._manager.compute_totals(rows)
        content = self._manager.format_report(summary, fmt)
        self._manager.save_report(content, "report.txt")
        self._manager.send_report_email(recipient, content)


# VIOLATION ISP-2: AuditClient only calls log_event() but depends on the full
# IEventBus interface including publish/subscribe/unsubscribe.
class IEventBus:
    def publish(self, topic: str, data: dict) -> None: ...
    def subscribe(self, topic: str, handler: object) -> None: ...
    def unsubscribe(self, topic: str, handler: object) -> None: ...
    def log_event(self, event: str, metadata: dict) -> None: ...
    def flush(self) -> None: ...


class InMemoryEventBus(IEventBus):
    def __init__(self) -> None:
        self._log: list[str] = []

    def publish(self, topic: str, data: dict) -> None:
        self._log.append(f"publish:{topic}")

    def subscribe(self, topic: str, handler: object) -> None:
        pass

    def unsubscribe(self, topic: str, handler: object) -> None:
        pass

    def log_event(self, event: str, metadata: dict) -> None:
        self._log.append(f"event:{event}")

    def flush(self) -> None:
        self._log.clear()


class AuditClient:
    def __init__(self, bus: IEventBus) -> None:
        self._bus = bus

    def record(self, action: str) -> None:
        # Only log_event() is used — four other IEventBus methods are unused dependencies
        self._bus.log_event(action, {"source": "audit"})


# DECOY: ServiceLocator looks like a god object (it touches db, cache, mailer)
# but is a legitimate service locator / composition root. It does not carry
# business logic — it wires dependencies and delegates entirely to focused services.
# A naive reviewer may flag it as SRP-1 because it references multiple concerns,
# but the pattern is intentionally broad at the composition boundary.
class DatabaseService:
    def query(self, sql: str) -> list:
        return []


class CacheService:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def set(self, key: str, value: object) -> None:
        self._store[key] = value


class MailService:
    def send(self, to: str, body: str) -> None:
        pass


class ServiceLocator:
    """Composition root — not an SRP violation.

    DECOY: wires three services but carries zero business logic itself.
    Each method returns a focused, single-purpose service object.
    """

    def __init__(self) -> None:
        self._db = DatabaseService()
        self._cache = CacheService()
        self._mail = MailService()

    def database(self) -> DatabaseService:
        return self._db

    def cache(self) -> CacheService:
        return self._cache

    def mailer(self) -> MailService:
        return self._mail

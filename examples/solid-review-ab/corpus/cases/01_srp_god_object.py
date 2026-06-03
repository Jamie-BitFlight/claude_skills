# CASE: SRP violations — god object (SRP-1), abstraction mixing (SRP-2), change coupling (SRP-3)
# Also contains a DECOY: OrderProcessor.process() uses a dependency injected in the constructor
# but also accepts a concrete default; this LOOKS like DIP-1 but is actually correct DI pattern.
from __future__ import annotations

import hashlib
import json
import os
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path


# VIOLATION SRP-1: god object — handles user auth, order management,
# reporting, and email notification in one class.
class UserOrderManager:
    """Manages users, orders, reports, and sends emails — four distinct responsibilities."""

    def __init__(self, db_path: str, smtp_host: str) -> None:
        self.db_path = db_path
        self.smtp_host = smtp_host
        self.users: dict[str, dict[str, str]] = {}
        self.orders: list[dict[str, object]] = []

    def create_user(self, username: str, password: str) -> None:
        """Create a user and hash their password."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {"password": hashed, "role": "customer"}

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user by comparing hashed passwords."""
        user = self.users.get(username)
        if user is None:
            return False
        return user["password"] == hashlib.sha256(password.encode()).hexdigest()

    def place_order(self, username: str, items: list[str], total: float) -> int:
        """Place an order and persist to disk."""
        order_id = len(self.orders)
        order = {"id": order_id, "username": username, "items": items, "total": total}
        self.orders.append(order)
        # Persist raw to disk — mixing storage concern into order logic
        path = Path(self.db_path) / f"order_{order_id}.json"
        path.write_text(json.dumps(order))
        return order_id

    def cancel_order(self, order_id: int) -> None:
        """Cancel an order and send confirmation email."""
        if order_id < len(self.orders):
            self.orders[order_id]["status"] = "cancelled"
        # Sends email directly — mixing notification into order domain
        self._send_email("admin@example.com", f"Order {order_id} cancelled", "Please review.")

    # VIOLATION SRP-2: high-level report orchestration mixed with low-level
    # CSV serialization detail in one function body.
    def generate_monthly_report(self) -> str:
        """Generate a monthly report, filter orders, format CSV — all in one body."""
        # High-level: decide what to report
        completed = [o for o in self.orders if o.get("status") == "completed"]
        total_revenue = sum(float(o["total"]) for o in completed)  # type: ignore[arg-type]

        # Low-level: manual CSV serialization detail mixed into the same function
        lines = ["order_id,username,total"]
        lines.extend(f"{o['id']},{o['username']},{o['total']}" for o in completed)
        csv_body = "\n".join(lines)
        return f"Revenue: {total_revenue}\n{csv_body}"

    # VIOLATION SRP-3: changing email provider (SMTP→API) forces edits to
    # UserOrderManager even though email is unrelated to order management.
    def _send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email directly via SMTP — tightly coupling email logic here."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = "system@example.com"
        msg["To"] = to
        msg.set_content(body)
        with smtplib.SMTP(self.smtp_host) as server:
            server.send_message(msg)

    def get_user_role(self, username: str) -> str | None:
        """Return the user's role string."""
        user = self.users.get(username)
        return user["role"] if user else None


# DECOY — false positive: OrderProcessor takes an injected dependency via constructor
# and provides a concrete default for convenience. The default is not a DIP-1 violation
# because the constructor parameter is typed to the abstraction; the default is a
# convenience that callers can override. A cheap reviewer may flag this as DIP-1.
@dataclass
class FileOrderStore:
    """Minimal concrete order store — used as a default in the decoy."""

    root: Path = field(default_factory=lambda: Path("/tmp/orders"))  # noqa: S108

    def save(self, order_id: int, data: dict[str, object]) -> None:
        """Persist an order to disk."""
        (self.root / f"{order_id}.json").write_text(json.dumps(data))


class OrderProcessor:
    """Processes orders using an injected store.

    DECOY: constructor has a concrete default for the store parameter, but the
    parameter type is FileOrderStore (an abstraction here for illustration).
    This is a legitimate convenience default, not a DIP-1 hard-wired construction.
    """

    def __init__(self, store: FileOrderStore | None = None) -> None:
        # Default is a convenience — callers can inject any FileOrderStore subtype.
        self.store = store if store is not None else FileOrderStore()

    def process(self, order_id: int, data: dict[str, object]) -> None:
        """Persist an order through the injected store."""
        self.store.save(order_id, data)


def load_config(config_path: str) -> dict[str, str]:
    """Load configuration from a JSON file.

    Args:
        config_path: Path to the JSON config file.

    Returns:
        Parsed configuration dictionary.
    """
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    cfg = load_config(os.environ.get("CONFIG_PATH", "config.json"))
    manager = UserOrderManager(cfg.get("db_path", "/tmp/db"), cfg.get("smtp", "localhost"))  # noqa: S108
    print(manager.generate_monthly_report())

# services/payment_qr_service.py
"""
Payment QR ticket lifecycle.

A ticket is created against an invoice, holds an opaque id, and is
settled by a wallet-side callback. The router exposes three endpoints:

    POST   /payments/qr                 → mint a ticket
    GET    /payments/qr/stream/{id}     → subscribe to the outcome (SSE)
    DELETE /payments/qr/{id}            → invalidate before settlement

This service is transport-agnostic: it stores tickets in memory and
exposes an async subscription per ticket. Swap `_tickets` for Redis or
Postgres once you need multi-process coordination.
"""
from __future__ import annotations

import asyncio
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, AsyncIterator
import logging

from core.logging_config import get_logger

logger = get_logger(__name__)


QR_TICKET_TTL = timedelta(minutes=10)
QR_TERMINAL_OUTCOMES = {"success", "failure", "expired", "cancelled"}


@dataclass
class QrTicket:
    ticket_id: str
    invoice_id: int
    amount: float
    currency: str
    payee_id: str
    note: Optional[str]
    qr_text: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Set once the ticket reaches a terminal state. None while waiting.
    outcome: Optional[str] = None
    message: Optional[str] = None
    reference: Optional[str] = None
    # Subscribers waiting on the terminal event.
    _waiters: list[asyncio.Queue] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return self.outcome in QR_TERMINAL_OUTCOMES

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    async def push(self, event: dict) -> None:
        """Record a terminal event and wake every waiter."""
        self.outcome = event["outcome"]
        self.message = event.get("message")
        self.reference = event.get("reference")
        for q in list(self._waiters):
            await q.put(event)

    async def subscribe(self) -> AsyncIterator[dict]:
        """
        Yield exactly one event: the terminal outcome for this ticket.
        Returns immediately if the ticket is already terminal.
        """
        if self.is_terminal():
            yield {
                "outcome": self.outcome,
                "message": self.message,
                "reference": self.reference,
            }
            return

        q: asyncio.Queue = asyncio.Queue()
        self._waiters.append(q)
        try:
            # Wait for either the terminal event or the TTL.
            remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
            try:
                event = await asyncio.wait_for(q.get(), timeout=max(remaining, 0))
            except asyncio.TimeoutError:
                await self.push({
                    "outcome": "expired",
                    "message": "QR expired.",
                })
                event = {
                    "outcome": "expired",
                    "message": "QR expired.",
                }
            yield event
        finally:
            if q in self._waiters:
                self._waiters.remove(q)


class PaymentQrService:
    def __init__(self) -> None:
        # ticket_id → QrTicket. Process-local; swap for a shared store
        # when you need multi-worker coordination.
        self._tickets: Dict[str, QrTicket] = {}

    def create_ticket(
        self,
        invoice_id: int,
        amount: float,
        currency: str,
        payee_id: str,
        note: Optional[str],
    ) -> QrTicket:
        if amount <= 0:
            raise ValueError("amount must be positive")

        ticket_id = f"qr_{uuid.uuid4().hex[:16]}"
        expires_at = datetime.now(timezone.utc) + QR_TICKET_TTL

        # The QR text is what the payer's wallet decodes. Keep it a
        # canonical, versioned string so the wallet side can parse it
        # without a schema negotiation.
        qr_text = (
            f"walletpay://v1"
            f"?ticket={ticket_id}"
            f"&invoice={invoice_id}"
            f"&amount={amount:.2f}"
            f"&currency={currency}"
            f"&payee={payee_id}"
            f"&expires={expires_at.isoformat()}"
        )

        ticket = QrTicket(
            ticket_id=ticket_id,
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            payee_id=payee_id,
            note=note,
            qr_text=qr_text,
            expires_at=expires_at,
        )
        self._tickets[ticket_id] = ticket
        logger.info(
            "QR ticket minted: %s invoice=%s amount=%s",
            ticket_id, invoice_id, amount,
        )
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[QrTicket]:
        return self._tickets.get(ticket_id)

    async def cancel_ticket(self, ticket_id: str) -> bool:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        if ticket.is_terminal():
            # Already settled; cancelling is a no-op.
            return True
        await ticket.push({
            "outcome": "cancelled",
            "message": "Cancelled by provider.",
        })
        return True

    async def settle_ticket(
        self,
        ticket_id: str,
        outcome: str,
        message: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> bool:
        """
        Called by the wallet-side callback to settle a ticket. Also
        usable from an admin endpoint for manual overrides.
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        if ticket.is_terminal():
            return False
        if outcome not in QR_TERMINAL_OUTCOMES:
            raise ValueError(f"invalid outcome {outcome!r}")
        await ticket.push({
            "outcome": outcome,
            "message": message,
            "reference": reference,
        })
        return True


# Process-singleton. Inject via FastAPI dependency if you'd rather
# manage the lifetime yourself.
payment_qr_service = PaymentQrService()
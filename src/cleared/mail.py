"""Outbound mail.

There is one transport for now: it logs. A real provider plugs in behind the same interface,
and nothing above this line needs to know which one is in use.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("cleared.mail")


@dataclass(frozen=True)
class Outgoing:
    recipient: str
    subject: str
    body: str


class Transport(Protocol):
    def send(self, message: Outgoing) -> None: ...


class LogTransport:
    """Writes the message to the log instead of sending it."""

    def send(self, message: Outgoing) -> None:
        logger.info(
            "mail.outbound",
            extra={"recipient": message.recipient, "subject": message.subject},
        )


def get_transport() -> Transport:
    return LogTransport()

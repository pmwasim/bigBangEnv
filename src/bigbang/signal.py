"""Signals: the impulses that travel across the kernel bus.

Every signal is created and stamped by the kernel. Cells never construct
signals directly, so they cannot forge sender, trust or birth tick.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
from typing import Any


class Trust(IntEnum):
    """Authority ladder. Higher values carry more authority."""

    WORLD = 0  # untrusted outside input (web pages, emails, tool output)
    USER = 1  # a person interacting with the agent
    OPERATOR = 2  # whoever deployed and configured the agent
    OWNER = 3  # the principal the agent ultimately serves
    KERNEL = 4  # the runtime itself; never granted to cells


class Kind(str, Enum):
    EXCITE = "excite"  # "do / consider this"
    INHIBIT = "inhibit"  # "stop": cancels pending excite signals on the topic


@dataclass(frozen=True)
class Signal:
    id: int
    topic: str
    payload: Any
    kind: Kind
    sender: str
    trust: Trust
    born: int  # tick at which the signal was emitted
    ttl: int  # ticks the signal stays alive after birth

    def expired(self, tick: int) -> bool:
        return tick - self.born > self.ttl

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["trust"] = self.trust.name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        return cls(
            id=data["id"],
            topic=data["topic"],
            payload=data["payload"],
            kind=Kind(data["kind"]),
            sender=data["sender"],
            trust=Trust[data["trust"]],
            born=data["born"],
            ttl=data["ttl"],
        )

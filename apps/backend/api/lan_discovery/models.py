"""
LAN Discovery Data Models

Dataclasses for LAN devices and clients.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict


# Service type for mDNS discovery
SERVICE_TYPE = "_omnistudio._tcp.local."


@dataclass
class LANClient:
    """Represents a connected client to this hub"""
    id: str
    name: str
    ip: str
    connected_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LANDevice:
    """Represents a discovered MedStation instance on the network"""
    id: str
    name: str
    ip: str
    port: int
    is_hub: bool
    version: str
    discovered_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

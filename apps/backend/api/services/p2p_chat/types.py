"""
P2P Chat Service - Type Definitions

Internal type definitions for the P2P chat service.
External models (Peer, Channel, Message, etc.) are in p2p_chat_models.py.
"""

# Protocol constants
PROTOCOL_ID = "/omnistudio/chat/1.0.0"
FILE_PROTOCOL_ID = "/omnistudio/file/1.0.0"
MDNS_SERVICE_NAME = "_omnistudio._udp.local"

# Storage path configuration
from api.config_paths import get_config_paths
PATHS = get_config_paths()
DB_PATH = PATHS.data_dir / "p2p_chat.db"

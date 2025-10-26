"""
Workflow P2P Sync Service
Syncs workflow state across P2P mesh for offline collaboration
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

try:
    from .workflow_models import (
        WorkItem,
        Workflow,
        WorkflowSyncMessage,
        WorkItemConflict,
        WorkItemStatus,
    )
    from .workflow_storage import WorkflowStorage
    from .workflow_orchestrator import WorkflowOrchestrator
except ImportError:
    from workflow_models import (
        WorkItem,
        Workflow,
        WorkflowSyncMessage,
        WorkItemConflict,
        WorkItemStatus,
    )
    from workflow_storage import WorkflowStorage
    from workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)

# Protocol ID for workflow sync
WORKFLOW_SYNC_PROTOCOL = "/elohimos/workflow/1.0.0"


class WorkflowP2PSync:
    """
    P2P synchronization for workflow state using CRDT principles

    Features:
    - Sync work item state changes (claim, complete, transition)
    - Sync workflow definitions
    - Vector clocks for causality tracking
    - Conflict resolution (last-write-wins with tie-breaking)
    - Offline queue with replay on reconnect
    """

    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        storage: WorkflowStorage,
        peer_id: str,
    ):
        self.orchestrator = orchestrator
        self.storage = storage
        self.peer_id = peer_id

        # Vector clock for causality tracking
        # Format: {peer_id: counter}
        self.vector_clock: Dict[str, int] = {peer_id: 0}

        # Offline message queue
        self.offline_queue: List[WorkflowSyncMessage] = []

        # Message handlers
        self.message_handlers: List[Callable] = []

        # Seen messages (for deduplication)
        self.seen_messages: set = set()

        logger.info(f"🔄 Workflow P2P Sync initialized for peer {peer_id}")

    # ============================================
    # VECTOR CLOCK OPERATIONS
    # ============================================

    def increment_clock(self) -> Dict[str, int]:
        """Increment our local clock"""
        self.vector_clock[self.peer_id] += 1
        return self.vector_clock.copy()

    def merge_clock(self, remote_clock: Dict[str, int]) -> None:
        """Merge remote vector clock with ours"""
        for peer_id, counter in remote_clock.items():
            if peer_id not in self.vector_clock:
                self.vector_clock[peer_id] = counter
            else:
                self.vector_clock[peer_id] = max(self.vector_clock[peer_id], counter)

    def happens_before(self, clock_a: Dict[str, int], clock_b: Dict[str, int]) -> bool:
        """Check if event A happened before event B (causality)"""
        # A < B if: for all peers, A[p] <= B[p] AND exists p where A[p] < B[p]
        all_peers = set(clock_a.keys()) | set(clock_b.keys())

        less_or_equal = True
        strictly_less = False

        for peer in all_peers:
            a_val = clock_a.get(peer, 0)
            b_val = clock_b.get(peer, 0)

            if a_val > b_val:
                less_or_equal = False
                break
            elif a_val < b_val:
                strictly_less = True

        return less_or_equal and strictly_less

    # ============================================
    # MESSAGE BROADCASTING
    # ============================================

    async def broadcast_work_item_created(self, work_item: WorkItem) -> None:
        """Broadcast that a new work item was created"""
        message = WorkflowSyncMessage(
            message_type="work_item_created",
            sender_peer_id=self.peer_id,
            sender_user_id=work_item.created_by,
            work_item_id=work_item.id,
            workflow_id=work_item.workflow_id,
            payload={
                "work_item": work_item.model_dump(),
            },
            vector_clock=self.increment_clock(),
        )

        await self._broadcast_message(message)
        logger.info(f"📤 Broadcast work_item_created: {work_item.id}")

    async def broadcast_work_item_claimed(self, work_item: WorkItem, user_id: str) -> None:
        """Broadcast that a work item was claimed"""
        message = WorkflowSyncMessage(
            message_type="work_item_claimed",
            sender_peer_id=self.peer_id,
            sender_user_id=user_id,
            work_item_id=work_item.id,
            workflow_id=work_item.workflow_id,
            payload={
                "work_item_id": work_item.id,
                "assigned_to": work_item.assigned_to,
                "claimed_at": work_item.claimed_at.isoformat() if work_item.claimed_at else None,
                "status": work_item.status.value,
            },
            vector_clock=self.increment_clock(),
        )

        await self._broadcast_message(message)
        logger.info(f"📤 Broadcast work_item_claimed: {work_item.id}")

    async def broadcast_work_item_completed(self, work_item: WorkItem) -> None:
        """Broadcast that a work item completed a stage"""
        message = WorkflowSyncMessage(
            message_type="work_item_completed",
            sender_peer_id=self.peer_id,
            sender_user_id=work_item.assigned_to or "system",
            work_item_id=work_item.id,
            workflow_id=work_item.workflow_id,
            payload={
                "work_item_id": work_item.id,
                "current_stage_id": work_item.current_stage_id,
                "current_stage_name": work_item.current_stage_name,
                "status": work_item.status.value,
                "data": work_item.data,
                "history": [t.model_dump() for t in work_item.history],
                "completed_at": work_item.completed_at.isoformat() if work_item.completed_at else None,
            },
            vector_clock=self.increment_clock(),
        )

        await self._broadcast_message(message)
        logger.info(f"📤 Broadcast work_item_completed: {work_item.id}")

    async def broadcast_workflow_updated(self, workflow: Workflow) -> None:
        """Broadcast that a workflow definition was updated"""
        message = WorkflowSyncMessage(
            message_type="workflow_updated",
            sender_peer_id=self.peer_id,
            sender_user_id="system",
            workflow_id=workflow.id,
            payload={
                "workflow": workflow.model_dump(),
            },
            vector_clock=self.increment_clock(),
        )

        await self._broadcast_message(message)
        logger.info(f"📤 Broadcast workflow_updated: {workflow.name}")

    async def _broadcast_message(self, message: WorkflowSyncMessage) -> None:
        """
        Broadcast message to all connected peers

        This would integrate with the existing P2P chat service
        In production, you'd call the P2P service's broadcast method
        """
        # Mark as seen locally
        self.seen_messages.add(message.message_id)

        # Serialize message
        payload = message.model_dump()
        payload_json = json.dumps(payload, default=str)

        # TODO: Integrate with p2p_chat_service to actually broadcast
        # For now, just log and queue if offline
        logger.debug(f"Broadcasting message {message.message_id} (type: {message.message_type})")

        # Call registered handlers (for testing/local processing)
        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")

    # ============================================
    # MESSAGE RECEIVING
    # ============================================

    async def handle_incoming_message(self, payload: Dict) -> None:
        """
        Handle incoming sync message from peer

        Args:
            payload: Raw message payload from P2P network
        """
        try:
            # Parse message
            message = WorkflowSyncMessage(**payload)

            # Check if already seen (deduplication)
            if message.message_id in self.seen_messages:
                logger.debug(f"Skipping duplicate message: {message.message_id}")
                return

            self.seen_messages.add(message.message_id)

            # Merge vector clock
            if message.vector_clock:
                self.merge_clock(message.vector_clock)

            # Route based on message type
            if message.message_type == "work_item_created":
                await self._handle_work_item_created(message)
            elif message.message_type == "work_item_claimed":
                await self._handle_work_item_claimed(message)
            elif message.message_type == "work_item_completed":
                await self._handle_work_item_completed(message)
            elif message.message_type == "workflow_updated":
                await self._handle_workflow_updated(message)
            else:
                logger.warning(f"Unknown message type: {message.message_type}")

            logger.info(f"📥 Processed {message.message_type} from {message.sender_peer_id}")

        except Exception as e:
            logger.error(f"Failed to handle incoming message: {e}")

    async def _handle_work_item_created(self, message: WorkflowSyncMessage) -> None:
        """Handle work_item_created message"""
        work_item_data = message.payload.get("work_item")
        if not work_item_data:
            return

        # Check if we already have this work item
        existing = self.storage.get_work_item(work_item_data["id"])
        if existing:
            logger.debug(f"Work item {work_item_data['id']} already exists")
            return

        # Create work item from remote data
        work_item = WorkItem(**work_item_data)

        # Add to orchestrator and storage
        self.orchestrator.active_work_items[work_item.id] = work_item
        self.storage.save_work_item(work_item)

        logger.info(f"✨ Created work item from peer: {work_item.id}")

    async def _handle_work_item_claimed(self, message: WorkflowSyncMessage) -> None:
        """Handle work_item_claimed message"""
        work_item_id = message.payload.get("work_item_id")
        if not work_item_id:
            return

        # Get local work item
        work_item = self.orchestrator.active_work_items.get(work_item_id)
        if not work_item:
            work_item = self.storage.get_work_item(work_item_id)

        if not work_item:
            logger.warning(f"Work item {work_item_id} not found for claim")
            return

        # Check for conflict (already claimed by someone else)
        if work_item.assigned_to and work_item.assigned_to != message.payload.get("assigned_to"):
            logger.warning(f"⚠️  Claim conflict for {work_item_id}: local={work_item.assigned_to}, remote={message.payload.get('assigned_to')}")

            # Conflict resolution: Use vector clocks to determine winner
            # For now, use simple last-write-wins with peer_id tie-breaking
            if message.sender_peer_id > self.peer_id:
                # Remote wins
                work_item.assigned_to = message.payload.get("assigned_to")
                work_item.status = WorkItemStatus(message.payload.get("status", "claimed"))
                work_item.updated_at = datetime.utcnow()

                self.storage.save_work_item(work_item)
                logger.info(f"🔄 Resolved claim conflict (remote wins): {work_item_id}")

        else:
            # No conflict, apply update
            work_item.assigned_to = message.payload.get("assigned_to")
            work_item.status = WorkItemStatus(message.payload.get("status", "claimed"))

            claimed_at_str = message.payload.get("claimed_at")
            if claimed_at_str:
                work_item.claimed_at = datetime.fromisoformat(claimed_at_str)

            work_item.updated_at = datetime.utcnow()

            self.orchestrator.active_work_items[work_item.id] = work_item
            self.storage.save_work_item(work_item)

            logger.info(f"✅ Updated work item claim: {work_item_id}")

    async def _handle_work_item_completed(self, message: WorkflowSyncMessage) -> None:
        """Handle work_item_completed message"""
        work_item_id = message.payload.get("work_item_id")
        if not work_item_id:
            return

        # Get local work item
        work_item = self.orchestrator.active_work_items.get(work_item_id)
        if not work_item:
            work_item = self.storage.get_work_item(work_item_id)

        if not work_item:
            logger.warning(f"Work item {work_item_id} not found for completion")
            return

        # Apply stage completion
        work_item.current_stage_id = message.payload.get("current_stage_id")
        work_item.current_stage_name = message.payload.get("current_stage_name")
        work_item.status = WorkItemStatus(message.payload.get("status"))
        work_item.data = message.payload.get("data", {})

        # Update history
        from workflow_models import StageTransition
        history_data = message.payload.get("history", [])
        work_item.history = [StageTransition(**t) for t in history_data]

        # Check if completed
        if message.payload.get("completed_at"):
            work_item.completed_at = datetime.fromisoformat(message.payload["completed_at"])

        work_item.updated_at = datetime.utcnow()

        self.orchestrator.active_work_items[work_item.id] = work_item
        self.storage.save_work_item(work_item)

        logger.info(f"✅ Updated work item completion: {work_item_id}")

    async def _handle_workflow_updated(self, message: WorkflowSyncMessage) -> None:
        """Handle workflow_updated message"""
        workflow_data = message.payload.get("workflow")
        if not workflow_data:
            return

        # Parse workflow
        workflow = Workflow(**workflow_data)

        # Register with orchestrator (will save to storage)
        self.orchestrator.register_workflow(workflow)

        logger.info(f"✨ Updated workflow from peer: {workflow.name}")

    # ============================================
    # OFFLINE QUEUE
    # ============================================

    async def queue_for_sync(self, message: WorkflowSyncMessage) -> None:
        """Queue message for sync when back online"""
        self.offline_queue.append(message)
        logger.info(f"📮 Queued message for offline sync: {message.message_id}")

    async def replay_offline_queue(self) -> None:
        """Replay queued messages when reconnected"""
        if not self.offline_queue:
            return

        logger.info(f"🔄 Replaying {len(self.offline_queue)} offline messages")

        for message in self.offline_queue:
            try:
                await self._broadcast_message(message)
            except Exception as e:
                logger.error(f"Failed to replay message {message.message_id}: {e}")

        self.offline_queue.clear()
        logger.info("✅ Offline queue replayed")

    # ============================================
    # INTEGRATION HOOKS
    # ============================================

    def register_message_handler(self, handler: Callable) -> None:
        """Register a handler for incoming messages"""
        self.message_handlers.append(handler)

    async def sync_initial_state(self, peer_id: str) -> None:
        """
        Sync full state with a newly connected peer

        Args:
            peer_id: Peer to sync with
        """
        # Send all workflows
        for workflow in self.orchestrator.workflows.values():
            await self.broadcast_workflow_updated(workflow)

        # Send all active work items
        for work_item in self.orchestrator.active_work_items.values():
            if work_item.status not in [WorkItemStatus.COMPLETED, WorkItemStatus.CANCELLED]:
                message = WorkflowSyncMessage(
                    message_type="work_item_created",
                    sender_peer_id=self.peer_id,
                    sender_user_id="system",
                    work_item_id=work_item.id,
                    workflow_id=work_item.workflow_id,
                    payload={"work_item": work_item.model_dump()},
                    vector_clock=self.increment_clock(),
                )
                await self._broadcast_message(message)

        logger.info(f"🔄 Synced initial state with peer {peer_id}")


# ============================================
# GLOBAL INSTANCE
# ============================================

_workflow_sync_instance: Optional[WorkflowP2PSync] = None


def get_workflow_sync() -> Optional[WorkflowP2PSync]:
    """Get the global workflow sync instance"""
    return _workflow_sync_instance


def init_workflow_sync(
    orchestrator: WorkflowOrchestrator,
    storage: WorkflowStorage,
    peer_id: str,
) -> WorkflowP2PSync:
    """Initialize the global workflow sync instance"""
    global _workflow_sync_instance

    if not _workflow_sync_instance:
        _workflow_sync_instance = WorkflowP2PSync(orchestrator, storage, peer_id)

    return _workflow_sync_instance

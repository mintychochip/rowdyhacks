"""WebSocket manager for real-time updates."""

import asyncio

from fastapi import WebSocket


class ConnectionManager:
    """Bidirectional room-based WebSocket connection manager.

    Maintains two indexes---``_rooms`` (room -> websockets) and
    ``_connections`` (websocket -> rooms)---so that disconnecting a
    client automatically cleans up every room it belonged to.
    """

    def __init__(self):
        """Initialize room and connection tracking structures."""
        # room_id -> set of websockets
        self._rooms: dict[str, set[WebSocket]] = {}
        # websocket -> set of room_ids
        self._connections: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str):
        """Accept a WebSocket and register it in a room.

        Behavior:
        1. Accept the WebSocket connection.
        2. Add the websocket to the room set under the lock.
        3. Add the room to the websocket's connection tracking.

        Raises: None
        Side Effects: Mutates ``_rooms`` and ``_connections`` dicts.
        Dependencies: fastapi.WebSocket.
        Consumers: WebSocket endpoint handlers.
        """
        await websocket.accept()

        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(websocket)

            if websocket not in self._connections:
                self._connections[websocket] = set()
            self._connections[websocket].add(room)

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket from all rooms and drop tracking.

        Behavior:
        1. Pop all rooms the websocket belonged to.
        2. Remove the websocket from each room set.
        3. Delete empty room sets to free memory.

        Raises: None
        Side Effects: Mutates ``_rooms`` and ``_connections`` dicts.
        Dependencies: None
        Consumers: WebSocket disconnect handlers, dead-connection cleanup.
        """
        async with self._lock:
            rooms = self._connections.pop(websocket, set())
            for room in rooms:
                if room in self._rooms:
                    self._rooms[room].discard(websocket)
                    if not self._rooms[room]:
                        del self._rooms[room]

    async def join_room(self, websocket: WebSocket, room: str):
        """Add an existing connection to an additional room.

        Behavior:
        1. Create the room set if it does not exist.
        2. Add the websocket to the room set.
        3. Track the room in the websocket's connection set.

        Raises: None
        Side Effects: Mutates ``_rooms`` and ``_connections`` dicts.
        Dependencies: None
        Consumers: Room subscription handlers.
        """
        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(websocket)

            if websocket not in self._connections:
                self._connections[websocket] = set()
            self._connections[websocket].add(room)

    async def leave_room(self, websocket: WebSocket, room: str):
        """Remove a connection from a single room.

        Behavior:
        1. Remove the websocket from the room set.
        2. Delete the room set if it becomes empty.
        3. Remove the room from the websocket's connection tracking.

        Raises: None
        Side Effects: Mutates ``_rooms`` and ``_connections`` dicts.
        Dependencies: None
        Consumers: Room unsubscription handlers.
        """
        async with self._lock:
            if room in self._rooms:
                self._rooms[room].discard(websocket)
                if not self._rooms[room]:
                    del self._rooms[room]

            if websocket in self._connections:
                self._connections[websocket].discard(room)

    async def broadcast_to_room(self, room: str, message: dict):
        """Send a JSON message to every connection in a room.

        Behavior:
        1. Copy the current connection set for the room under the lock.
        2. Iterate connections and send the JSON message.
        3. Collect dead connections that raise an exception.
        4. Remove dead connections to prevent accumulation.

        Raises: None
        Side Effects: Sends data over WebSockets; mutates ``_rooms`` and ``_connections`` on dead cleanup.
        Dependencies: fastapi.WebSocket.send_json.
        Consumers: Event notification dispatchers.
        """
        async with self._lock:
            connections = self._rooms.get(room, set()).copy()

        # Send to all connections (outside lock)
        dead_connections = []
        for conn in connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead_connections.append(conn)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for conn in dead_connections:
                    await self.disconnect(conn)

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send a JSON message to a single WebSocket.

        Behavior:
        1. Attempt to send the JSON message.
        2. Disconnect the websocket on any send failure.

        Raises: None
        Side Effects: Sends data over WebSocket; may mutate room state on disconnect.
        Dependencies: fastapi.WebSocket.send_json.
        Consumers: Direct message handlers.
        """
        try:
            await websocket.send_json(message)
        except Exception:
            await self.disconnect(websocket)


# Global manager instance
manager = ConnectionManager()


# Room name helpers
def hackathon_room(hackathon_id: str) -> str:
    """Build the room name for a hackathon broadcast channel.

    Behavior:
    1. Prefix the hackathon ID with ``hackathon:``.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: hackathon broadcast helpers.
    """
    return f"hackathon:{hackathon_id}"


def submission_room(submission_id: str) -> str:
    """Build the room name for a submission broadcast channel.

    Behavior:
    1. Prefix the submission ID with ``submission:``.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: submission broadcast helpers.
    """
    return f"submission:{submission_id}"


def user_room(user_id: str) -> str:
    """Build the room name for a user-private broadcast channel.

    Behavior:
    1. Prefix the user ID with ``user:``.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: user-private broadcast helpers.
    """
    return f"user:{user_id}"


def check_updates_room(check_id: str) -> str:
    """Build the room name for a check-update stream.

    Behavior:
    1. Prefix the check ID with ``check:``.

    Raises: None
    Side Effects: None (read-only).
    Dependencies: None
    Consumers: check-progress broadcast helpers.
    """
    return f"check:{check_id}"


# Message builders
async def notify_check_progress(submission_id: str, check_name: str, status: str, progress: dict):
    """Broadcast a check-progress update to the submission room.

    Behavior:
    1. Build the submission room name.
    2. Broadcast a ``check_progress`` payload to that room.

    Raises: None
    Side Effects: Sends WebSocket messages.
    Dependencies: manager.broadcast_to_room, submission_room.
    Consumers: analysis pipeline progress updates.
    """
    await manager.broadcast_to_room(
        submission_room(submission_id),
        {
            "type": "check_progress",
            "submission_id": submission_id,
            "check_name": check_name,
            "status": status,
            "progress": progress,
        },
    )


async def notify_analysis_complete(submission_id: str, verdict: dict):
    """Broadcast the final analysis verdict to the submission room.

    Behavior:
    1. Build the submission room name.
    2. Broadcast an ``analysis_complete`` payload to that room.

    Raises: None
    Side Effects: Sends WebSocket messages.
    Dependencies: manager.broadcast_to_room, submission_room.
    Consumers: analysis pipeline completion handler.
    """
    await manager.broadcast_to_room(
        submission_room(submission_id),
        {
            "type": "analysis_complete",
            "submission_id": submission_id,
            "verdict": verdict,
        },
    )


async def notify_registration_update(hackathon_id: str, registration: dict):
    """Broadcast a registration change to the hackathon room.

    Behavior:
    1. Build the hackathon room name.
    2. Broadcast a ``registration_update`` payload to that room.

    Raises: None
    Side Effects: Sends WebSocket messages.
    Dependencies: manager.broadcast_to_room, hackathon_room.
    Consumers: registration event handlers.
    """
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "registration_update",
            "hackathon_id": hackathon_id,
            "registration": registration,
        },
    )


async def notify_judging_update(hackathon_id: str, project_id: str, scores: dict):
    """Broadcast a judging score update to the hackathon room.

    Behavior:
    1. Build the hackathon room name.
    2. Broadcast a ``judging_update`` payload to that room.

    Raises: None
    Side Effects: Sends WebSocket messages.
    Dependencies: manager.broadcast_to_room, hackathon_room.
    Consumers: judging score event handlers.
    """
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "judging_update",
            "hackathon_id": hackathon_id,
            "project_id": project_id,
            "scores": scores,
        },
    )


async def notify_announcement(hackathon_id: str, announcement: dict):
    """Broadcast a new announcement to the hackathon room.

    Behavior:
    1. Build the hackathon room name.
    2. Broadcast an ``announcement`` payload to that room.

    Raises: None
    Side Effects: Sends WebSocket messages.
    Dependencies: manager.broadcast_to_room, hackathon_room.
    Consumers: announcement event handlers.
    """
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "announcement",
            "hackathon_id": hackathon_id,
            "announcement": announcement,
        },
    )

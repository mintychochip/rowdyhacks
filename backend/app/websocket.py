"""WebSocket manager for real-time updates."""
import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json


class ConnectionManager:
    """Manage WebSocket connections with room-based subscription."""
    
    def __init__(self):
        # room_id -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # websocket -> set of room_ids
        self._connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, room: str):
        """Accept connection and add to room."""
        await websocket.accept()
        
        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(websocket)
            
            if websocket not in self._connections:
                self._connections[websocket] = set()
            self._connections[websocket].add(room)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove connection from all rooms."""
        async with self._lock:
            rooms = self._connections.pop(websocket, set())
            for room in rooms:
                if room in self._rooms:
                    self._rooms[room].discard(websocket)
                    if not self._rooms[room]:
                        del self._rooms[room]
    
    async def join_room(self, websocket: WebSocket, room: str):
        """Add connection to a room."""
        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(websocket)
            
            if websocket not in self._connections:
                self._connections[websocket] = set()
            self._connections[websocket].add(room)
    
    async def leave_room(self, websocket: WebSocket, room: str):
        """Remove connection from a room."""
        async with self._lock:
            if room in self._rooms:
                self._rooms[room].discard(websocket)
                if not self._rooms[room]:
                    del self._rooms[room]
            
            if websocket in self._connections:
                self._connections[websocket].discard(room)
    
    async def broadcast_to_room(self, room: str, message: dict):
        """Send message to all connections in a room."""
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
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            await self.disconnect(websocket)


# Global manager instance
manager = ConnectionManager()


# Room name helpers
def hackathon_room(hackathon_id: str) -> str:
    return f"hackathon:{hackathon_id}"


def submission_room(submission_id: str) -> str:
    return f"submission:{submission_id}"


def user_room(user_id: str) -> str:
    return f"user:{user_id}"


def check_updates_room(check_id: str) -> str:
    return f"check:{check_id}"


# Message builders
async def notify_check_progress(submission_id: str, check_name: str, status: str, progress: dict):
    """Notify about check progress."""
    await manager.broadcast_to_room(
        submission_room(submission_id),
        {
            "type": "check_progress",
            "submission_id": submission_id,
            "check_name": check_name,
            "status": status,
            "progress": progress,
        }
    )


async def notify_analysis_complete(submission_id: str, verdict: dict):
    """Notify that analysis is complete."""
    await manager.broadcast_to_room(
        submission_room(submission_id),
        {
            "type": "analysis_complete",
            "submission_id": submission_id,
            "verdict": verdict,
        }
    )


async def notify_registration_update(hackathon_id: str, registration: dict):
    """Notify about registration changes."""
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "registration_update",
            "hackathon_id": hackathon_id,
            "registration": registration,
        }
    )


async def notify_judging_update(hackathon_id: str, project_id: str, scores: dict):
    """Notify about judging updates."""
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "judging_update",
            "hackathon_id": hackathon_id,
            "project_id": project_id,
            "scores": scores,
        }
    )


async def notify_announcement(hackathon_id: str, announcement: dict):
    """Notify about new announcement."""
    await manager.broadcast_to_room(
        hackathon_room(hackathon_id),
        {
            "type": "announcement",
            "hackathon_id": hackathon_id,
            "announcement": announcement,
        }
    )

"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.auth import get_current_user_ws
from app.websocket import hackathon_room, manager, submission_room, user_room

router = APIRouter(prefix="/api/ws", tags=["websocket"])


@router.websocket("/hackathon/{hackathon_id}")
async def hackathon_websocket(websocket: WebSocket, hackathon_id: str):
    """Subscribe to hackathon updates (registrations, announcements, judging).

    Behavior:
    1. Connect the WebSocket to the hackathon room.
    2. Listen for incoming text messages in a loop.
    3. Respond to "ping" with "pong".

    Raises: WebSocketDisconnect on client disconnect.
    Side Effects: Mutates WebSocket connection state.
    Dependencies: app.websocket.manager, app.websocket.hackathon_room.
    Consumers: GET /api/ws/hackathon/{hackathon_id}, live updates.
    """
    await manager.connect(websocket, hackathon_room(hackathon_id))
    try:
        while True:
            # Keep connection alive and handle client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.websocket("/submission/{submission_id}")
async def submission_websocket(websocket: WebSocket, submission_id: str):
    """Subscribe to submission analysis progress.

    Behavior:
    1. Connect the WebSocket to the submission room.
    2. Listen for incoming text messages in a loop.
    3. Respond to "ping" with "pong".

    Raises: WebSocketDisconnect on client disconnect.
    Side Effects: Mutates WebSocket connection state.
    Dependencies: app.websocket.manager, app.websocket.submission_room.
    Consumers: GET /api/ws/submission/{submission_id}, live updates.
    """
    await manager.connect(websocket, submission_room(submission_id))
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.websocket("/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: str, current_user: dict | None = Depends(get_current_user_ws)):
    """Subscribe to personal notifications (requires auth).

    Behavior:
    1. Verify the current user matches the requested user_id.
    2. Close with 403 if unauthorized.
    3. Connect the WebSocket to the user room.
    4. Listen for incoming text messages in a loop.
    5. Respond to "ping" with "pong".

    Raises: WebSocketDisconnect on client disconnect.
    Side Effects: Mutates WebSocket connection state.
    Dependencies: app.websocket.manager, app.websocket.user_room, app.auth.get_current_user_ws.
    Consumers: GET /api/ws/user/{user_id}, personal notifications.
    """
    # Verify user can only connect to their own room
    if not current_user or str(current_user.get("id")) != user_id:
        await websocket.close(code=403)
        return

    await manager.connect(websocket, user_room(user_id))
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

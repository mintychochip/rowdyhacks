"""QR code image serving endpoint."""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.qr_generator import generate_qr_png

router = APIRouter(prefix="/api", tags=["qr"])


@router.get("/qr")
async def get_qr_image(data: str = Query(..., description="Data to encode in QR code")):
    """Serve a QR code PNG image for the given data.

    Behavior:
    1. Generate a PNG QR code from the provided data string.
    2. Return it as a FastAPI Response with image/png content type.

    Raises: None
    Side Effects: None (read-only, CPU-bound image generation).
    Dependencies: app.qr_generator.generate_qr_png.
    Consumers: GET /api/qr, badge/QR display.
    """
    png = generate_qr_png(data)
    return Response(content=png, media_type="image/png")

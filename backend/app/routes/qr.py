"""QR code image serving endpoint."""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.qr_generator import generate_qr_png

router = APIRouter(prefix="/api", tags=["qr"])


@router.get("/qr")
async def get_qr_image(data: str = Query(..., description="Data to encode in QR code")):
    """Serve a QR code PNG image for the given data."""
    png = generate_qr_png(data)
    return Response(content=png, media_type="image/png")

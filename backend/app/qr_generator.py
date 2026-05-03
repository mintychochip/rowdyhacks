"""QR code image generation."""

import io

import qrcode
from qrcode.image.pil import PilImage


def generate_qr_png(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """Generate a QR code PNG image for the given URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_image(url: str, box_size: int = 10, border: int = 4):
    """Generate a QR code PIL Image for use in wallet passes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

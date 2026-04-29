"""Apple Wallet .pkpass generation with manual pass.json and PKCS7 signing."""

import hashlib
import io
import json
import logging
import os
import struct
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.qr_generator import generate_qr_png

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.primitives.serialization import pkcs7

logger = logging.getLogger(__name__)


def _make_icon_png(size: int = 180, color: tuple[int, int, int] = (28, 28, 30)) -> bytes:
    """Generate a minimal solid-color PNG icon for the wallet pass."""
    import zlib

    r, g, b = color

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)
    raw = b""
    pixel = bytes([r, g, b])
    for _ in range(size):
        raw += b"\x00"  # filter byte
        raw += pixel * size
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _generate_manifest(files: dict[str, bytes]) -> bytes:
    """Generate manifest.json (SHA1 hashes of all files)."""
    manifest: dict[str, str] = {}
    for filename, data in files.items():
        manifest[filename] = hashlib.sha1(data).hexdigest()
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign_manifest_cryptography(
    manifest_bytes: bytes,
    cert_path: str,
    cert_password: str,
) -> bytes | None:
    """Create a PKCS7 detached DER signature using the ``cryptography`` library.

    Returns the DER-encoded signature bytes, or None on failure.
    """
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12, pkcs7
        from cryptography.hazmat.primitives import hashes, serialization

        with open(cert_path, "rb") as f:
            p12_data = f.read()

        p12_password: bytes | None = cert_password.encode("utf-8") if cert_password else None
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            p12_data,
            p12_password,
        )

        if private_key is None or certificate is None:
            logger.error("PKCS12 file did not contain a private key and certificate")
            return None

        builder = pkcs7.PKCS7SignatureBuilder().set_data(manifest_bytes)

        # Add signer with the cert + key
        builder = builder.add_signer(certificate, private_key, hashes.SHA256())

        # Add any additional CA certificates from the bundle
        for extra_cert in additional_certs or []:
            if isinstance(extra_cert, pkcs12.PKCS12Certificate):
                builder = builder.add_certificate(extra_cert.certificate)
            else:
                builder = builder.add_certificate(extra_cert)

        signature = builder.sign(
            serialization.Encoding.DER,
            [pkcs7.PKCS7Options.DetachedSignature],
        )
        return signature
    except Exception as exc:
        logger.error("Cryptography PKCS7 signing failed: %s", exc)
        return None


def _sign_manifest_openssl(
    manifest_bytes: bytes,
    cert_path: str,
    cert_password: str,
) -> bytes | None:
    """Fallback: create PKCS7 detached signature via openssl CLI."""
    mname = sname = None
    try:
        with (
            tempfile.NamedTemporaryFile(suffix=".manifest", delete=False) as mf,
            tempfile.NamedTemporaryFile(suffix=".sig", delete=False) as sf,
        ):
            mf.write(manifest_bytes)
            mname = mf.name
            sname = sf.name

        result = subprocess.run(
            [
                "openssl", "smime",
                "-sign",
                "-in", mname,
                "-out", sname,
                "-signer", cert_path,
                "-passin", f"pass:{cert_password}",
                "-outform", "DER",
                "-binary",
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("openssl smime sign failed: %s", result.stderr.decode().strip())
            return None

        with open(sname, "rb") as f:
            return f.read()
    except Exception as exc:
        logger.error("openssl signing failed: %s", exc)
        return None
    finally:
        for p in (mname, sname):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def _sign_manifest(
    manifest_bytes: bytes,
    cert_path: str,
    cert_password: str,
) -> bytes | None:
    """Sign the manifest.  Prefers the ``cryptography`` library over CLI openssl."""
    sig = _sign_manifest_cryptography(manifest_bytes, cert_path, cert_password)
    if sig is not None:
        return sig
    return _sign_manifest_openssl(manifest_bytes, cert_path, cert_password)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apple_pass_available() -> bool:
    """Check whether Apple Wallet pass generation is configured."""
    from app.config import settings

    return (
        bool(settings.apple_pass_cert_path)
        and bool(settings.apple_team_identifier)
        and os.path.exists(settings.apple_pass_cert_path)
    )


def generate_apple_pass(
    registration_id: str,
    participant_name: str,
    team_name: str | None,
    hackathon_name: str,
    start_date: str,
    end_date: str,
    qr_url: str,
    checkin_status: str = "Accepted",
) -> bytes | None:
    """Generate a .pkpass file.

    Builds pass.json, manifest.json, applies a PKCS7 detached signature
    (via the ``cryptography`` library or ``openssl`` CLI fallback), and
    zips everything into a ``.pkpass`` byte string.

    Returns ``None`` when Apple Wallet is not configured or signing fails.
    """
    if not apple_pass_available():
        return None

    from app.config import settings

    # ── QR code image ──────────────────────────────────────────────────
    qr_png = generate_qr_png(qr_url)

    # ── Icon / logo images ─────────────────────────────────────────────
    icon = _make_icon_png(180)
    icon_2x = _make_icon_png(360)

    # ── pass.json ──────────────────────────────────────────────────────
    pass_json: dict = {
        "formatVersion": 1,
        "passTypeIdentifier": settings.apple_pass_type_identifier,
        "teamIdentifier": settings.apple_team_identifier,
        "serialNumber": registration_id,
        "organizationName": hackathon_name,
        "description": f"{hackathon_name} Check-in Pass",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": "rgb(28, 28, 30)",
        "labelColor": "rgb(108, 92, 231)",
        "barcode": {
            "message": qr_url,
            "format": "PKBarcodeFormatQR",
            "messageEncoding": "iso-8859-1",
            "altText": f"Check-in: {team_name or participant_name}",
        },
        "barcodes": [
            {
                "message": qr_url,
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
                "altText": f"Check-in: {team_name or participant_name}",
            }
        ],
        "relevantDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "locations": [],
        "maxDistance": 0,
        "storeCard": {
            "headerFields": [
                {"key": "event", "label": "Event", "value": hackathon_name},
            ],
            "primaryFields": [
                {"key": "name", "label": "Participant", "value": participant_name},
            ],
            "secondaryFields": [
                {"key": "team", "label": "Team", "value": team_name or "Solo"},
            ],
            "auxiliaryFields": [
                {
                    "key": "dates",
                    "label": "Event Dates",
                    "value": f"{start_date} \u2014 {end_date}",
                },
            ],
            "backFields": [
                {"key": "reg_id", "label": "Registration ID", "value": registration_id},
                {"key": "status", "label": "Status", "value": checkin_status},
            ],
        },
    }

    pass_json_bytes = json.dumps(pass_json, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # ── Assemble all files ─────────────────────────────────────────────
    files: dict[str, bytes] = {
        "pass.json": pass_json_bytes,
        "barcode.png": qr_png,
        "icon.png": icon,
        "icon@2x.png": icon_2x,
        "logo.png": icon,
        "logo@2x.png": icon_2x,
    }

    # Fetch custom logo from URL if configured
    if settings.wallet_logo_url:
        try:
            import httpx

            resp = httpx.get(settings.wallet_logo_url, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 100:
                files["logo.png"] = resp.content
                files["logo@2x.png"] = resp.content  # reuse; wallet handles scaling
        except Exception as exc:
            logger.warning("Failed to fetch wallet_logo_url %s: %s", settings.wallet_logo_url, exc)

    # ── manifest.json ──────────────────────────────────────────────────
    manifest_bytes = _generate_manifest(files)
    files["manifest.json"] = manifest_bytes

    # ── signature ──────────────────────────────────────────────────────
    sig = _sign_manifest(manifest_bytes, settings.apple_pass_cert_path, settings.apple_pass_cert_password)
    if sig is None:
        logger.error("Apple pass signing failed — returning None for 503 response.")
        return None
    files["signature"] = sig

    # ── Zip into .pkpass ───────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(files.items()):
            zf.writestr(name, data)
    return buf.getvalue()

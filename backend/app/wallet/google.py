"""Google Wallet pass generation with Google Wallet API integration."""

import json
import logging
import os
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Google Wallet REST API base
_WALLET_BASE = "https://walletobjects.googleapis.com/v1"

# Issuer ID for create-object API calls; injected once credentials are loaded
_issuer_id: str = ""


def _load_credentials() -> tuple | None:
    """Load and return Google Wallet service account credentials.

    Returns (credentials, issuer_id) or None if not configured.
    """
    from app.config import settings

    global _issuer_id
    if not _issuer_id:
        _issuer_id = settings.google_wallet_issuer_id

    if not settings.google_wallet_credentials_path or not os.path.exists(settings.google_wallet_credentials_path):
        return None
    if not _issuer_id:
        return None

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        creds = service_account.Credentials.from_service_account_file(
            settings.google_wallet_credentials_path,
            scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
        )
        creds.refresh(Request())
        return creds, _issuer_id
    except Exception as exc:
        logger.warning("Failed to load Google Wallet credentials: %s", exc)
        return None


def _get_headers(creds) -> dict:
    """Build auth headers for Google Wallet API calls."""
    if hasattr(creds, "token"):
        return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    return {}


def _ensure_class_exists(creds, issuer_id: str) -> bool:
    """Create the GenericClass if it does not already exist.

    The class is identified by ``{issuer_id}.hackverify_checkin``.
    Returns True on success (class exists now), False on failure.
    """
    class_id = f"{issuer_id}.hackverify_checkin"
    import httpx

    url = f"{_WALLET_BASE}/genericClass/{class_id}"
    headers = _get_headers(creds)

    # Check if it already exists
    resp = httpx.get(url, headers=headers, timeout=15)
    if resp.status_code == 200:
        return True

    # Create it
    payload = {
        "id": class_id,
        "classTemplateInfo": {
            "cardTemplateOverride": {
                "cardRowTemplateInfos": [
                    {
                        "twoItems": {
                            "startItem": {"firstValue": {}},
                            "endItem": {"firstValue": {}},
                        }
                    }
                ]
            }
        },
        "viewUnlockRequirement": "VIEW_UNLOCK_REQUIREMENT_UNSPECIFIED",
        "multipleDevicesAndHoldersAllowedStatus": "MULTIPLE_DEVICES_AND_HOLDERS_ALLOWED_STATUS_UNSPECIFIED",
        "callbackOptions": {"url": ""},
        "messages": [],
    }
    # Use insert (POST) — will fail if already exists, but we checked above
    resp = httpx.post(
        f"{_WALLET_BASE}/genericClass",
        headers=headers,
        content=json.dumps(payload),
        timeout=15,
    )
    if resp.status_code == 200:
        logger.info("Created Google Wallet class: %s", class_id)
        return True
    # 409 = already exists (race condition); 200 = created
    if resp.status_code == 409:
        return True
    logger.warning("Failed to create generic class %s: %s %s", class_id, resp.status_code, resp.text)
    return False


def _create_pass_object(
    creds,
    issuer_id: str,
    registration_id: str,
    participant_name: str,
    team_name: str | None,
    hackathon_name: str,
    start_date: str,
    end_date: str,
    qr_url: str,
    checkin_status: str = "Accepted",
) -> dict | None:
    """Insert a GenericObject via the Google Wallet API.

    Returns the created object dict, or None on failure.
    """
    from app.config import settings

    object_id = f"{issuer_id}.{registration_id}"
    class_id = f"{issuer_id}.hackverify_checkin"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "genericType": "GENERIC_TYPE_UNSPECIFIED",
        "hexBackgroundColor": "#1c1c1e",
        "logo": {
            "sourceUri": {
                "uri": settings.wallet_logo_url or "",
                "description": "HackVerify logo",
            }
        },
        "cardTitle": {
            "defaultValue": {"language": "en", "value": hackathon_name},
        },
        "header": {
            "defaultValue": {"language": "en", "value": participant_name},
        },
        "subheader": {
            "defaultValue": {"language": "en", "value": f"Team: {team_name or 'Solo'}"},
        },
        "barcode": {
            "type": "QR_CODE",
            "value": qr_url,
            "alternateText": f"Check-in: {team_name or participant_name}",
        },
        "textModulesData": [
            {"id": "dates", "header": "Event Dates", "body": f"{start_date} \u2014 {end_date}"},
            {"id": "status", "header": "Status", "body": checkin_status},
            {"id": "reg_id", "header": "Registration ID", "body": registration_id},
        ],
        "linksModuleData": {
            "uris": [
                {
                    "uri": qr_url,
                    "description": "Check-in QR Code",
                }
            ]
        },
        "infoModuleData": {
            "hexFontColor": "#ffffff",
            "hexBackgroundColor": "#1c1c1e",
        },
        "validTimeInterval": {
            "start": {"date": start_date},
            "end": {"date": end_date},
        },
    }

    import httpx

    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    url = f"{_WALLET_BASE}/genericObject"

    resp = httpx.post(url, headers=headers, content=json.dumps(payload), timeout=15)
    if resp.status_code == 200:
        return resp.json()

    # 409 = already exists — update instead
    if resp.status_code == 409:
        update_url = f"{_WALLET_BASE}/genericObject/{object_id}"
        resp2 = httpx.patch(update_url, headers=headers, content=json.dumps(payload), timeout=15)
        if resp2.status_code == 200:
            return resp2.json()
        logger.warning("Failed to update generic object %s: %s %s", object_id, resp2.status_code, resp2.text)
        return None

    logger.warning("Failed to insert generic object %s: %s %s", object_id, resp.status_code, resp.text)
    return None


def google_wallet_available() -> bool:
    """Check if Google Wallet is configured with valid credentials."""
    try:
        result = _load_credentials()
        return result is not None
    except Exception:
        return False


def build_google_wallet_pass_object(
    registration_id: str,
    participant_name: str,
    team_name: str | None,
    hackathon_name: str,
    start_date: str,
    end_date: str,
    qr_url: str,
    checkin_status: str = "Accepted",
) -> dict | None:
    """Build the Google Wallet GenericObject via the API.

    This calls the Google Wallet REST API to create/update a GenericObject
    for the given registration and returns the API response object.
    Returns None if Google Wallet is not configured.
    """
    creds_and_id = _load_credentials()
    if creds_and_id is None:
        return None

    creds, issuer_id = creds_and_id

    # Ensure the class exists (one-time setup per issuer)
    if not _ensure_class_exists(creds, issuer_id):
        logger.error("Google Wallet class could not be created; pass generation aborted.")
        return None

    return _create_pass_object(
        creds,
        issuer_id,
        registration_id,
        participant_name,
        team_name,
        hackathon_name,
        start_date,
        end_date,
        qr_url,
        checkin_status,
    )


def get_google_wallet_save_url(pass_object: dict | None) -> str | None:
    """Extract the save-to-wallet URL from a GenericObject response.

    If the API response contains a ``saveUri`` field it is returned directly.
    Otherwise a JWT-based save URL is constructed.
    """
    if pass_object is None:
        return None

    # Google Wallet API sometimes returns saveUri directly
    save_uri = pass_object.get("saveUri")
    if save_uri:
        return save_uri

    # Fallback: build a JWT-signed save URL using the service account
    creds_and_id = _load_credentials()
    if creds_and_id is None:
        return None

    creds, issuer_id = creds_and_id
    object_id = pass_object.get("id", "")
    if not object_id:
        return None

    # Build a JWT for the client-side Google Pay save handler
    jwt_payload = {
        "iss": getattr(creds, "service_account_email", issuer_id),
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "genericObjects": [
                pass_object,
            ]
        },
    }

    try:
        # Sign with the service account's private key using jose
        from jose import jwt as pyjwt

        private_key = creds.private_key if hasattr(creds, "private_key") else None
        if not private_key and hasattr(creds, "_private_key"):
            private_key = creds._private_key
        if not private_key:
            # Fallback: load from file
            from app.config import settings

            if settings.google_wallet_credentials_path:
                with open(settings.google_wallet_credentials_path) as f:
                    sa_data = json.load(f)
                private_key = sa_data.get("private_key")

        if private_key:
            signed_jwt = pyjwt.encode(jwt_payload, private_key, algorithm="RS256")
            return f"https://pay.google.com/gp/v/save/{signed_jwt}"

        logger.warning("No private key available for JWT signing")
        return None
    except Exception as exc:
        logger.warning("Failed to build JWT save URL: %s", exc)
        return None

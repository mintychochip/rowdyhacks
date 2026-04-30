"""Wallet configuration and test endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.auth import decode_token
from app.wallet import (
    apple_pass_available,
    google_wallet_available,
    generate_apple_pass,
    build_google_wallet_pass_object,
    get_google_wallet_save_url,
)

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


def _get_current_user_payload(authorization: str | None):
    """Extract and validate the current user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


class WalletStatusResponse(BaseModel):
    apple_wallet_available: bool
    google_wallet_available: bool
    config_complete: bool


class TestPassRequest(BaseModel):
    participant_name: str = "Test User"
    team_name: Optional[str] = "Test Team"
    hackathon_name: str = "Test Hackathon"
    start_date: str = "2026-05-01"
    end_date: str = "2026-05-02"


@router.get("/status", response_model=WalletStatusResponse)
async def wallet_status():
    """Check if wallet integration is properly configured."""
    apple_available = apple_pass_available()
    google_available = google_wallet_available()
    
    return WalletStatusResponse(
        apple_wallet_available=apple_available,
        google_wallet_available=google_available,
        config_complete=apple_available or google_available,
    )


@router.post("/test/apple")
async def test_apple_wallet(
    request: TestPassRequest,
    authorization: str | None = Header(alias="Authorization"),
):
    """Generate a test Apple Wallet pass."""
    _get_current_user_payload(authorization)
    
    if not apple_pass_available():
        raise HTTPException(
            status_code=503,
            detail="Apple Wallet not configured. Run setup-apple-wallet.sh first."
        )
    
    # Generate test pass
    pkpass = generate_apple_pass(
        registration_id="test-reg-123",
        participant_name=request.participant_name,
        team_name=request.team_name,
        hackathon_name=request.hackathon_name,
        start_date=request.start_date,
        end_date=request.end_date,
        qr_url=f"https://example.com/checkin/test-reg-123",
        checkin_status="Accepted",
    )
    
    if pkpass is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate Apple pass. Check server logs for details."
        )
    
    return Response(
        content=pkpass,
        media_type="application/vnd.apple.pkpass",
        headers={
            "Content-Disposition": "attachment; filename=hackverify-test.pkpass"
        }
    )


@router.post("/test/google")
async def test_google_wallet(
    request: TestPassRequest,
    authorization: str | None = Header(alias="Authorization"),
):
    """Generate a test Google Wallet pass."""
    _get_current_user_payload(authorization)
    
    if not google_wallet_available():
        raise HTTPException(
            status_code=503,
            detail="Google Wallet not configured. Run setup-google-wallet.sh first."
        )
    
    # Create pass object via API
    pass_obj = build_google_wallet_pass_object(
        registration_id="test-reg-123",
        participant_name=request.participant_name,
        team_name=request.team_name,
        hackathon_name=request.hackathon_name,
        start_date=request.start_date,
        end_date=request.end_date,
        qr_url=f"https://example.com/checkin/test-reg-123",
        checkin_status="Accepted",
    )
    
    if pass_obj is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Google Wallet pass. Check server logs for details."
        )
    
    # Get save URL
    save_url = get_google_wallet_save_url(pass_obj)
    
    return JSONResponse({
        "save_url": save_url,
        "pass_id": pass_obj.get("id"),
        "instructions": "Open the save_url in a browser to add the pass to Google Wallet",
    })


@router.get("/diagnostics")
async def wallet_diagnostics():
    """Detailed diagnostics for wallet configuration."""
    import os
    from app.config import settings
    
    diagnostics = {
        "apple": {
            "configured": False,
            "cert_path_set": bool(settings.apple_pass_cert_path),
            "cert_exists": False,
            "cert_readable": False,
            "team_id_set": bool(settings.apple_team_identifier),
            "pass_type_id_set": bool(settings.apple_pass_type_identifier),
            "errors": [],
        },
        "google": {
            "configured": False,
            "credentials_path_set": bool(settings.google_wallet_credentials_path),
            "credentials_exist": False,
            "credentials_readable": False,
            "issuer_id_set": bool(settings.google_wallet_issuer_id),
            "errors": [],
        },
    }
    
    # Check Apple configuration
    if settings.apple_pass_cert_path:
        diagnostics["apple"]["cert_exists"] = os.path.exists(settings.apple_pass_cert_path)
        if diagnostics["apple"]["cert_exists"]:
            try:
                with open(settings.apple_pass_cert_path, 'rb') as f:
                    f.read(1)
                diagnostics["apple"]["cert_readable"] = True
            except Exception as e:
                diagnostics["apple"]["errors"].append(f"Cannot read certificate: {e}")
    
    if not settings.apple_team_identifier:
        diagnostics["apple"]["errors"].append("Apple Team ID not set")
    
    if not settings.apple_pass_cert_path:
        diagnostics["apple"]["errors"].append("Certificate path not set")
    elif not os.path.exists(settings.apple_pass_cert_path):
        diagnostics["apple"]["errors"].append(f"Certificate not found at: {settings.apple_pass_cert_path}")
    
    diagnostics["apple"]["configured"] = apple_pass_available()
    
    # Check Google configuration
    if settings.google_wallet_credentials_path:
        diagnostics["google"]["credentials_exist"] = os.path.exists(settings.google_wallet_credentials_path)
        if diagnostics["google"]["credentials_exist"]:
            try:
                with open(settings.google_wallet_credentials_path, 'r') as f:
                    f.read(1)
                diagnostics["google"]["credentials_readable"] = True
            except Exception as e:
                diagnostics["google"]["errors"].append(f"Cannot read credentials: {e}")
    
    if not settings.google_wallet_issuer_id:
        diagnostics["google"]["errors"].append("Google Wallet Issuer ID not set")
    
    if not settings.google_wallet_credentials_path:
        diagnostics["google"]["errors"].append("Credentials path not set")
    elif not os.path.exists(settings.google_wallet_credentials_path):
        diagnostics["google"]["errors"].append(f"Credentials not found at: {settings.google_wallet_credentials_path}")
    
    diagnostics["google"]["configured"] = google_wallet_available()
    
    return diagnostics

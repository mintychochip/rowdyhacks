"""Tests for the TypeScript SDK generator script."""

import subprocess
import sys
from pathlib import Path


def test_generate_sdk_creates_output_file():
    """Running the generator script must create sdk/openhack-client.ts."""
    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent
    script = backend_dir / "scripts" / "generate-sdk.py"
    out_file = project_root / "sdk" / "openhack-client.ts"

    # Ensure a clean state
    if out_file.exists():
        out_file.unlink()

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert out_file.exists(), f"Expected output file {out_file} was not created"

    content = out_file.read_text(encoding="utf-8")

    # Required convenience methods must exist with exact signatures
    assert "async getConfig(): Promise<Record<string, string>>" in content
    assert "async getThemeCss(): Promise<string>" in content
    assert "async updateConfig(updates: Record<string, string>): Promise<{ updated: string[] }>" in content
    assert "async uploadAsset(file: File | Blob, key?: string | null): Promise<{ key: string; url: string }>" in content
    assert "async getBranding(): Promise<BrandingResponse>" in content

    # Core interfaces must exist
    assert "export interface BrandingResponse" in content
    assert "export interface AssetUploadResponse" in content
    assert "export interface ConfigUpdateResponse" in content
    assert "export interface ConfigKeyResponse" in content
    assert "export class OpenHackClient" in content

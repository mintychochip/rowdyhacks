"""Pydantic schemas for the config router."""

from pydantic import BaseModel


class BrandingResponse(BaseModel):
    """Pydantic schema for public hackathon branding configuration.

    Behavior:
    1. Returns seven branding fields: name, tagline, email, primary color, logo URL, favicon URL, year.
    2. Consumed by the frontend theme initialization and layout components.

    Raises: ValidationError on missing fields or type mismatches.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/config/branding route, frontend theme.ts, Layout component.
    """
    hackathon_name: str
    hackathon_tagline: str
    hackathon_email: str
    hackathon_primary_color: str
    hackathon_logo_url: str
    hackathon_favicon_url: str
    hackathon_year: int


class ConfigKeyResponse(BaseModel):
    """Pydantic schema for a single key-value configuration entry.

    Behavior:
    1. Returns the config key and its stored string value.
    2. Used when the client requests one specific setting.

    Raises: ValidationError on missing key or value.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: GET /api/config/{key} route.
    """
    key: str
    value: str


class ConfigUpdateResponse(BaseModel):
    """Pydantic schema confirming a batch configuration update.

    Behavior:
    1. Returns the list of keys that were successfully updated.
    2. Lets the frontend know which settings changed.

    Raises: ValidationError if updated list is missing.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: PUT /api/config route, admin configuration panel.
    """
    updated: list[str]


class AssetUploadResponse(BaseModel):
    """Pydantic schema returned after a successful branding asset upload.

    Behavior:
    1. Returns the config key and public URL for the uploaded asset.
    2. Typically used for logo or favicon uploads.

    Raises: ValidationError on missing key or url.
    Side Effects: None.
    Dependencies: pydantic.BaseModel.
    Consumers: POST /api/config/assets route, admin asset manager.
    """
    key: str
    url: str

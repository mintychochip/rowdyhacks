"""Instance configuration service with DB + env fallback + Redis cache."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete, cache_get, cache_set
from app.config import settings
from app.models import SiteConfig

DEFAULTS = {
    "hackathon_name": ("OpenHack", "hackathon_name", "general"),
    "hackathon_tagline": ("The open-source hackathon framework", "hackathon_tagline", "general"),
    "hackathon_email": ("noreply@example.com", "hackathon_email", "email"),
    "hackathon_primary_color": ("#2563eb", "hackathon_primary_color", "theme"),
    "hackathon_background_color": ("#0f172a", None, "theme"),
    "hackathon_text_color": ("#f1f5f9", None, "theme"),
    "hackathon_accent_color": ("#06b6d4", None, "theme"),
    "hackathon_font_heading": ("Space Grotesk, sans-serif", None, "theme"),
    "hackathon_font_body": ("Inter, sans-serif", None, "theme"),
    "hackathon_logo_url": ("/openhack-logo.png", "hackathon_logo_url", "assets"),
    "hackathon_favicon_url": ("/openhack-logo.png", "hackathon_favicon_url", "assets"),
    "hackathon_year": ("2025", "hackathon_year", "general"),
    "custom_css": ("", None, "theme"),
    "registration_open": ("true", None, "features"),
    "judging_enabled": ("true", None, "features"),
}

_CACHE_KEY = "config:all"
_CACHE_TTL = 60

_CSS_MAP = {
    "hackathon_primary_color": "--oh-primary",
    "hackathon_background_color": "--oh-bg-base",
    "hackathon_text_color": "--oh-text-primary",
    "hackathon_accent_color": "--oh-accent",
    "hackathon_font_heading": "--oh-font-heading",
    "hackathon_font_body": "--oh-font-body",
}


class ConfigService:
    async def get(self, key: str, db: AsyncSession) -> str:
        if key not in DEFAULTS:
            raise ValueError(f"Unknown key '{key}'. Valid keys: {list(DEFAULTS.keys())}")
        default_value, env_attr, _ = DEFAULTS[key]
        if env_attr:
            env_val = getattr(settings, env_attr, None)
            if env_val is not None:
                return str(env_val)
        result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
        row = result.scalar_one_or_none()
        if row:
            return row.value
        return default_value

    async def get_all(self, db: AsyncSession, category: str | None = None) -> dict[str, str]:
        cached = await cache_get(_CACHE_KEY)
        if cached and isinstance(cached, dict):
            if category:
                return {k: v for k, v in cached.items() if DEFAULTS.get(k, (None, None, ""))[2] == category}
            return cached
        result = await db.execute(select(SiteConfig))
        rows = result.scalars().all()
        db_values = {r.key: r.value for r in rows}
        config = {}
        for key, (default, env_attr, cat) in DEFAULTS.items():
            if category and cat != category:
                continue
            if env_attr:
                env_val = getattr(settings, env_attr, None)
                if env_val is not None:
                    config[key] = str(env_val)
                    continue
            config[key] = db_values.get(key, default)
        await cache_set(_CACHE_KEY, config, _CACHE_TTL)
        return config

    async def set(self, key: str, value: str, db: AsyncSession) -> None:
        if key not in DEFAULTS:
            raise ValueError(f"Unknown key '{key}'. Valid keys: {list(DEFAULTS.keys())}")
        result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(SiteConfig(key=key, value=value, category=DEFAULTS[key][2]))
        await db.commit()
        await cache_delete(_CACHE_KEY)

    async def set_many(self, updates: dict[str, str], db: AsyncSession) -> None:
        invalid = [k for k in updates if k not in DEFAULTS]
        if invalid:
            raise ValueError(f"Unknown keys: {invalid}. Valid keys: {list(DEFAULTS.keys())}")
        for key, value in updates.items():
            result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
            row = result.scalar_one_or_none()
            if row:
                row.value = value
            else:
                db.add(SiteConfig(key=key, value=value, category=DEFAULTS[key][2]))
        await db.commit()
        await cache_delete(_CACHE_KEY)

    async def get_theme_css(self, db: AsyncSession) -> str:
        all_config = await self.get_all(db)
        lines = [":root {"]
        for key, css_var in _CSS_MAP.items():
            val = all_config.get(key, DEFAULTS.get(key, ("", None, ""))[0])
            lines.append(f"  {css_var}: {val};")
        lines.append("}")
        return "\n".join(lines)

    async def get_custom_css(self, db: AsyncSession) -> str | None:
        val = await self.get("custom_css", db)
        return val if val else None

    async def _seed_defaults(self, db: AsyncSession) -> None:
        for key, (default, env_attr, category) in DEFAULTS.items():
            result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
            row = result.scalar_one_or_none()
            if row is None:
                value = default
                if env_attr:
                    env_val = getattr(settings, env_attr, None)
                    if env_val is not None:
                        value = str(env_val)
                db.add(SiteConfig(key=key, value=value, category=category, description=f"Default {category} config"))
        await db.commit()

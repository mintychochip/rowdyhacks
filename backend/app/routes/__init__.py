try:
    from app.routes.content import router as content_router
except ImportError:
    content_router = None  # type: ignore

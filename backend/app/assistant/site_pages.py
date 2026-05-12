"""Site page indexing for the assistant vector store."""

from sqlalchemy import select

from app.assistant.indexer import DocumentIndexer
from app.models import ContentPage


async def index_content_page(page: ContentPage, db) -> dict:
    """Index a single content page into the assistant knowledge base.

    Args:
        page: The ContentPage ORM instance to index.
        db: An async SQLAlchemy session.

    Returns:
        dict with document_id, chunk_count, and chunk_ids.
    """
    indexer = DocumentIndexer(db)
    return await indexer.index_content_page(page)


async def delete_content_page(page_id: str, db) -> bool:
    """Remove a content page from the assistant knowledge base.

    Args:
        page_id: The UUID string of the ContentPage to unindex.
        db: An async SQLAlchemy session.

    Returns:
        True if an indexed document was found and deleted, False otherwise.
    """
    indexer = DocumentIndexer(db)
    return await indexer.delete_content_page(page_id)


async def index_site_pages() -> None:
    """Index all published content pages into the assistant vector store.

    Called on application startup to ensure all published pages are
    searchable by the AI assistant.
    """
    from app.database import async_session

    async with async_session() as db:
        result = await db.execute(select(ContentPage).where(ContentPage.is_published.is_(True)))
        pages = result.scalars().all()

        indexer = DocumentIndexer(db)
        for page in pages:
            await indexer.index_content_page(page)

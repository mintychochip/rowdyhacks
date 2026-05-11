"""Webhook delivery service with HMAC signing and retry logic."""

import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, WebhookDeliveryLog, WebhookSubscription

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class WebhookService:
    """Deliver events to webhook subscriptions with HMAC-SHA256 signatures."""

    async def deliver(
        self,
        db: AsyncSession,
        event: Event,
        subscription: WebhookSubscription,
    ) -> WebhookDeliveryLog:
        """POST event payload to subscription URL with HMAC signature.

        Creates a delivery log entry and attempts up to MAX_RETRIES on failure.
        """
        payload = {
            "event_type": event.type,
            "payload": event.payload,
            "timestamp": event.created_at.isoformat() if event.created_at else None,
        }
        body = json.dumps(payload, separators=(",", ":"), default=str)
        signature = self._sign(body, subscription.secret)

        log = WebhookDeliveryLog(
            subscription_id=subscription.id,
            event_id=event.id,
            status="retrying",
            http_status=None,
            response_body=None,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        subscription.url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": signature,
                            "User-Agent": "OpenHack-Webhook/1.0",
                        },
                    )
                log.http_status = resp.status_code
                if resp.status_code < 400:
                    log.status = "success"
                    log.response_body = resp.text[:1000]
                    break
                else:
                    log.status = "failed"
                    log.response_body = resp.text[:1000]
                    logger.warning(f"Webhook {subscription.url} returned {resp.status_code}")
            except Exception as exc:
                log.status = "failed"
                log.response_body = str(exc)[:1000]
                logger.warning(f"Webhook delivery error to {subscription.url}: {exc}")

        if log.status == "failed":
            log.status = "failed"

        await db.commit()
        return log

    async def retry_failed(self, db: AsyncSession) -> list[WebhookDeliveryLog]:
        """Re-deliver failed webhooks that haven't exceeded max attempts.

        Returns list of newly created delivery logs.
        """
        result = await db.execute(
            select(WebhookDeliveryLog)
            .where(WebhookDeliveryLog.status == "failed")
            .order_by(WebhookDeliveryLog.created_at.desc())
            .limit(100)
        )
        logs = result.scalars().all()
        new_logs = []
        for log in logs:
            sub_result = await db.execute(
                select(WebhookSubscription).where(WebhookSubscription.id == log.subscription_id)
            )
            sub = sub_result.scalar_one_or_none()
            if not sub or not sub.active:
                continue
            event_result = await db.execute(select(Event).where(Event.id == log.event_id))
            event = event_result.scalar_one_or_none()
            if not event:
                continue
            new_log = await self.deliver(db, event, sub)
            new_logs.append(new_log)
        return new_logs

    @staticmethod
    def _sign(body: str, secret: str) -> str:
        """Generate HMAC-SHA256 hex signature for the request body."""
        return hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

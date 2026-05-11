"""Clerk auth utilities — stub for transition to self-hosted auth."""

from fastapi import HTTPException, Request


async def decode_clerk_token(token: str):
    return {}


def extract_clerk_user_id(request: Request):
    return None


def extract_clerk_user_email(request: Request):
    return None


async def fetch_clerk_user_details(user_id: str):
    return {}


def is_clerk_token(token: str) -> bool:
    return False


async def require_clerk_user_with_db(request: Request):
    raise HTTPException(status_code=401, detail="Clerk auth disabled")


async def require_clerk_user(request: Request):
    raise HTTPException(status_code=401, detail="Clerk auth disabled")


async def require_organizer(request: Request):
    raise HTTPException(status_code=401, detail="Clerk auth disabled")

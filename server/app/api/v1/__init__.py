"""v1 router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    auth,
    centers,
    chat,
    documents,
    health,
    recommendations,
    schemes,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(chat.router)
api_router.include_router(schemes.router)
api_router.include_router(recommendations.router)
api_router.include_router(documents.router)
api_router.include_router(centers.router)
api_router.include_router(admin.router)

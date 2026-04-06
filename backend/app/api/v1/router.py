from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, organizations, tickets, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tickets.router)
api_router.include_router(admin.router)
api_router.include_router(organizations.router)

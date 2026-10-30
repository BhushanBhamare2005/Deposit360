from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    cases,
    dashboard,
    documents,
    extraction,
    institutions,
    instruments,
    notifications,
    policy_rules,
    releases,
    renewals,
    users,
    verification,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(institutions.router)
api_router.include_router(instruments.router)
api_router.include_router(documents.router)
api_router.include_router(extraction.router)
api_router.include_router(cases.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(renewals.router)
api_router.include_router(releases.router)
api_router.include_router(notifications.router)
api_router.include_router(policy_rules.router)
api_router.include_router(verification.router)

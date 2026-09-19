"""The caller's own identity.

``/me`` is the second of the three route scopes in architecture §5: authenticated, but
with no organization context. It is also the smallest possible demonstration that
``get_current_user`` works.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.auth.dependencies import CurrentUser
from api.schemas.auth import UserResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
async def read_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)

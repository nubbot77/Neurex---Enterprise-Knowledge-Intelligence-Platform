"""Auth routes — Phase 4, Task 6.

Thin on purpose: validate, call the service, shape the response. The workflow lives in
``AuthService`` so it can be tested without HTTP.

These are the only routes in the system that accept an unauthenticated caller. Every
route added from Phase 5 onward sits under ``/orgs/{organization_id}/`` and resolves an
organization context first.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, status

from api.auth.dependencies import AccessClaims, AuthServiceDep, CurrentUser
from api.auth.jwt import TokenPair
from api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPairResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(pair: TokenPair) -> TokenPairResponse:
    """Dataclass to response model.

    ``asdict`` rather than ``vars``: ``TokenPair`` uses ``slots=True``, so it has no
    ``__dict__`` at all.
    """
    return TokenPairResponse(**asdict(pair))


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> RegisterResponse:
    """Create an account, its personal organization and the admin membership."""
    user, organization, tokens = await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        organization_id=organization.id,
        tokens=_tokens(tokens),
    )


@router.post("/login")
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenPairResponse:
    """Exchange email and password for a token pair."""
    _, tokens = await service.login(email=payload.email, password=payload.password)
    return _tokens(tokens)


@router.post("/refresh")
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenPairResponse:
    """Rotate a refresh token into a new pair.

    Unauthenticated by design: the expired access token cannot be presented here, and
    the refresh token is the credential being checked.
    """
    tokens = await service.refresh(payload.refresh_token)
    return _tokens(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    claims: AccessClaims,
    service: AuthServiceDep,
) -> None:
    """Revoke this session's access and refresh tokens."""
    await service.logout(access_claims=claims, refresh_token=payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_everywhere(user: CurrentUser, service: AuthServiceDep) -> None:
    """Revoke every token for the caller, on every device."""
    await service.logout_everywhere(user.id)

"""Declarative authorization — Phase 5, Task 5.

Architecture §7.9. A route states the permission it needs in its own signature:

    @router.delete(
        "/members/{membership_id}",
        dependencies=[Depends(require(Permission.MEMBER_REMOVE))],
    )

The property that matters is not what happens when a developer declares the right
permission. It is what happens when they declare **none**: the endpoint must lock and
someone must file a bug, rather than opening silently to every member of every
organization.

That guarantee needs a mechanism, because "we always remember" is not one. Two pieces
provide it:

``require(...)``
    marks the route's dependency tree with the permissions it demands, and checks them
    against the caller's ``OrgContext``.

``enforce_declared_permission``
    sits on the organization router itself, so it runs for every route underneath. It
    looks up whether the matched endpoint carries a marker and denies outright when it
    does not.

The lookup table is built once at startup by ``scan_permission_declarations`` and
recorded in the log, so an undeclared route is visible at boot as well as at the moment
it refuses someone. Invariant 6 is what this file exists to hold up; the matching test
in ``tests/test_rbac.py`` is what stops it regressing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.routing import APIRoute

from api.auth.context import OrgContext
from api.auth.dependencies import OrgContextDep
from api.auth.exceptions import PermissionDenied
from api.auth.permissions import Permission

logger = structlog.get_logger(__name__)

# The attribute a dependency carries to say "this route declared what it needs".
_MARKER = "__rbac_permissions__"


def require(*permissions: Permission) -> Callable[..., Awaitable[OrgContext]]:
    """Route dependency: the caller must hold every listed permission.

    Several permissions mean *all* of them, not any. "Any of these" is a different
    rule, and writing it as a list that silently means "or" is how a route ends up
    reachable by half the people its author had in mind.

    Returns the ``OrgContext`` as well, so a handler that needs it can annotate the
    dependency directly instead of asking for it twice.
    """
    if not permissions:
        # A zero-argument require() would look like a declaration while demanding
        # nothing — the exact silent hole this module exists to prevent. Routes that
        # genuinely need only membership use ``Depends(get_org_context)`` and say so.
        raise ValueError("require() needs at least one Permission")

    required = frozenset(permissions)

    async def dependency(ctx: OrgContextDep) -> OrgContext:
        missing = required - ctx.permissions
        if missing:
            logger.info(
                "rbac.denied",
                missing=sorted(p.value for p in missing),
                **ctx.log_fields(),
            )
            raise PermissionDenied(reason="missing_permission")
        return ctx

    setattr(dependency, _MARKER, required)
    return dependency


def route_permissions(route: APIRoute) -> frozenset[Permission] | None:
    """Every permission this route declares, or ``None`` when it declares nothing.

    Walks the whole dependency tree rather than the route's own list, so a permission
    declared inside a shared sub-dependency still counts as declared.
    """
    found: set[Permission] = set()
    seen: set[int] = set()
    stack: list[Any] = [route.dependant]

    while stack:
        dependant = stack.pop()
        if id(dependant) in seen:
            continue
        seen.add(id(dependant))

        marker = getattr(dependant.call, _MARKER, None)
        if marker is not None:
            found |= set(marker)

        stack.extend(dependant.dependencies)

    return frozenset(found) if found else None


def iter_api_routes(router: Any, prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Every ``APIRoute`` reachable from an app or router, with its full path.

    FastAPI 0.141 stopped flattening ``include_router`` into ``app.routes``: an
    included router is kept as one nested object carrying the original router and the
    prefix it was mounted under. So this walks the tree rather than reading a list —
    a scan of ``app.routes`` alone sees three built-in routes and nothing of ours,
    which is the kind of silent miss that would make the default-deny audit below
    quietly pass while checking nothing.
    """
    for route in getattr(router, "routes", ()):
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
            continue

        original = getattr(route, "original_router", None)
        if original is not None:
            context = getattr(route, "include_context", None)
            yield from iter_api_routes(original, prefix + (getattr(context, "prefix", "") or ""))
        elif hasattr(route, "routes"):
            yield from iter_api_routes(route, prefix + (getattr(route, "path", "") or ""))


def scan_permission_declarations(app: FastAPI, *, scoped_prefix: str = "/orgs/") -> set[Any]:
    """Build the set of endpoints that declared a permission, and log the gaps.

    Called once at app creation. The returned set is what
    ``enforce_declared_permission`` consults per request — an identity test against a
    set, which costs nothing on the request path.
    """
    declared: set[Any] = set()

    for path, route in iter_api_routes(app):
        permissions = route_permissions(route)
        if permissions is not None:
            declared.add(route.endpoint)
            continue

        if scoped_prefix in path:
            # Loud on purpose. This route will refuse every caller, and the reason
            # belongs in the log at boot rather than in a support ticket.
            logger.error(
                "rbac.route_without_permission",
                path=path,
                methods=sorted(route.methods or ()),
            )

    app.state.rbac_declared_endpoints = declared
    return declared


async def enforce_declared_permission(request: Request) -> None:
    """Default deny, applied to every organization-scoped route.

    Attached to the organization router, so it runs for anything mounted underneath —
    including routes added in later phases by someone who never reads this file.
    """
    declared: set[Any] = getattr(request.app.state, "rbac_declared_endpoints", set())
    endpoint = request.scope.get("endpoint")

    if endpoint not in declared:
        logger.error(
            "rbac.denied",
            reason="no_permission_declared",
            path=request.url.path,
            method=request.method,
        )
        raise PermissionDenied(reason="no_permission_declared")


# The router-level guard, written once so every organization router reads the same.
DefaultDeny = Depends(enforce_declared_permission)

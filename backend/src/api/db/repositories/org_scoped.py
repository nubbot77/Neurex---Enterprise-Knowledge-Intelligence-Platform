"""Tenant isolation, enforced structurally — Phase 5, Tasks 6 and 9.

Architecture §7.9. Authorization and isolation answer different questions and neither
substitutes for the other:

    authorization   may this role perform this action?      route / service
    isolation       is this row inside my organization?     here

One missing ``WHERE organization_id = ?`` is a full cross-tenant breach, so this class
exists to make writing that query something a developer cannot do by accident. Every
read narrows to the context's organization, every write stamps it, and every update or
delete refuses a row belonging to anyone else.

Crossing tenants is still possible — a platform operator has to be able to — but only
through a differently-named method that demands an explicit argument, records who did
it and why, and refuses to write anything (§7.10).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from api.auth.context import OrgContext
from api.auth.exceptions import CrossTenantWriteForbidden, PermissionDenied
from api.db.base import Base
from api.db.repositories.base import BaseRepository
from api.models.audit import AuditLog
from api.models.user import User

logger = structlog.get_logger(__name__)


class OrgScopedRepository[ModelT: Base](BaseRepository[ModelT]):
    """Base for every table carrying ``organization_id``.

    Subclasses set ``model`` and add queries; they never write the tenant filter
    themselves, and they never need to remember to.

    The inherited ``BaseRepository`` methods are all overridden rather than extended.
    ``session.get()`` in particular loads by primary key straight from the identity map
    and would return another tenant's row without ever issuing a filtered query — so
    the override is not a convenience, it is the point.
    """

    def __init__(self, session: AsyncSession, ctx: OrgContext | None = None) -> None:
        super().__init__(session)
        self._ctx = ctx

    # -- the filter --------------------------------------------------------

    @property
    def ctx(self) -> OrgContext:
        """The context every scoped query filters by.

        Missing context raises rather than falling back to an unfiltered query. This is
        a programming error, not a runtime condition: the alternative — returning
        everything when nobody said which tenant — is the exact failure this class
        exists to prevent.
        """
        if self._ctx is None:
            raise RuntimeError(
                f"{type(self).__name__} was constructed without an OrgContext; "
                "scoped queries need one. Use the *_across_tenants methods for an "
                "audited platform-operator read."
            )
        return self._ctx

    @property
    def organization_id(self) -> UUID:
        return self.ctx.organization_id

    def _scoped(self, filters: dict[str, Any]) -> list[ColumnElement[bool]]:
        """Caller filters plus the tenant filter, which is never optional.

        A caller-supplied ``organization_id`` is dropped, not honoured and not merged:
        accepting one would let a filter argument widen or redirect the scope, which is
        precisely the hole the class closes.
        """
        filters.pop("organization_id", None)
        clauses = self._clauses(filters)
        clauses.append(self.model.organization_id == self.organization_id)  # type: ignore[attr-defined]
        return clauses

    # -- reads -------------------------------------------------------------

    async def get(self, id: Any) -> ModelT | None:
        """Fetch by primary key **within this organization**.

        Another tenant's id returns ``None``, exactly as an unknown id does. The caller
        turns that into a 404, so guessing ids tells an attacker nothing — a distinct
        "exists but not yours" answer would confirm the row.
        """
        result = await self.session.execute(
            select(self.model)
            .where(
                self.model.id == id,  # type: ignore[attr-defined]
                self.model.organization_id == self.organization_id,  # type: ignore[attr-defined]
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by(self, **filters: Any) -> ModelT | None:
        result = await self.session.execute(
            select(self.model).where(*self._scoped(filters)).limit(1)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: ColumnElement[Any] | None = None,
        **filters: Any,
    ) -> Sequence[ModelT]:
        stmt = select(self.model).where(*self._scoped(filters)).limit(limit).offset(offset)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(*self._scoped(filters))
        )
        return result.scalar_one()

    async def exists(self, **filters: Any) -> bool:
        result = await self.session.execute(
            select(self.model.id).where(*self._scoped(filters)).limit(1)  # type: ignore[attr-defined]
        )
        return result.first() is not None

    # -- writes ------------------------------------------------------------

    async def create(self, **values: Any) -> ModelT:
        """Insert into this organization.

        ``organization_id`` is stamped from the context, and a caller-supplied value
        for a different tenant is refused rather than quietly overwritten — a service
        that thinks it is writing elsewhere has a bug worth surfacing.
        """
        supplied = values.pop("organization_id", None)
        if supplied is not None and supplied != self.organization_id:
            raise PermissionDenied(reason="cross_tenant_create")
        values["organization_id"] = self.organization_id
        return await super().create(**values)

    async def update(self, instance: ModelT, **values: Any) -> ModelT:
        """Update a row this organization owns.

        Reparenting is refused outright: moving a row between tenants is not an
        operation this system has, and allowing it here would give every service one.
        """
        self._assert_owned(instance, operation="update")
        supplied = values.pop("organization_id", None)
        if supplied is not None and supplied != self.organization_id:
            raise PermissionDenied(reason="cross_tenant_reparent")
        return await super().update(instance, **values)

    async def delete(self, instance: ModelT) -> None:
        self._assert_owned(instance, operation="delete")
        await super().delete(instance)

    def _assert_owned(self, instance: ModelT, *, operation: str) -> None:
        """Last line of defence for a row that arrived from somewhere else.

        A service can hold an instance loaded by another repository, or by a bypass
        read. Re-checking here costs nothing and closes the gap between "fetched
        safely" and "written safely".
        """
        owner = getattr(instance, "organization_id", None)
        if owner != self.organization_id:
            logger.warning(
                "isolation.cross_tenant_write_blocked",
                operation=operation,
                model=self.model.__name__,
                row_organization_id=str(owner),
                **self.ctx.log_fields(),
            )
            raise PermissionDenied(reason=f"cross_tenant_{operation}")

    # -- the audited bypass — architecture §7.10 ---------------------------

    async def get_across_tenants(
        self,
        id: Any,
        *,
        across_tenants: bool,
        actor: User,
        reason: str,
    ) -> ModelT | None:
        """Read one row from any organization, as a platform operator.

        Three rules, all from §7.10, all visible from the call site:

        **Explicit.** ``across_tenants=True`` is passed consciously. It is not an
        ``if actor.is_super_admin`` branch hidden inside the ordinary ``get()`` —
        someone reading the call site has to be able to see that this query can leave
        the tenant.

        **Audited.** Every call writes an ``audit_log`` row: who, which organization,
        which resource, when, and ``reason``. The row is written in the caller's
        transaction, so a rolled-back request leaves no audit row and also returned no
        data; what is never recorded is also never read.

        **Read-only.** There is no ``update_across_tenants``. Support work is reading;
        a cross-tenant write turns one mistake into damage at several customers.
        """
        self._assert_bypass_allowed(across_tenants=across_tenants, actor=actor, reason=reason)

        result = await self.session.execute(
            select(self.model).where(self.model.id == id).limit(1)  # type: ignore[attr-defined]
        )
        row = result.scalar_one_or_none()

        await self._record_bypass(
            actor=actor,
            reason=reason,
            organization_id=getattr(row, "organization_id", None),
            resource_id=str(id),
        )
        return row

    async def list_across_tenants(
        self,
        *,
        across_tenants: bool,
        actor: User,
        reason: str,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> Sequence[ModelT]:
        """List rows across organizations, as a platform operator.

        ``organization_id`` may be passed as an ordinary filter here — narrowing a
        support read to one tenant is the common case, and unlike the scoped methods
        there is no scope for it to escape.
        """
        self._assert_bypass_allowed(across_tenants=across_tenants, actor=actor, reason=reason)

        stmt = select(self.model).where(*self._clauses(filters)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        await self._record_bypass(
            actor=actor,
            reason=reason,
            organization_id=filters.get("organization_id"),
            resource_id=None,
            matched=len(rows),
        )
        return rows

    def _assert_bypass_allowed(self, *, across_tenants: bool, actor: User, reason: str) -> None:
        if not across_tenants:
            # The argument exists to be read at the call site. Defaulting it, or
            # accepting False and doing the scoped thing instead, would make the call
            # site's meaning depend on a value the reader has to go and look up.
            raise ValueError("across_tenants must be True to use a cross-tenant read")
        if not actor.is_super_admin:
            logger.warning(
                "isolation.bypass_denied",
                actor_user_id=str(actor.id),
                model=self.model.__name__,
            )
            raise PermissionDenied(reason="not_super_admin")
        if not reason.strip():
            # An empty reason makes the audit row useless for the question it exists to
            # answer, so it is rejected rather than stored.
            raise ValueError("a cross-tenant read must state a reason")

    async def _record_bypass(
        self,
        *,
        actor: User,
        reason: str,
        organization_id: UUID | None,
        resource_id: str | None,
        matched: int | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor.id,
                organization_id=organization_id,
                action="cross_tenant_read",
                resource_type=self.model.__tablename__,
                resource_id=resource_id,
                reason=reason.strip(),
                via_super_admin=True,
            )
        )
        await self.session.flush()
        logger.warning(
            "isolation.cross_tenant_read",
            actor_user_id=str(actor.id),
            model=self.model.__name__,
            organization_id=str(organization_id) if organization_id else None,
            resource_id=resource_id,
            matched=matched,
        )

    # Writing across tenants is not an oversight; it is refused by name so the absence
    # is discoverable from an editor's autocomplete rather than from a design document.
    async def update_across_tenants(self, *args: Any, **kwargs: Any) -> None:
        raise CrossTenantWriteForbidden(reason="cross_tenant_write_attempted")

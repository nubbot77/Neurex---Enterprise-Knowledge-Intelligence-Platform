from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from api.db.base import Base


class BaseRepository[ModelT: Base]:
    """Generic data access for one table.

    Subclasses set ``model`` and add only the queries specific to that table.

    Two rules hold for every repository in this project:

    **It never commits.** Writes are flushed, not committed — flushing emits the SQL
    so primary keys are populated and constraint violations surface immediately, while
    leaving the transaction open. The commit belongs at the request boundary, so that a
    multi-row operation (registration writes a User, an Organization and a Membership)
    either lands whole or not at all.

    **It returns models, nothing else.** No Pydantic schemas, no HTTP concepts. The
    layers below the route do not know HTTP exists.

    This class deliberately applies no tenant filter. ``users`` and ``organizations``
    cannot be organization-scoped — a user is a global identity, and an organization is
    itself the tenant. Phase 5 adds ``OrgScopedRepository`` on top of this one for the
    tables that must always be filtered by ``organization_id``.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- reads -------------------------------------------------------------

    async def get(self, id: Any) -> ModelT | None:
        """Fetch by primary key. Returns ``None`` when absent.

        Absence is not an error here. Only the caller knows whether a missing row is a
        404, an empty result, or an ordinary branch.
        """
        return await self.session.get(self.model, id)

    async def get_by(self, **filters: Any) -> ModelT | None:
        """Fetch the first row matching an equality filter, or ``None``."""
        result = await self.session.execute(
            select(self.model).where(*self._clauses(filters)).limit(1)
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
        """Fetch a page of rows.

        Offset pagination is correct and cheap at this scale. It degrades at large
        offsets, where keyset pagination is the replacement — a change confined to this
        method because no caller builds its own query.
        """
        stmt = select(self.model).where(*self._clauses(filters)).limit(limit).offset(offset)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(*self._clauses(filters))
        )
        return result.scalar_one()

    async def exists(self, **filters: Any) -> bool:
        result = await self.session.execute(
            select(self.model.__table__.c.values()[0]).where(*self._clauses(filters)).limit(1)
        )
        return result.first() is not None

    # -- writes ------------------------------------------------------------

    async def create(self, **values: Any) -> ModelT:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    # -- internals ---------------------------------------------------------

    def _clauses(self, filters: dict[str, Any]) -> list[ColumnElement[bool]]:
        """Turn ``field=value`` keyword arguments into equality clauses.

        An unknown field raises rather than being ignored: a silently dropped filter
        would widen a query, and a widened query is how rows leak.
        """
        clauses: list[ColumnElement[bool]] = []
        for field, value in filters.items():
            column = getattr(self.model, field, None)
            if column is None:
                raise AttributeError(f"{self.model.__name__} has no attribute {field!r}")
            clauses.append(column == value)
        return clauses

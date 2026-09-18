from __future__ import annotations

from api.db.repositories.base import BaseRepository
from api.models.user import User


class UserRepository(BaseRepository[User]):
    """Queries against ``users``.

    Not organization-scoped: a user is a global identity that may hold memberships in
    several organizations. Authority is read from ``Membership``, never from here.
    """

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Look up by email — the login path.

        ``email`` is uniquely indexed, so this is a single index hit.
        """
        return await self.get_by(email=email)

    async def email_exists(self, email: str) -> bool:
        """Registration pre-check.

        Advisory only. Two concurrent registrations can both pass this and only the
        unique index decides, so the caller must still handle the integrity error.
        """
        return await self.exists(email=email)

"""User aggregate persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, or_, select

from app.models.user import User, UserProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def by_firebase_uid(self, firebase_uid: str) -> User | None:
        stmt = select(User).where(User.firebase_uid == firebase_uid)
        return await self._scalar_one(stmt)

    async def by_id(self, user_id: Any) -> User | None:
        return await self.get(user_id)

    async def get_or_create_by_firebase(
        self, firebase_uid: str, *, auth_method: str = "email"
    ) -> User:
        existing = await self.by_firebase_uid(firebase_uid)
        if existing:
            return existing
        user = await self.add(User(firebase_uid=firebase_uid, auth_method=auth_method))
        await self.session.commit()
        return user

    # -- admin views --------------------------------------------------------

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(User)
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_recent(self, days: int = 30) -> int:
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(func.count()).select_from(User).where(User.created_at >= cutoff)
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_admin(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        q: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        if q:
            name_needle = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(name_needle),
                    User.display_name.ilike(name_needle),
                    User.firebase_uid == q,
                )
            )
        if role:
            stmt = stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total


class ProfileRepository(BaseRepository[UserProfile]):
    model = UserProfile

    async def by_user(self, user_id: Any) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        return await self._scalar_one(stmt)

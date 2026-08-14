"""Scheme catalog + user scheme-interaction persistence.

Search/filter semantics live in :class:`SchemeService`; the repository is a thin
persistence layer (no request business logic). All queries use SQLAlchemy
expression constructs — never raw strings — guaranteeing injection safety.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import CursorResult, delete, desc, func, or_, select, update

from app.models.scheme import (
    SEARCH_HISTORY_LIMIT,
    Scheme,
    UserSavedScheme,
    UserSavedSearch,
    UserSchemeView,
    UserSearchHistory,
)
from app.repositories.base import BaseRepository

#: Searchable text columns (lower-cased).
_SEARCHABLE = ("code", "short_name", "name_en", "name_native", "summary_en", "description_en")


class SchemeRepository(BaseRepository[Scheme]):
    model = Scheme

    # -- CRUD -----------------------------------------------------------------

    async def by_code(self, code: str) -> Scheme | None:
        stmt = select(Scheme).where(func.lower(Scheme.code) == code.strip().lower())
        return await self._scalar_one(stmt)

    async def delete_scheme_rows(self, scheme: Scheme) -> None:
        """Remove scheme-dependent rows, then the scheme (portable across DBs)."""
        await self.session.execute(
            delete(UserSavedScheme).where(UserSavedScheme.scheme_id == scheme.id)
        )
        await self.session.execute(
            delete(UserSchemeView).where(UserSchemeView.scheme_id == scheme.id)
        )
        await self.delete(scheme)

    async def all_public(self) -> list[Scheme]:
        """All published schemes (browse/search universe). Ordered for stable pagination."""
        stmt = (
            select(Scheme)
            .where(Scheme.scheme_status == "published")
            .order_by(desc(Scheme.popularity), Scheme.code)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def page_by_popularity(self, page: int, page_size: int) -> tuple[list[Scheme], int]:
        """SQL-paginated browse path ordered by popularity (fast for no-filter reads)."""
        total = await self.published_count()
        stmt = (
            select(Scheme)
            .where(Scheme.scheme_status == "published")
            .order_by(desc(Scheme.popularity), desc(Scheme.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # -- admin views (Prompt 15) ---------------------------------------------

    async def published_count(self) -> int:
        stmt = select(func.count()).select_from(Scheme).where(Scheme.scheme_status == "published")
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_by_status(self) -> dict[str, int]:
        """Scheme row counts keyed by status (admin overview)."""
        stmt = select(Scheme.scheme_status, func.count()).group_by(Scheme.scheme_status)
        rows = (await self.session.execute(stmt)).all()
        return {status: count for status, count in rows}

    async def list_admin(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        q: str | None = None,
        status: str | None = None,
        category: str | None = None,
        verification_status: str | None = None,
        ministry: str | None = None,
        scope: str | None = None,
        sort: str = "updated",
    ) -> tuple[list[Scheme], int]:
        """Admin catalog listing over *all* statuses (public only sees live)."""
        stmt = select(Scheme)
        if q:
            needle = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Scheme.code.ilike(needle),
                    Scheme.name_en.ilike(needle),
                    Scheme.short_name.ilike(needle),
                )
            )
        if status:
            stmt = stmt.where(Scheme.scheme_status == status)
        if category:
            stmt = stmt.where(Scheme.category == category)
        if verification_status:
            stmt = stmt.where(Scheme.verification_status == verification_status)
        if ministry:
            stmt = stmt.where(Scheme.ministry.ilike(f"%{ministry}%"))
        if scope:
            stmt = stmt.where(Scheme.scope == scope)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())

        if sort == "popular":
            order: list[Any] = [desc(Scheme.popularity), desc(Scheme.created_at)]
        elif sort == "name":
            order = [Scheme.name_en.asc(), Scheme.code]
        else:
            order = [desc(Scheme.updated_at), desc(Scheme.created_at)]
        stmt = stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_by_category(self) -> dict[str, int]:
        """Live-scheme counts keyed by category (admin + public rails)."""
        stmt = (
            select(Scheme.category, func.count())
            .where(Scheme.scheme_status == "published")
            .group_by(Scheme.category)
        )
        rows = (await self.session.execute(stmt)).all()
        return {category: count for category, count in rows}

    # -- View / trending counters ---------------------------------------------

    async def bump_views(self, scheme: Scheme, amount: int = 1) -> None:
        """Increment the global view counter (powers popular ordering).

        Runs server-side with ``synchronize_session=False`` so the loaded
        instance stays clean: mutating it here would dirty the row, and the
        ``updated_at`` ``onupdate`` trigger would then expire that column on
        commit → an async lazy load (``MissingGreenlet``) on the next read.
        """
        await self.session.execute(
            update(Scheme)
            .where(Scheme.id == scheme.id)
            .values(view_count=Scheme.view_count + amount),
            execution_options={"synchronize_session": False},
        )

    async def set_popularity(self, scheme: Scheme, value: int) -> None:
        scheme.popularity = value

    # -- Bookmarks -------------------------------------------------------------

    async def is_bookmarked(self, user_id: Any, scheme_id: Any) -> bool:
        stmt = select(UserSavedScheme.scheme_id).where(
            UserSavedScheme.user_id == user_id, UserSavedScheme.scheme_id == scheme_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def add_bookmark(self, user_id: Any, scheme_id: Any, *, notify: bool = True) -> bool:
        """Persist a bookmark row; returns True when newly created."""
        if await self.is_bookmarked(user_id, scheme_id):
            return False
        self.session.add(
            UserSavedScheme(user_id=user_id, scheme_id=scheme_id, notify_on_update=notify)
        )
        return True

    async def remove_bookmark(self, user_id: Any, scheme_id: Any) -> bool:
        stmt = delete(UserSavedScheme).where(
            UserSavedScheme.user_id == user_id, UserSavedScheme.scheme_id == scheme_id
        )
        result = cast("CursorResult[Any]", await self.session.execute(stmt))
        if result.rowcount == 0:
            return False
        scheme = await self.get(scheme_id)
        if scheme is not None:
            scheme.bookmark_count = max(scheme.bookmark_count - 1, 0)
        return True

    async def list_bookmarks(
        self, user_id: Any, *, page: int = 1, page_size: int = 20, limit: int | None = None
    ) -> tuple[list[Scheme], int]:
        """Saved schemes (most recently saved first)."""
        count_stmt = (
            select(func.count())
            .select_from(UserSavedScheme)
            .join(Scheme, UserSavedScheme.scheme_id == Scheme.id)
            .where(UserSavedScheme.user_id == user_id, Scheme.scheme_status == "published")
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = (
            select(Scheme)
            .join(UserSavedScheme, UserSavedScheme.scheme_id == Scheme.id)
            .where(UserSavedScheme.user_id == user_id, Scheme.scheme_status == "published")
            .order_by(desc(UserSavedScheme.saved_at))
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        else:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_bookmarks_by_scheme(self, scheme_id: Any) -> int:
        stmt = (
            select(func.count())
            .select_from(UserSavedScheme)
            .where(UserSavedScheme.scheme_id == scheme_id)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    # -- Recently viewed -------------------------------------------------------

    async def record_view(self, user_id: Any, scheme_id: Any) -> None:
        stmt = select(UserSchemeView.id).where(
            UserSchemeView.user_id == user_id, UserSchemeView.scheme_id == scheme_id
        )
        view_id = (await self.session.execute(stmt)).scalar_one_or_none()
        if view_id is None:
            self.session.add(
                UserSchemeView(user_id=user_id, scheme_id=scheme_id, viewed_at=func.now())
            )
        else:
            await self.session.execute(
                update(UserSchemeView)
                .where(UserSchemeView.id == view_id)
                .values(viewed_at=func.now())
            )

    async def list_recent_views(self, user_id: Any, *, limit: int = 30) -> list[Scheme]:
        stmt = (
            select(Scheme)
            .join(UserSchemeView, UserSchemeView.scheme_id == Scheme.id)
            .where(UserSchemeView.user_id == user_id, Scheme.scheme_status == "published")
            .order_by(desc(UserSchemeView.viewed_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -- Saved searches --------------------------------------------------------

    async def save_search(
        self,
        user_id: Any,
        query: str,
        filters: dict[str, Any] | None,
        *,
        notify: bool = False,
    ) -> UserSavedSearch:
        existing = await self.saved_search_by_query(user_id, query)
        if existing is not None:
            existing.notify_on_update = notify
            if filters:
                existing.filters = filters
            await self.session.flush()
            return existing
        saved = UserSavedSearch(
            user_id=user_id, query=query, filters=filters or {}, notify_on_update=notify
        )
        self.session.add(saved)
        await self.session.flush()
        return saved

    async def saved_search_by_query(self, user_id: Any, query: str) -> UserSavedSearch | None:
        stmt = select(UserSavedSearch).where(
            UserSavedSearch.user_id == user_id,
            func.lower(UserSavedSearch.query) == query.strip().lower(),
        )
        result = await self._scalar_one(stmt)
        return cast("UserSavedSearch | None", result)

    async def list_saved_searches(
        self, user_id: Any, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[UserSavedSearch], int]:
        stmt = (
            select(UserSavedSearch)
            .where(UserSavedSearch.user_id == user_id)
            .order_by(desc(UserSavedSearch.created_at))
        )
        sub_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(sub_stmt)).scalar_one())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def delete_saved_search(self, user_id: Any, search_id: Any) -> bool:
        stmt = delete(UserSavedSearch).where(
            UserSavedSearch.user_id == user_id, UserSavedSearch.id == search_id
        )
        result = cast("CursorResult[Any]", await self.session.execute(stmt))
        return result.rowcount > 0

    # -- Search history --------------------------------------------------------

    async def add_search_history(
        self, user_id: Any, query: str, filters: dict[str, Any] | None = None
    ) -> None:
        self.session.add(
            UserSearchHistory(user_id=user_id, query=query.strip(), filters=filters or {})
        )
        # prune to the most recent N rows for this user
        stmt = (
            select(UserSearchHistory.id)
            .where(UserSearchHistory.user_id == user_id)
            .order_by(desc(UserSearchHistory.created_at))
            .offset(SEARCH_HISTORY_LIMIT)
        )
        stale_ids = [row[0] for row in (await self.session.execute(stmt)).all()]
        if stale_ids:
            await self.session.execute(
                delete(UserSearchHistory).where(UserSearchHistory.id.in_(stale_ids))
            )

    async def list_search_history(
        self, user_id: Any, *, limit: int = SEARCH_HISTORY_LIMIT
    ) -> list[UserSearchHistory]:
        stmt = (
            select(UserSearchHistory)
            .where(UserSearchHistory.user_id == user_id)
            .order_by(desc(UserSearchHistory.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

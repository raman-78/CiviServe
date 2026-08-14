"""Scheme catalog service: search, filters, trending, bookmarks, saved searches.

Search is a hybrid: structured columns (category/state/ministry/…) filter first,
then an in-Python relevance score (keyword hits + difflib fuzzy fallback) ranks
the results so misspellings still surface the right scheme. This keeps the
engine portable (SQLite tests → Postgres prod) and is designed to be replaced by
pg_trgm + tsvector + embeddings (docs/database/06) without changing the API.

The eligibility *recommendation* engine is explicitly out of scope (a later
prompt). Demographic filters here only express "not obviously excluded".
"""

from __future__ import annotations

import re
import uuid
from difflib import SequenceMatcher
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.core.errors import ConflictError, NotFoundError
from app.models.scheme import Scheme
from app.repositories.scheme_repo import SchemeRepository
from app.schemas.common import Paginated
from app.schemas.scheme import (
    BookmarkStatusOut,
    LocalizedText,
    SavedSearchCreate,
    SavedSearchOut,
    SchemeCreate,
    SchemeOut,
    SchemeSummaryOut,
    SchemeUpdate,
    SearchHistoryOut,
    SuggestionsOut,
    TrendingOut,
)

#: Fields a boolean "targeted" rule may use (from the eligibility filter catalog).
_BOOLEAN_FIELDS = {
    "is_farmer",
    "is_student",
    "is_disabled",
    "is_minority",
    "is_senior_citizen",
    "is_self_employed",
    "is_widow",
}
_GENDER_FIELDS = {"gender", "is_women"}


def _normalize(text: str) -> str:
    """Lowercase + strip non-alphanumerics so search/typo matching is stable."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


class SchemeService:
    """Orchestrates scheme reads/writes; no HTTP awareness."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = SchemeRepository(session)
        self.session = session
        self.cache = get_cache()

    # ------------------------------------------------------------------ dto --

    def to_summary(self, scheme: Scheme, match_score: int | None = None) -> SchemeSummaryOut:
        return SchemeSummaryOut(
            id=str(scheme.id),
            code=scheme.code,
            category=scheme.category,
            scope=scheme.scope,
            state_code=scheme.state_code,
            short_name=scheme.short_name,
            name=LocalizedText(en=scheme.name_en, native=scheme.name_native),
            summary=LocalizedText(en=scheme.summary_en, native=scheme.summary_native),
            tags=scheme.tags or [],
            match_score=match_score,
            popularity=scheme.popularity,
        )

    def to_out(self, scheme: Scheme) -> SchemeOut:
        links = scheme.application_links or {}
        return SchemeOut(
            id=str(scheme.id),
            code=scheme.code,
            short_name=scheme.short_name,
            name=LocalizedText(en=scheme.name_en, native=scheme.name_native),
            summary=LocalizedText(en=scheme.summary_en, native=scheme.summary_native),
            description=LocalizedText(en=scheme.description_en, native=scheme.description_native),
            category=scheme.category,
            sub_category=scheme.sub_category,
            ministry=scheme.ministry,
            department=scheme.department,
            scope=scheme.scope,
            state_code=scheme.state_code,
            applicable_states=scheme.applicable_states or [],
            target_beneficiaries=scheme.target_beneficiaries or [],
            benefits=scheme.benefits or [],
            eligibility_rules=scheme.eligibility_rules or [],
            required_documents=scheme.required_documents or [],
            application_steps=scheme.application_steps or [],
            renewal_process=scheme.renewal_process,
            application_links=links,
            official_website=scheme.official_website,
            official_application_link=scheme.official_application_link,
            helpline=links.get("helpline"),
            faqs=scheme.faqs or [],
            scheme_status=scheme.scheme_status,
            last_verified_at=scheme.last_verified_at,
            source_name=scheme.source_name,
            source_url=scheme.source_url,
            source_type=scheme.source_type,
            verification_status=scheme.verification_status,
            review_note=scheme.review_note,
            keywords=scheme.keywords or [],
            tags=scheme.tags or [],
            popularity=scheme.popularity,
            view_count=scheme.view_count,
            bookmark_count=scheme.bookmark_count,
            created_at=scheme.created_at,
            updated_at=scheme.updated_at,
        )

    def _paginate(self, schemes: list[Any], page: int, page_size: int) -> tuple[list[Any], int]:
        total = len(schemes)
        start = (page - 1) * page_size
        return schemes[start : start + page_size], total

    # ------------------------------------------------------------- retrieval --

    async def get_public(self, code: str) -> Scheme:
        scheme = await self.repo.by_code(code)
        if scheme is None or scheme.scheme_status != "published":
            raise NotFoundError("Scheme not found.")
        return scheme

    async def record_scheme_view(self, scheme: Scheme, user_id: Any | None = None) -> None:
        """Bump global view count + per-user "recently viewed" (best-effort)."""
        await self.repo.bump_views(scheme)
        if user_id is not None:
            await self.repo.record_view(user_id, scheme.id)
        await self.session.commit()

    async def browse(
        self,
        *,
        page: int,
        page_size: int,
        sort: str,
        category: str | None = None,
        sub_category: str | None = None,
        state: str | None = None,
        scope: str | None = None,
        ministry: str | None = None,
        department: str | None = None,
        demographic: dict[str, Any] | None = None,
    ) -> tuple[list[Scheme], int]:
        schemes = await self.repo.all_public()
        if state is not None:
            schemes = [s for s in schemes if self._state_applies(s, state)]
        if category is not None:
            schemes = [s for s in schemes if s.category == category]
        if sub_category is not None:
            schemes = [s for s in schemes if (s.sub_category or "").lower() == sub_category.lower()]
        if scope is not None:
            schemes = [s for s in schemes if s.scope == scope]
        if ministry is not None:
            needle = _normalize(ministry)
            schemes = [s for s in schemes if needle in _normalize(s.ministry)]
        if department is not None:
            needle = _normalize(department)
            schemes = [s for s in schemes if needle in _normalize(s.department or "")]
        if demographic:
            schemes = [s for s in schemes if self._passes_demographic(s, demographic)]

        schemes.sort(key=_sort_key(sort))
        items, total = self._paginate(schemes, page, page_size)
        return items, total

    # ---------------------------------------------------------------- search --

    async def search(
        self,
        *,
        q: str,
        page: int,
        page_size: int,
        sort: str,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[tuple[Scheme, int]], int]:
        """Keyword/partial/misspelled search with a 0-100 relevance score.

        Non-English queries (detected by script) are translated to English first
        so Indic-language searches reach the same catalog keywords; the
        untranslated text is still used for the demographic/filter passes.
        """
        query = _normalize(await self._localize_query(q))
        schemes = await self.repo.all_public()
        tokens = query.split() if query else []
        scored: list[tuple[Scheme, int]] = [
            (scheme, self._score(scheme, query, tokens)) for scheme in schemes
        ]
        if query:
            scored = [(s, score) for s, score in scored if score > 0]

        filters = filters or {}
        if filters:
            scored = [
                (s, score)
                for s, score in scored
                if self._passes_filters(s, filters) and self._passes_demographic(s, filters)
            ]

        scored.sort(key=_search_sort_key(sort))
        items, total = self._paginate(scored, page, page_size)
        return items, total

    async def _localize_query(self, q: str) -> str:
        """Translate a non-English query to the catalog's language (best-effort)."""
        from app.services.translation.service import TranslationService

        translation = TranslationService()
        detected = translation.detect(q, preferred="en")
        if detected.language == "en":
            return q
        return await translation.to_english(q, source=detected.language)

    def _score(self, scheme: Scheme, query: str, tokens: list[str]) -> int:
        if not query:
            return 0
        haystack = self._haystack(scheme)
        score = 0

        code = _normalize(scheme.code)
        name = _normalize(scheme.name_en)
        if code == query or name == query:
            return 100
        if name.startswith(query) or code.startswith(query):
            score += 45

        for token in tokens:
            if token in name:
                score += 22
            elif token in code:
                score += 18
            elif token in self._keywords(scheme):
                score += 16
            elif token in haystack:
                score += 8

        if all(token in name for token in tokens):
            score += 12

        # Fuzzy fallback for misspellings (only when nothing else matched strongly).
        # Compares the query against individual tokens so "kissaan" → "kisan".
        if score < 30 and len(query) >= 3:
            fuzzy_text = " ".join(
                [name, code, _normalize(scheme.short_name or ""), self._keywords(scheme)]
            )
            candidates = {c for c in fuzzy_text.split() if len(c) >= 3}
            best = max((_ratio(query, c) for c in candidates), default=0.0)
            if best >= 0.68:
                score = max(score, int(best * 55))
        return min(score, 100)

    def _haystack(self, scheme: Scheme) -> str:
        parts = [
            scheme.name_en,
            scheme.summary_en,
            scheme.description_en,
            scheme.ministry,
            scheme.department or "",
            scheme.category,
            scheme.sub_category or "",
            " ".join(scheme.benefits or []),
            " ".join(scheme.target_beneficiaries or []),
        ]
        return _normalize(" ".join(parts))

    def _keywords(self, scheme: Scheme) -> str:
        return _normalize(" ".join((scheme.keywords or []) + (scheme.tags or [])))

    async def suggestions(self, q: str, *, limit: int = 8) -> SuggestionsOut:
        query = _normalize(q)
        if not query:
            return SuggestionsOut(query=q, suggestions=[], corrected=None)

        cache_key = f"scheme:suggestions:{query}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cast("SuggestionsOut", cached)

        terms: set[str] = set()
        for scheme in await self.repo.all_public():
            terms.update(
                _normalize(t)
                for t in [
                    scheme.code,
                    scheme.short_name or "",
                    scheme.name_en,
                    *scheme.tags,
                    *scheme.keywords,
                ]
                if t
            )

        suggestions = sorted(t for t in terms if query in t)[:limit]
        corrected: str | None = None
        if not suggestions and len(query) >= 3:
            query_tokens = query.split()

            def best_match(term: str) -> float:
                term_tokens = [tk for tk in term.split() if len(tk) >= 3]
                pairs = ((_ratio(qt, tk) for tk in term_tokens) for qt in query_tokens)
                return max((r for group in pairs for r in group), default=0.0)

            closest = max(terms, key=best_match, default="")
            if closest and best_match(closest) >= 0.6:
                corrected = closest
        result = SuggestionsOut(query=q, suggestions=suggestions, corrected=corrected)
        self.cache.set(cache_key, result)
        return result

    # --------------------------------------------------------------- trending --

    async def trending(self, *, limit: int = 8) -> list[TrendingOut]:
        """Editor-assigned popularity — cached, the classic "hot schemes" rail."""
        return await self._ranked("trending", limit, key=lambda s: s.popularity)

    async def popular(self, *, limit: int = 8) -> list[TrendingOut]:
        """Live view-count leaderboard — cached, "most viewed"."""
        return await self._ranked("popular", limit, key=lambda s: s.view_count)

    async def _ranked(self, rail: str, limit: int, *, key: Any) -> list[TrendingOut]:
        cache_key = f"scheme:{rail}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cast("list[TrendingOut]", cached)
        schemes = sorted(await self.repo.all_public(), key=key, reverse=True)[:limit]
        ranked = [
            TrendingOut(rank=index + 1, scheme=self.to_summary(scheme))
            for index, scheme in enumerate(schemes)
        ]
        self.cache.set(cache_key, ranked)
        return ranked

    async def popular_categories(self, *, limit: int = 8) -> list[dict[str, Any]]:
        cache_key = "scheme:popular-categories"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cast("list[dict[str, Any]]", cached)
        counts: dict[str, int] = {}
        for scheme in await self.repo.all_public():
            counts[scheme.category] = counts.get(scheme.category, 0) + 1
        result = [
            {"category": category, "count": count}
            for category, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        ][:limit]
        self.cache.set(cache_key, result)
        return result

    # -------------------------------------------------------------- related --

    async def related(self, scheme: Scheme, *, limit: int = 6) -> list[Scheme]:
        schemes = [s for s in await self.repo.all_public() if s.id != scheme.id]
        scored = []
        for candidate in schemes:
            score = 0
            if candidate.category == scheme.category:
                score += 30
            if candidate.scope == scheme.scope:
                score += 10
            if (candidate.ministry or "").lower() == (scheme.ministry or "").lower():
                score += 20
            if candidate.scope == "state" and self._state_overlap(scheme, candidate):
                score += 15
            scored.append((score, candidate))
        scored.sort(key=lambda pair: (-pair[0], -pair[1].popularity))
        return [candidate for _, candidate in scored[:limit]]

    # ------------------------------------------------------------ bookmarks --

    async def add_bookmark(self, user_id: Any, scheme_id: Any) -> BookmarkStatusOut:
        scheme = await self.repo.get(uuid.UUID(str(scheme_id)))
        if scheme is None or scheme.scheme_status != "published":
            raise NotFoundError("Scheme not found.")
        added = await self.repo.add_bookmark(user_id, scheme.id)
        if added:
            scheme.bookmark_count = (scheme.bookmark_count or 0) + 1
        await self.session.commit()
        return BookmarkStatusOut(
            scheme_id=str(scheme.id), saved=True, bookmark_count=scheme.bookmark_count
        )

    async def remove_bookmark(self, user_id: Any, scheme_id: Any) -> BookmarkStatusOut:
        scheme = await self.repo.get(uuid.UUID(str(scheme_id)))
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        await self.repo.remove_bookmark(user_id, scheme.id)
        await self.session.commit()
        return BookmarkStatusOut(
            scheme_id=str(scheme.id),
            saved=False,
            bookmark_count=scheme.bookmark_count if scheme is not None else 0,
        )

    async def list_bookmarks(
        self, user_id: Any, *, page: int = 1, page_size: int = 20
    ) -> Paginated[SchemeSummaryOut]:
        schemes, total = await self.repo.list_bookmarks(user_id, page=page, page_size=page_size)
        return Paginated(
            items=[self.to_summary(s) for s in schemes], page=page, page_size=page_size, total=total
        )

    async def bookmarked_ids(self, user_id: Any) -> set[str]:
        schemes, _ = await self.repo.list_bookmarks(user_id, page=1, page_size=500)
        return {str(scheme.id) for scheme in schemes}

    async def recent_views(self, user_id: Any, *, limit: int = 20) -> list[SchemeSummaryOut]:
        schemes = await self.repo.list_recent_views(user_id, limit=limit)
        return [self.to_summary(s) for s in schemes]

    # -------------------------------------------------------- saved searches --

    async def save_search(self, user_id: Any, payload: SavedSearchCreate) -> SavedSearchOut:
        saved = await self.repo.save_search(
            user_id, payload.query, payload.filters, notify=payload.notify_on_update
        )
        await self.session.commit()
        return self._saved_search_out(saved)

    async def list_saved_searches(
        self, user_id: Any, *, page: int = 1, page_size: int = 20
    ) -> Paginated[SavedSearchOut]:
        rows, total = await self.repo.list_saved_searches(user_id, page=page, page_size=page_size)
        return Paginated(
            items=[self._saved_search_out(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def delete_saved_search(self, user_id: Any, search_id: Any) -> None:
        uuid_search_id = (
            uuid.UUID(str(search_id)) if not isinstance(search_id, uuid.UUID) else search_id
        )
        if not await self.repo.delete_saved_search(user_id, uuid_search_id):
            raise NotFoundError("Saved search not found.")

    def _saved_search_out(self, row: Any) -> SavedSearchOut:
        return SavedSearchOut(
            id=str(row.id),
            query=row.query,
            filters=row.filters or {},
            notify_on_update=row.notify_on_update,
            created_at=row.created_at,
        )

    async def search_history(self, user_id: Any, *, limit: int = 10) -> list[SearchHistoryOut]:
        rows = await self.repo.list_search_history(user_id, limit=limit)
        return [
            SearchHistoryOut(id=str(row.id), query=row.query, created_at=row.created_at)
            for row in rows
        ]

    async def record_search(
        self, user_id: Any, query: str, filters: dict[str, Any] | None = None
    ) -> None:
        """Best-effort recent-search persistence (never fails the request)."""
        if not query.strip():
            return
        await self.repo.add_search_history(user_id, query, filters)
        await self.session.commit()

    # ----------------------------------------------------------------- admin --

    async def create_scheme(self, payload: SchemeCreate) -> Scheme:
        if await self.repo.by_code(payload.code) is not None:
            raise ConflictError(f"Scheme code '{payload.code}' already exists.")
        scheme = Scheme(
            code=payload.code,
            short_name=payload.short_name,
            name_en=payload.name.en,
            name_native=payload.name.native,
            summary_en=payload.summary.en,
            summary_native=payload.summary.native,
            description_en=payload.description.en,
            description_native=payload.description.native,
            category=payload.category,
            sub_category=payload.sub_category,
            ministry=payload.ministry,
            department=payload.department,
            scope=payload.scope,
            state_code=payload.state_code,
            applicable_states=payload.applicable_states,
            target_beneficiaries=payload.target_beneficiaries,
            benefits=payload.benefits,
            eligibility_rules=payload.eligibility_rules,
            required_documents=payload.required_documents,
            application_steps=payload.application_steps,
            faqs=payload.faqs,
            renewal_process=payload.renewal_process,
            application_links=payload.application_links,
            official_website=payload.official_website,
            official_application_link=payload.official_application_link,
            keywords=payload.keywords,
            tags=payload.tags,
            scheme_status=payload.scheme_status,
            last_verified_at=payload.last_verified_at,
            source_name=payload.source_name,
            source_url=payload.source_url,
            source_type=payload.source_type,
            verification_status=payload.verification_status,
            review_note=payload.review_note,
        )
        scheme = await self.repo.add(scheme)
        await self.session.commit()
        await self.session.refresh(scheme)
        return scheme

    async def update_scheme(self, code: str, payload: SchemeUpdate) -> Scheme:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        data = payload.model_dump(exclude_unset=True)

        def _text(value: Any) -> tuple[str, str]:
            if isinstance(value, dict):
                return (value.get("en") or "", value.get("native") or "")
            return (value.en or "", value.native or "")

        if "name" in data:
            scheme.name_en, scheme.name_native = _text(data.pop("name"))
        if "summary" in data:
            scheme.summary_en, scheme.summary_native = _text(data.pop("summary"))
        if "description" in data:
            scheme.description_en, scheme.description_native = _text(data.pop("description"))
        for key, value in data.items():
            setattr(scheme, key, value)
        await self.session.commit()
        await self.session.refresh(scheme)
        return scheme

    async def delete_scheme(self, code: str) -> None:
        scheme = await self.repo.by_code(code)
        if scheme is None:
            raise NotFoundError("Scheme not found.")
        await self.repo.delete_scheme_rows(scheme)
        await self.session.commit()

    # ------------------------------------------------------------ filtering --

    def _state_applies(self, scheme: Scheme, state_code: str) -> bool:
        if scheme.scope == "central":
            return True
        if state_code == "*":
            return True
        return (
            state_code in (scheme.applicable_states or [])
            or scheme.state_code == state_code
            or scheme.state_code == "*"
        )

    @staticmethod
    def _state_overlap(a: Scheme, b: Scheme) -> bool:
        if a.scope == "central" or b.scope == "central":
            return True
        a_states = set(a.applicable_states or []) | (
            {a.state_code} if a.state_code != "*" else set()
        )
        b_states = set(b.applicable_states or []) | (
            {b.state_code} if b.state_code != "*" else set()
        )
        return bool(a_states & b_states)

    def _passes_filters(self, scheme: Scheme, filters: dict[str, Any]) -> bool:
        """Structured (SQL-able) filter conditions — mirrors `browse`."""
        if filters.get("category") and scheme.category != filters["category"]:
            return False
        if (
            filters.get("sub_category")
            and (scheme.sub_category or "").lower() != str(filters["sub_category"]).lower()
        ):
            return False
        if filters.get("scope") and scheme.scope != filters["scope"]:
            return False
        if filters.get("state") and not self._state_applies(scheme, str(filters["state"])):
            return False
        if filters.get("ministry") and _normalize(str(filters["ministry"])) not in _normalize(
            scheme.ministry
        ):
            return False
        if filters.get("department"):
            return _normalize(str(filters["department"])) in _normalize(scheme.department or "")
        return True

    def _passes_demographic(self, scheme: Scheme, params: dict[str, Any]) -> bool:
        """ "Not obviously excluded" semantics for the profile-based filters."""
        rules = scheme.eligibility_rules or []

        def allowed(field: str) -> set[Any]:
            values: set[Any] = set()
            for rule in rules:
                if rule.get("field") != field or rule.get("operator") not in ("eq", "in"):
                    continue
                value = rule.get("value")
                if isinstance(value, list):
                    values.update(value)
                else:
                    values.add(value)
            return values

        if params.get("gender"):
            wants = params["gender"]
            if wants in allowed("gender"):
                pass
            elif allowed("gender"):
                return False  # a gender is constrained and ours is not among them

        for flag in _BOOLEAN_FIELDS:
            if not params.get(flag):
                continue
            values = allowed(flag)
            if values and True not in values:
                return False  # explicit "only for X" rule that isn't this group

        if params.get("isWomen"):
            gender_allowed = allowed("gender")
            if gender_allowed and "female" not in gender_allowed:
                return False
            women_rules = allowed("is_women")
            if women_rules and True not in women_rules:
                return False

        income_bands = allowed("income_band")
        if params.get("incomeBand") and income_bands and params["incomeBand"] not in income_bands:
            return False
        occupations = allowed("occupation")
        if params.get("occupation") and occupations and params["occupation"] not in occupations:
            return False
        education_levels = allowed("education")
        if (
            params.get("education")
            and education_levels
            and params["education"] not in education_levels
        ):
            return False

        age_min = params.get("ageMin")
        age_max = params.get("ageMax")
        if age_min is not None or age_max is not None:
            for rule in rules:
                if rule.get("field") != "age" or rule.get("operator") not in (
                    "gte",
                    "lte",
                    "between",
                ):
                    continue
                operator, value = rule.get("operator"), rule.get("value")
                if operator == "gte" and isinstance(value, (int, float)) and age_max is not None:
                    if value > age_max:
                        return False
                elif operator == "lte" and isinstance(value, (int, float)) and age_min is not None:
                    if value < age_min:
                        return False
                elif operator == "between" and isinstance(value, list) and len(value) == 2:
                    low, high = value
                    if age_min is not None and high < age_min:
                        return False
                    if age_max is not None and low > age_max:
                        return False
        return True


def _sort_key(sort: str) -> Any:
    def key(scheme: Scheme) -> tuple[Any, ...]:
        if sort == "popular":
            return (-scheme.popularity, -scheme.view_count, scheme.code)
        if sort == "updated":
            stamp = scheme.last_verified_at or scheme.updated_at
            return (-stamp.timestamp() if stamp else 0, -scheme.popularity)
        return (-scheme.popularity, scheme.code)

    return key


def _search_sort_key(sort: str) -> Any:
    def key(pair: tuple[Scheme, int]) -> tuple[Any, ...]:
        scheme, score = pair
        if sort == "popular":
            return (-score, -scheme.popularity)
        if sort == "updated":
            ts = scheme.last_verified_at or scheme.updated_at
            return (-score, -(ts.timestamp() if ts else 0))
        return (-score, -scheme.popularity)

    return key

"""Scheme catalog + user scheme-interaction endpoints (Prompt 6).

Public read routes: list, search, suggestions, trending, popular, detail.
Per-user routes (bookmarks, recent views, saved searches) require auth.
Write routes (create/update/delete) are staff-only.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, rate_limit_search
from app.core.security import AuthPrincipal, get_current_user, get_optional_user
from app.schemas.common import Paginated
from app.schemas.scheme import (
    BookmarkStatusOut,
    SavedSearchCreate,
    SavedSearchOut,
    SchemeCreate,
    SchemeOut,
    SchemeSearchResultOut,
    SchemeSummaryOut,
    SchemeUpdate,
    SearchHistoryOut,
    SuggestionsOut,
    TrendingOut,
)
from app.services.scheme import SchemeService
from app.services.user import UserService

router = APIRouter(tags=["schemes"], prefix="/schemes")

DbDep = Annotated[AsyncSession, Depends(get_db)]
PrincipalDep = Annotated[AuthPrincipal, Depends(get_current_user)]
OptionalPrincipalDep = Annotated[AuthPrincipal | None, Depends(get_optional_user)]


# ---------------------------------------------------------------------------
# Public rails (declared before the {code} route to avoid path capture).
# ---------------------------------------------------------------------------


@router.get("/search", response_model=Paginated[SchemeSearchResultOut])
async def search_schemes(
    db: DbDep,
    principal: OptionalPrincipalDep,
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=60),
    sort: str = Query(default="relevance", pattern="^(relevance|popular|updated)$"),
    category: str | None = Query(default=None),
    sub_category: str | None = Query(default=None, max_length=60, alias="subCategory"),
    state: str | None = Query(default=None, max_length=8),
    scope: str | None = Query(default=None, pattern="^(central|state)$"),
    ministry: str | None = Query(default=None, max_length=120),
    department: str | None = Query(default=None, max_length=120),
    gender: str | None = Query(default=None, max_length=20),
    income_band: str | None = Query(default=None, max_length=20, alias="incomeBand"),
    education: str | None = Query(default=None, max_length=30),
    occupation: str | None = Query(default=None, max_length=40),
    is_farmer: bool | None = Query(default=None, alias="isFarmer"),
    is_student: bool | None = Query(default=None, alias="isStudent"),
    is_disabled: bool | None = Query(default=None, alias="isDisabled"),
    is_minority: bool | None = Query(default=None, alias="isMinority"),
    is_senior_citizen: bool | None = Query(default=None, alias="isSeniorCitizen"),
    is_self_employed: bool | None = Query(default=None, alias="isSelfEmployed"),
    is_women: bool | None = Query(default=None, alias="isWomen"),
    age_min: int | None = Query(default=None, ge=0, le=130, alias="ageMin"),
    age_max: int | None = Query(default=None, ge=0, le=130, alias="ageMax"),
) -> Paginated[SchemeSearchResultOut]:
    """Keyword/partial/misspelled search + profile filters (rate-limited)."""
    service = SchemeService(db)
    filters = {
        "category": category,
        "sub_category": sub_category,
        "state": state,
        "scope": scope,
        "ministry": ministry,
        "department": department,
        "gender": gender,
        "incomeBand": income_band,
        "education": education,
        "occupation": occupation,
        "isFarmer": is_farmer,
        "isStudent": is_student,
        "isDisabled": is_disabled,
        "isMinority": is_minority,
        "isSeniorCitizen": is_senior_citizen,
        "isSelfEmployed": is_self_employed,
        "isWomen": is_women,
        "ageMin": age_min,
        "ageMax": age_max,
    }
    filters = {key: value for key, value in filters.items() if value is not None}
    items, total = await service.search(
        q=q, page=page, page_size=page_size, sort=sort, filters=filters
    )
    if principal and not principal.is_guest and q.strip():
        user = await UserService(db).get_or_create_by_firebase(principal.uid)
        await service.record_search(user.id, q.strip(), filters or {})
    return Paginated(
        items=[
            SchemeSearchResultOut.model_validate(service.to_summary(scheme, match_score=score))
            for scheme, score in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/suggestions",
    response_model=SuggestionsOut,
    dependencies=[Depends(rate_limit_search)],
)
async def search_suggestions(
    db: DbDep,
    q: str = Query(default="", max_length=60),
    limit: int = Query(default=8, ge=1, le=20),
) -> SuggestionsOut:
    """Autocomplete + "did you mean" corrections."""
    return await SchemeService(db).suggestions(q, limit=limit)


@router.get("/trending", response_model=list[TrendingOut])
async def trending_schemes(
    db: DbDep,
    limit: int = Query(default=8, ge=1, le=24),
) -> list[TrendingOut]:
    """Currently trending schemes (editor popularity, cached)."""
    return await SchemeService(db).trending(limit=limit)


@router.get("/popular", response_model=list[TrendingOut])
async def popular_schemes(
    db: DbDep,
    limit: int = Query(default=8, ge=1, le=24),
) -> list[TrendingOut]:
    """Most-viewed schemes (live counters, cached)."""
    return await SchemeService(db).popular(limit=limit)


@router.get("/categories/popular", response_model=list[dict])
async def popular_categories(db: DbDep) -> list[dict]:
    """Category popularity counts for the browse rails."""
    return await SchemeService(db).popular_categories()


# ---------------------------------------------------------------------------
# Authenticated, user-scoped routes
# ---------------------------------------------------------------------------


@router.get("/me/saved", response_model=Paginated[SchemeSummaryOut])
async def list_saved_schemes(
    principal: PrincipalDep,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=60),
) -> Paginated[SchemeSummaryOut]:
    """Bookmarked schemes, most recently saved first."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).list_bookmarks(user.id, page=page, page_size=page_size)


@router.put("/me/saved/{scheme_id}", response_model=BookmarkStatusOut)
async def save_scheme(
    scheme_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> BookmarkStatusOut:
    """Bookmark a scheme (idempotent)."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).add_bookmark(user.id, scheme_id)


@router.delete("/me/saved/{scheme_id}", response_model=BookmarkStatusOut)
async def unsave_scheme(
    scheme_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> BookmarkStatusOut:
    """Remove a bookmark (idempotent)."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).remove_bookmark(user.id, scheme_id)


@router.get("/me/recent", response_model=list[SchemeSummaryOut])
async def recently_viewed(
    principal: PrincipalDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[SchemeSummaryOut]:
    """Schemes the caller has opened recently."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).recent_views(user.id, limit=limit)


@router.get("/me/searches", response_model=Paginated[SavedSearchOut])
async def list_saved_searches(
    principal: PrincipalDep,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> Paginated[SavedSearchOut]:
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).list_saved_searches(user.id, page=page, page_size=page_size)


@router.post("/me/searches", response_model=SavedSearchOut, status_code=201)
async def create_saved_search(
    payload: SavedSearchCreate,
    principal: PrincipalDep,
    db: DbDep,
) -> SavedSearchOut:
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).save_search(user.id, payload)


@router.delete("/me/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> None:
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    await SchemeService(db).delete_saved_search(user.id, search_id)


@router.get("/me/search-history", response_model=list[SearchHistoryOut])
async def search_history(
    principal: PrincipalDep,
    db: DbDep,
    limit: int = Query(default=10, ge=1, le=20),
) -> list[SearchHistoryOut]:
    """Recent searches for the caller (recency-first)."""
    user = await UserService(db).get_or_create_by_firebase(principal.uid)
    return await SchemeService(db).search_history(user.id, limit=limit)


# ---------------------------------------------------------------------------
# Catalog reads
# ---------------------------------------------------------------------------


@router.get("", response_model=Paginated[SchemeSummaryOut])
async def list_schemes(
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=60),
    sort: str = Query(default="popular", pattern="^(popular|updated|relevance)$"),
    category: str | None = Query(default=None, max_length=30),
    sub_category: str | None = Query(default=None, max_length=60, alias="subCategory"),
    state: str | None = Query(default=None, max_length=8),
    scope: str | None = Query(default=None, pattern="^(central|state)$"),
    ministry: str | None = Query(default=None, max_length=120),
    department: str | None = Query(default=None, max_length=120),
    gender: str | None = Query(default=None, max_length=20),
    income_band: str | None = Query(default=None, max_length=20, alias="incomeBand"),
    education: str | None = Query(default=None, max_length=30),
    occupation: str | None = Query(default=None, max_length=40),
    is_farmer: bool | None = Query(default=None, alias="isFarmer"),
    is_student: bool | None = Query(default=None, alias="isStudent"),
    is_disabled: bool | None = Query(default=None, alias="isDisabled"),
    is_minority: bool | None = Query(default=None, alias="isMinority"),
    is_senior_citizen: bool | None = Query(default=None, alias="isSeniorCitizen"),
    is_self_employed: bool | None = Query(default=None, alias="isSelfEmployed"),
    is_women: bool | None = Query(default=None, alias="isWomen"),
    age_min: int | None = Query(default=None, ge=0, le=130, alias="ageMin"),
    age_max: int | None = Query(default=None, ge=0, le=130, alias="ageMax"),
) -> Paginated[SchemeSummaryOut]:
    """Browse the catalog with structured + demographic filters."""
    demographic = {
        "gender": gender,
        "incomeBand": income_band,
        "education": education,
        "occupation": occupation,
        "isFarmer": is_farmer,
        "isStudent": is_student,
        "isDisabled": is_disabled,
        "isMinority": is_minority,
        "isSeniorCitizen": is_senior_citizen,
        "isSelfEmployed": is_self_employed,
        "isWomen": is_women,
        "ageMin": age_min,
        "ageMax": age_max,
    }
    items, total = await SchemeService(db).browse(
        page=page,
        page_size=page_size,
        sort=sort,
        category=category,
        sub_category=sub_category,
        state=state,
        scope=scope,
        ministry=ministry,
        department=department,
        demographic=demographic,
    )
    service = SchemeService(db)
    return Paginated(
        items=[service.to_summary(scheme) for scheme in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{code}/related", response_model=list[SchemeSummaryOut])
async def related_schemes(
    code: str,
    db: DbDep,
    limit: int = Query(default=6, ge=1, le=12),
) -> list[SchemeSummaryOut]:
    """Same-category/ministry/state suggestions for the detail page."""
    service = SchemeService(db)
    scheme = await service.get_public(code)
    related = await service.related(scheme, limit=limit)
    return [service.to_summary(s) for s in related]


@router.get("/{code}", response_model=SchemeOut)
async def get_scheme(
    code: str,
    db: DbDep,
    principal: OptionalPrincipalDep,
) -> SchemeOut:
    """Fetch one scheme's full details (also bumps its view counter)."""
    service = SchemeService(db)
    scheme = await service.get_public(code)
    user = None
    if principal and not principal.is_guest:
        user = await UserService(db).get_or_create_by_firebase(principal.uid)
    await service.record_scheme_view(scheme, user_id=user.id if user else None)
    return service.to_out(scheme)


# ---------------------------------------------------------------------------
# Admin CRUD (staff only)
# ---------------------------------------------------------------------------


@router.post("", response_model=SchemeOut, status_code=201)
async def create_scheme(
    payload: SchemeCreate,
    principal: PrincipalDep,
    db: DbDep,
) -> SchemeOut:
    """Create a scheme (staff only)."""
    principal.require_role("admin", "content_editor")
    scheme = await SchemeService(db).create_scheme(payload)
    return SchemeService(db).to_out(scheme)


@router.put("/{code}", response_model=SchemeOut)
async def update_scheme(
    code: str,
    payload: SchemeUpdate,
    principal: PrincipalDep,
    db: DbDep,
) -> SchemeOut:
    """Partial update of a scheme (staff only)."""
    principal.require_role("admin", "content_editor")
    service = SchemeService(db)
    scheme = await service.update_scheme(code, payload)
    return service.to_out(scheme)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheme(
    code: str,
    principal: PrincipalDep,
    db: DbDep,
) -> None:
    """Delete a scheme + its saved/view rows (staff only)."""
    principal.require_role("admin", "content_editor")
    await SchemeService(db).delete_scheme(code)

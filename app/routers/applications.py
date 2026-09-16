from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, or_, select

from app.enums import Status
from app.models import Application, StatusHistory
from app.schemas import (
    ApplicationCreate,
    ApplicationPatch,
    ApplicationRead,
    HistoryRead,
)
from app.security import CurrentUser, Db

router = APIRouter(tags=["applications"])


def owned_application(db, user_id, application_id, *, lock=False):
    query = select(Application).where(
        Application.id == application_id,
        Application.user_id == user_id,
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return item


@router.post("/applications", response_model=ApplicationRead, status_code=201)
def create_application(payload: ApplicationCreate, db: Db, user: CurrentUser):
    item = Application(
        user_id=user.id,
        **payload.model_dump(mode="json"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/applications", response_model=list[ApplicationRead])
def list_applications(
    db: Db,
    user: CurrentUser,
    status: Status | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Application).where(Application.user_id == user.id)
    if status is not None:
        query = query.where(Application.status == status)
    if search is not None:
        query = query.where(
            or_(
                Application.company.icontains(search, autoescape=True),
                Application.position.icontains(search, autoescape=True),
            )
        )
    query = query.order_by(
        Application.created_at.desc(), Application.id.desc()
    ).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/applications/{application_id}", response_model=ApplicationRead)
def get_application(application_id: int, db: Db, user: CurrentUser):
    return owned_application(db, user.id, application_id)


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
def patch_application(
    application_id: int,
    payload: ApplicationPatch,
    db: Db,
    user: CurrentUser,
):
    item = owned_application(db, user.id, application_id, lock=True)
    data = payload.model_dump(exclude_unset=True, mode="json")
    old_status = item.status.value
    if "status" in data and data["status"] != old_status:
        db.add(
            StatusHistory(
                application_id=item.id,
                old_status=old_status,
                new_status=data["status"],
            )
        )
    for name, value in data.items():
        setattr(item, name, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: int, db: Db, user: CurrentUser):
    item = owned_application(db, user.id, application_id, lock=True)
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@router.get(
    "/applications/{application_id}/history",
    response_model=list[HistoryRead],
)
def get_history(application_id: int, db: Db, user: CurrentUser):
    owned_application(db, user.id, application_id)
    query = select(StatusHistory).where(
        StatusHistory.application_id == application_id
    ).order_by(StatusHistory.changed_at, StatusHistory.id)
    return list(db.scalars(query))


@router.get("/stats")
def get_stats(db: Db, user: CurrentUser):
    query = (
        select(Application.status, func.count(Application.id))
        .where(Application.user_id == user.id)
        .group_by(Application.status)
    )
    counts = {status.value: 0 for status in Status}
    for status, count in db.execute(query):
        counts[status.value] = count
    return {"total": sum(counts.values()), "by_status": counts}
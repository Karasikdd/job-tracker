from enum import Enum

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Job Tracker API")


class Status(str, Enum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    status: Status = Status.saved


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status


applications: dict[int, dict] = {}
next_id = 1


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/applications", status_code=201)
async def create_application(payload: ApplicationCreate):
    global next_id
    item = {"id": next_id, **payload.model_dump()}
    applications[next_id] = item
    next_id += 1
    return item


@app.get("/applications")
async def list_applications():
    return list(applications.values())


@app.get("/applications/{application_id}")
async def get_application(application_id: int):
    if application_id not in applications:
        raise HTTPException(status_code=404, detail="Application not found")
    return applications[application_id]


@app.patch("/applications/{application_id}")
async def update_application(application_id: int, payload: StatusUpdate):
    item = await get_application(application_id)
    item["status"] = payload.status
    return item


@app.delete("/applications/{application_id}", status_code=204)
async def delete_application(application_id: int):
    await get_application(application_id)
    del applications[application_id]
    return Response(status_code=204)
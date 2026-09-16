from fastapi import FastAPI

from app.routers import applications, auth
from app.schemas import UserRead
from app.security import CurrentUser

app = FastAPI(title="Job Tracker API", version="0.1.0")
app.include_router(auth.router)
app.include_router(applications.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/users/me", response_model=UserRead, tags=["users"])
def read_me(user: CurrentUser):
    return user
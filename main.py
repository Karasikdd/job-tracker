from fastapi import FastAPI

app = FastAPI(title="Job Tracker API")


@app.get("/health")
def health():
    return {"status": "ok","version": "1.01"}
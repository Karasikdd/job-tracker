from fastapi import FastAPI

app = FastAPI(title="Job Tracker API")
a=1

@app.get("/health")
def health():
    return {"status": "ok","version": "1.01"}
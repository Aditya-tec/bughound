from fastapi import FastAPI

from api.routers import github_app, issues, jobs

app = FastAPI(title="BugHound API")

app.include_router(jobs.router)
app.include_router(issues.router)
app.include_router(github_app.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

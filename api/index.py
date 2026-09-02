from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import github_app, issues, jobs

app = FastAPI(title="BugHound API")

# Wildcard is fine here: every route is either a public, shareable scan report or
# gated by possession of a job id / GitHub PAT — there's no cookie-based auth for
# allow_credentials to leak, and Vercel preview deployments get a new origin per PR.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(issues.router)
app.include_router(github_app.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

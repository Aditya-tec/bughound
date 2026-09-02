from typing import Literal

from pydantic import BaseModel, HttpUrl


class CreateJobRequest(BaseModel):
    target_url: HttpUrl
    mode: Literal["scan", "owner"]


class CreateJobResponse(BaseModel):
    job_id: str

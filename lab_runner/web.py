"""FastAPI web application for Lab Runner with SSE streaming."""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from lab_runner.config import Config
from lab_runner.modules import MODULE_REGISTRY
from lab_runner.runner import Runner, resolve_dependencies

app = FastAPI(title="Lab Runner — AI501")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class RunRequest(BaseModel):
    username: str
    password: str
    cluster_domain: str
    modules: list[int] = []
    up_to: int | None = None


class StatusRequest(BaseModel):
    username: str
    password: str
    cluster_domain: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/modules")
async def list_modules():
    modules = []
    for mid in sorted(MODULE_REGISTRY):
        m = MODULE_REGISTRY[mid]()
        modules.append({
            "id": mid,
            "name": m.name,
            "dependencies": m.dependencies,
        })
    return modules


@app.post("/api/run")
async def run_modules(req: RunRequest):
    module_ids = req.modules
    if req.up_to is not None:
        module_ids = [mid for mid in sorted(MODULE_REGISTRY) if mid <= req.up_to]

    if not module_ids:
        return {"error": "No modules selected"}

    config = Config(
        username=req.username,
        password=req.password,
        cluster_domain=req.cluster_domain,
    )
    runner = Runner(config)

    async def event_stream():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _produce():
            for event in runner.run_modules_streaming(module_ids):
                loop.call_soon_threadsafe(queue.put_nowait, event)
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        loop.run_in_executor(None, _produce)

        while True:
            event = await queue.get()
            if event is sentinel:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/status")
async def check_status(req: StatusRequest):
    config = Config(
        username=req.username,
        password=req.password,
        cluster_domain=req.cluster_domain,
    )
    runner = Runner(config)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, runner.get_status)
    return result


def serve():
    """Entry point for lab-runner-web console script."""
    import uvicorn

    uvicorn.run(
        "lab_runner.web:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from holodeck_core.pipeline.factory import create_pipeline
from holodeck_core.pipeline.stage_data import StageData

app = FastAPI(title="Holodeck Web")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Store running tasks and review events
tasks: dict[str, dict] = {}
review_events: dict[str, asyncio.Event] = {}
review_decisions: dict[str, str] = {}  # "pass" or "retry"

STAGES = ["scene_ref", "extract", "cards", "constraints", "layout", "assets"]


def read_env_file() -> dict[str, str]:
    """Read .env file and return as dict."""
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    result = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


@app.get("/config/status")
async def config_status():
    """Check API key configuration status (reads .env file in real-time)."""
    env = read_env_file()
    return {
        "image": bool(env.get("IMAGE_GEN_API_KEY", "")),
        "image_protocol": env.get("IMAGE_GEN_PROTOCOL", "gemini"),
        "image_url": env.get("IMAGE_GEN_BASE_URL", ""),
        "image_model": env.get("IMAGE_GEN_MODEL", ""),
        "vlm": bool(env.get("CUSTOM_VLM_API_KEY", "")),
        "vlm_url": env.get("CUSTOM_VLM_BASE_URL", ""),
        "vlm_model": env.get("CUSTOM_VLM_MODEL_NAME", ""),
        "hunyuan": bool(env.get("HUNYUAN_SECRET_ID", "") and env.get("HUNYUAN_SECRET_KEY", "")),
        "asset_retrieval": env.get("ASSET_RETRIEVAL_ENABLED", "").lower() == "true",
        "asset_threshold": env.get("ASSET_RETRIEVAL_THRESHOLD", "0.25"),
        "review_stages": env.get("REVIEW_STAGES", "").split(",") if env.get("REVIEW_STAGES") else []
    }


@app.post("/config/save", response_class=HTMLResponse)
async def config_save(
    request: Request,
    image_protocol: str = Form(""),
    image_url: str = Form(""),
    image_key: str = Form(""),
    image_model: str = Form(""),
    vlm_url: str = Form(""),
    vlm_key: str = Form(""),
    vlm_model: str = Form(""),
    hunyuan_id: str = Form(""),
    hunyuan_key: str = Form(""),
    asset_retrieval: str = Form(""),
    asset_threshold: str = Form(""),
    review_scene_ref: str = Form(""),
    review_extract: str = Form(""),
    review_cards: str = Form(""),
    review_constraints: str = Form(""),
    review_layout: str = Form(""),
    review_assets: str = Form("")
):
    """Save API keys to .env file."""
    env_path = Path(".env")
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    def update_key(lines, key, value):
        if not value:
            return lines
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                return lines
        lines.append(f"{key}={value}")
        return lines

    # 图像生成配置
    if image_protocol:
        lines = update_key(lines, "IMAGE_GEN_PROTOCOL", image_protocol)
        os.environ["IMAGE_GEN_PROTOCOL"] = image_protocol
    if image_url:
        lines = update_key(lines, "IMAGE_GEN_BASE_URL", image_url)
        os.environ["IMAGE_GEN_BASE_URL"] = image_url
    if image_key:
        lines = update_key(lines, "IMAGE_GEN_API_KEY", image_key)
        os.environ["IMAGE_GEN_API_KEY"] = image_key
    if image_model:
        lines = update_key(lines, "IMAGE_GEN_MODEL", image_model)
        os.environ["IMAGE_GEN_MODEL"] = image_model

    # VLM 配置
    if vlm_url:
        lines = update_key(lines, "VLM_BASE_URL", vlm_url)
        os.environ["VLM_BASE_URL"] = vlm_url
    if vlm_key:
        lines = update_key(lines, "VLM_API_KEY", vlm_key)
        os.environ["VLM_API_KEY"] = vlm_key
    if vlm_model:
        lines = update_key(lines, "VLM_MODEL", vlm_model)
        os.environ["VLM_MODEL"] = vlm_model

    # Hunyuan 3D 配置
    if hunyuan_id:
        lines = update_key(lines, "HUNYUAN_SECRET_ID", hunyuan_id)
        os.environ["HUNYUAN_SECRET_ID"] = hunyuan_id
    if hunyuan_key:
        lines = update_key(lines, "HUNYUAN_SECRET_KEY", hunyuan_key)
        os.environ["HUNYUAN_SECRET_KEY"] = hunyuan_key

    # 资产检索配置
    retrieval_value = "true" if asset_retrieval == "on" else "false"
    lines = update_key(lines, "ASSET_RETRIEVAL_ENABLED", retrieval_value)
    os.environ["ASSET_RETRIEVAL_ENABLED"] = retrieval_value
    if asset_threshold:
        lines = update_key(lines, "ASSET_RETRIEVAL_THRESHOLD", asset_threshold)
        os.environ["ASSET_RETRIEVAL_THRESHOLD"] = asset_threshold

    # 人工审查配置
    review_stages = []
    if review_scene_ref == "on": review_stages.append("scene_ref")
    if review_extract == "on": review_stages.append("extract")
    if review_cards == "on": review_stages.append("cards")
    if review_constraints == "on": review_stages.append("constraints")
    if review_layout == "on": review_stages.append("layout")
    if review_assets == "on": review_stages.append("assets")
    review_value = ",".join(review_stages)
    lines = update_key(lines, "REVIEW_STAGES", review_value)
    os.environ["REVIEW_STAGES"] = review_value

    env_path.write_text("\n".join(lines) + "\n")
    return "<div class='text-green-400'>✓ 配置已保存</div>"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page."""
    sessions = list_sessions()
    config = await config_status()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stages": STAGES,
        "sessions": sessions,
        "config": config
    })


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    text: str = Form(...),
    style: str = Form("realistic"),
    from_stage: str = Form("scene_ref"),
    until: str = Form("assets")
):
    """Start generation and return SSE endpoint."""
    import time
    import uuid

    if STAGES.index(from_stage) > STAGES.index(until):
        return HTMLResponse(f"Error: from_stage '{from_stage}' must be before or equal to until '{until}'", status_code=400)

    session_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    tasks[session_id] = {"status": "pending", "stage": "", "data": None}

    return templates.TemplateResponse("partials/status.html", {
        "request": request,
        "session_id": session_id,
        "text": text,
        "style": style,
        "from_stage": from_stage,
        "until": until
    })


@app.get("/stream/{session_id}")
async def stream(session_id: str, text: str, style: str, from_stage: str = "scene_ref", until: str = "assets"):
    """SSE endpoint for pipeline progress."""
    # Prevent duplicate execution for same session
    task = tasks.get(session_id, {})
    if task.get("status") in ("running", "done"):
        async def status_only():
            yield f"data: {json.dumps({'status': task.get('status'), 'stage': task.get('stage', '')})}\n\n"
        return StreamingResponse(status_only(), media_type="text/event-stream")

    tasks[session_id] = {"status": "running", "stage": "", "data": None}

    # Get review stages from env
    env = read_env_file()
    review_stages = set(env.get("REVIEW_STAGES", "").split(",")) if env.get("REVIEW_STAGES") else set()

    async def event_generator():
        try:
            runner = create_pipeline(
                workspace="workspace",
                from_stage=from_stage,
                until=until if until != "assets" else None
            )

            # Run pipeline with progress updates
            data = None
            for i, stage in enumerate(runner.stages):
                stage_name = stage.name
                tasks[session_id]["stage"] = stage_name
                yield f"data: {json.dumps({'stage': stage_name, 'status': 'running'})}\n\n"

                if data is None:
                    import time
                    import uuid
                    session_dir = Path("workspace/sessions") / session_id
                    session_dir.mkdir(parents=True, exist_ok=True)
                    data = StageData(
                        session_id=session_id,
                        session_dir=session_dir,
                        scene_text=text,
                        style=style
                    )

                data = await stage.run(data)
                yield f"data: {json.dumps({'stage': stage_name, 'status': 'done'})}\n\n"

                # Check if review is needed for this stage
                if stage_name in review_stages:
                    review_key = f"{session_id}_{stage_name}"
                    review_events[review_key] = asyncio.Event()
                    review_decisions[review_key] = None

                    # Send review request to frontend
                    yield f"data: {json.dumps({'stage': stage_name, 'status': 'review', 'session_id': session_id})}\n\n"

                    # Wait for user decision
                    await review_events[review_key].wait()
                    decision = review_decisions.get(review_key, "pass")

                    # Clean up
                    del review_events[review_key]
                    del review_decisions[review_key]

                    if decision == "retry":
                        # Re-run this stage
                        data = await stage.run(data)
                        yield f"data: {json.dumps({'stage': stage_name, 'status': 'done', 'retried': True})}\n\n"

            tasks[session_id]["status"] = "done"
            tasks[session_id]["data"] = data.to_dict() if data else {}
            yield f"data: {json.dumps({'status': 'complete', 'session_id': session_id})}\n\n"

        except Exception as e:
            tasks[session_id]["status"] = "error"
            tasks[session_id]["error"] = str(e)
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/result/{session_id}", response_class=HTMLResponse)
async def result(request: Request, session_id: str):
    """Get result partial."""
    task = tasks.get(session_id, {})
    data = task.get("data", {})

    # Load from disk if not in memory
    if not data:
        session_dir = Path("workspace/sessions") / session_id
        manifest = session_dir / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text())

    return templates.TemplateResponse("partials/result.html", {
        "request": request,
        "session_id": session_id,
        "data": data
    })


@app.get("/image/{session_id}/{filename}")
async def serve_image(session_id: str, filename: str):
    """Serve generated images."""
    path = Path("workspace/sessions") / session_id / filename
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("Not found", status_code=404)


@app.post("/review/{session_id}/{stage}")
async def review_decision(session_id: str, stage: str, decision: str = Form(...)):
    """Handle user review decision (pass/retry)."""
    review_key = f"{session_id}_{stage}"
    if review_key in review_events:
        review_decisions[review_key] = decision
        review_events[review_key].set()
        return {"status": "ok", "decision": decision}
    return {"status": "error", "message": "No pending review"}


@app.get("/review/{session_id}/{stage}", response_class=HTMLResponse)
async def review_page(request: Request, session_id: str, stage: str):
    """Get review UI for a stage."""
    session_dir = Path("workspace/sessions") / session_id

    # Gather stage outputs for review
    outputs = []
    if stage == "scene_ref":
        scene_ref = session_dir / "scene_ref.png"
        if scene_ref.exists():
            outputs.append({"type": "image", "path": f"/image/{session_id}/scene_ref.png"})
    elif stage == "extract":
        objects_json = session_dir / "objects.json"
        if objects_json.exists():
            outputs.append({"type": "json", "content": objects_json.read_text()})
    elif stage == "cards":
        cards_dir = session_dir / "object_cards"
        if cards_dir.exists():
            for img in cards_dir.glob("*.png"):
                outputs.append({"type": "image", "path": f"/image/{session_id}/object_cards/{img.name}"})
    elif stage in ("constraints", "layout"):
        json_file = session_dir / f"{stage}.json"
        if json_file.exists():
            outputs.append({"type": "json", "content": json_file.read_text()})
    elif stage == "assets":
        assets_dir = session_dir / "assets"
        if assets_dir.exists():
            for glb in assets_dir.glob("*.glb"):
                outputs.append({"type": "model", "path": f"/image/{session_id}/assets/{glb.name}"})

    return templates.TemplateResponse("partials/review.html", {
        "request": request,
        "session_id": session_id,
        "stage": stage,
        "outputs": outputs
    })


def list_sessions() -> list[dict]:
    """List existing sessions."""
    sessions_dir = Path("workspace/sessions")
    if not sessions_dir.exists():
        return []

    sessions = []
    for d in sorted(sessions_dir.iterdir(), reverse=True)[:10]:
        if d.is_dir():
            manifest = d / "manifest.json"
            info = {"id": d.name, "text": ""}
            if manifest.exists():
                try:
                    m = json.loads(manifest.read_text())
                    info["text"] = m.get("scene_text", "")[:50]
                except:
                    pass
            sessions.append(info)
    return sessions


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

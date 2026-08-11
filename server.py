import asyncio
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from core.telegram_engine import TelegramGrowthEngine
import config

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Telegram Growth Suite", version="3.0.0")
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

engine = TelegramGrowthEngine()
active_sockets: List[WebSocket] = []

# ─── WebSocket Manager ──────────────────────────────────────

async def broadcast(data: dict):
    for ws in list(active_sockets):
        try:
            await ws.send_json(data)
        except Exception:
            pass

# ─── Request Models ─────────────────────────────────────────

class LoginModel(BaseModel):
    api_id: int
    api_hash: str
    phone: str

class OTPModel(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    password: Optional[str] = None

class ScrapeModel(BaseModel):
    target_group: str
    only_active: bool = True
    only_photo: bool = False

class InviteModel(BaseModel):
    dest_group: str
    delay_seconds: int = 35
    max_invites: int = 30

class PipelineModel(BaseModel):
    target_group: str
    dest_group: str
    delay_seconds: int = 35
    max_invites: int = 30
    only_active: bool = True
    only_photo: bool = False

# ─── Routes ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_sockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_sockets:
            active_sockets.remove(websocket)

@app.post("/api/login")
async def login(data: LoginModel):
    try:
        result = await engine.connect(data.api_id, data.api_hash, data.phone)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.post("/api/verify-otp")
async def verify_otp(data: OTPModel):
    try:
        result = await engine.verify_otp(data.phone, data.code, data.phone_code_hash, data.password)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.post("/api/logout")
async def logout():
    try:
        result = await engine.logout()
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@app.post("/api/scrape")
async def start_scrape(data: ScrapeModel):
    async def cb(msg): await broadcast(msg)
    async def run():
        try:
            count = await engine.scrape(
                target_link=data.target_group,
                csv_file=config.CSV_FILE_PATH,
                only_active=data.only_active,
                only_photo=data.only_photo,
                cb=cb
            )
            await broadcast({"type": "scrape_done", "count": count})
        except Exception as e:
            await broadcast({"type": "log", "message": f"❌ Lỗi Scraper: {str(e)}"})
    asyncio.create_task(run())
    return {"status": "started"}

@app.post("/api/invite")
async def start_invite(data: InviteModel):
    async def cb(msg): await broadcast(msg)
    async def run():
        try:
            added = await engine.invite(
                dest_link=data.dest_group,
                csv_file=config.CSV_FILE_PATH,
                delay=data.delay_seconds,
                max_per_session=data.max_invites,
                cb=cb
            )
            await broadcast({"type": "invite_done", "added": added})
        except Exception as e:
            await broadcast({"type": "log", "message": f"❌ Lỗi Inviter: {str(e)}"})
    asyncio.create_task(run())
    return {"status": "started"}

@app.post("/api/pipeline")
async def start_pipeline(data: PipelineModel):
    async def cb(msg): await broadcast(msg)
    async def run():
        try:
            await engine.run_pipeline(
                target_link=data.target_group,
                dest_link=data.dest_group,
                csv_file=config.CSV_FILE_PATH,
                delay=data.delay_seconds,
                max_per_session=data.max_invites,
                only_active=data.only_active,
                only_photo=data.only_photo,
                cb=cb
            )
        except Exception as e:
            await broadcast({"type": "log", "message": f"❌ Lỗi Pipeline: {str(e)}"})
    asyncio.create_task(run())
    return {"status": "started"}

@app.post("/api/stop")
async def stop():
    engine.stop()
    await broadcast({"type": "log", "message": "🛑 Đã nhận lệnh dừng!"})
    return {"status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

import asyncio
import os
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
from typing import List, Dict, Any
from dotenv import load_dotenv
# Database
from database import init_db, get_all_devices, add_device, remove_device

# 🔐 Muat variabel lingkungan
load_dotenv()

# Validasi env var
required_vars = ["DASHBOARD_USERNAME", "DASHBOARD_PASSWORD", "TB_URL", "TB_EMAIL", "TB_PASSWORD"]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Environment variable {var} is required but not set!")

DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
TB_URL = os.getenv("TB_URL")
TB_EMAIL = os.getenv("TB_EMAIL")
TB_PASSWORD = os.getenv("TB_PASSWORD")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# CORS (opsional untuk development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session sederhana
active_sessions = {}

def verify_login(username: str, password: str) -> bool:
    return (
        secrets.compare_digest(username, DASHBOARD_USERNAME) and
        secrets.compare_digest(password, DASHBOARD_PASSWORD)
    )

def create_session(user_id: str) -> str:
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=2)
    }
    return session_id

def get_current_user(request: Request) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in active_sessions:
        return None
    
    session = active_sessions[session_id]
    if session["expires_at"] < datetime.now():
        del active_sessions[session_id]
        return None
    
    return session["user_id"]

# Endpoint Login
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    if not verify_login(username, password):
        return RedirectResponse(url="/login?error=Invalid+credentials", status_code=status.HTTP_303_SEE_OTHER)
    
    session_id = create_session(username)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,
        max_age=7200,
        path="/"
    )
    return response

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        active_sessions.pop(session_id, None)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_id")
    return response

# State global
tb_token: str = None
all_devices_state: Dict[str, Dict] = {}
active_connections: List[WebSocket] = []

# Helper: Get ThingsBoard token (tetap sama)
async def get_token(session: aiohttp.ClientSession) -> str:
    global tb_token
    if tb_token:
        return tb_token

    login_url = f"{TB_URL}/api/auth/login"
    payload = {"username": TB_EMAIL, "password": TB_PASSWORD}
    try:
        async with session.post(login_url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                tb_token = data.get("token")
                print("✅ Authenticated with ThingsBoard")
                return tb_token
            else:
                print(f"❌ Login failed: {await resp.text()}")
                return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

# Helper: Fetch telemetry (tetap sama)
async def fetch_telemetry(session: aiohttp.ClientSession, device_id: str) -> Dict[str, Any]:
    token = await get_token(session)
    if not token:
        return {"device_id": device_id, "error": "auth_failed"}

    headers = {"X-Authorization": f"Bearer {token}"}
    url = f"{TB_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys=waterLevel,pumpStatus,mode"
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "device_id": device_id,
                    "waterLevel": float(data.get("waterLevel", [{"value": "0"}])[0]["value"]),
                    "pumpStatus": data.get("pumpStatus", [{"value": "false"}])[0]["value"].lower() == "true",
                    "mode": data.get("mode", [{"value": "automatic"}])[0]["value"]
                }
            elif resp.status == 401:
                global tb_token
                tb_token = None
                return await fetch_telemetry(session, device_id)
            else:
                return {"device_id": device_id, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"device_id": device_id, "error": str(e)}

# Helper: Send RPC (tetap sama)
async def send_rpc(session: aiohttp.ClientSession, device_id: str, method: str, params):
    token = await get_token(session)
    if not token:
        return False

    headers = {"X-Authorization": f"Bearer {token}"}
    url = f"{TB_URL}/api/plugins/rpc/twoway/{device_id}"
    payload = {"method": method, "params": params}
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                return True
            elif resp.status == 401:
                global tb_token
                tb_token = None
                return await send_rpc(session, device_id, method, params)
            return False
    except Exception as e:
        print(f"RPC error: {e}")
        return False

# Broadcast all devices state
async def broadcast_all_devices():
    devices_list = await get_all_devices()
    full_devices = []
    for dev in devices_list:
        state = all_devices_state.get(dev["id"], {})
        full_devices.append({**dev, **state})

    for ws in active_connections[:]:
        try:
            await ws.send_json({"type": "all_devices", "data": full_devices})
        except:
            if ws in active_connections:
                active_connections.remove(ws)

# Background task: update all devices
async def devices_updater():
    global all_devices_state
    while True:
        devices_list = await get_all_devices()
        if not devices_list:
            await asyncio.sleep(3)
            continue

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_telemetry(session, dev["id"]) for dev in devices_list]
            results = await asyncio.gather(*tasks)

            for res in results:
                if "error" not in res:
                    all_devices_state[res["device_id"]] = res

            await broadcast_all_devices()
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup():
    print("🚀 Starting Water Tank Dashboard...")
    await init_db()  # ← Inisialisasi database
    asyncio.create_task(devices_updater())

# Endpoint utama
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    session_id = request.cookies.get("session_id")
    return templates.TemplateResponse("dashboard.html", {"request": request, "session_id": session_id})

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id")
    if not session_id or session_id not in active_sessions:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await websocket.accept()
    active_connections.append(websocket)
    await broadcast_all_devices()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "add_device":
                dev = data.get("device", {})
                device_id = dev.get("id", "").strip()
                name = dev.get("name", "").strip()
                location = dev.get("location", "").strip()

                if device_id and name:
                    await add_device(device_id, name, location)
                    print(f"✅ Added device: {name} ({device_id})")
                    await broadcast_all_devices()

            elif msg_type == "remove_device":
                device_id = data.get("device_id")
                await remove_device(device_id)
                all_devices_state.pop(device_id, None)
                await broadcast_all_devices()

            elif msg_type == "command":
                device_id = data.get("device_id")
                command = data.get("command")
                params = data.get("params")
                devices_list = await get_all_devices()
                if any(d["id"] == device_id for d in devices_list):
                    async with aiohttp.ClientSession() as session:
                        if command == "setMode" and params in ["automatic", "manual"]:
                            await send_rpc(session, device_id, "setMode", params)
                        elif command == "setPumpStatus" and isinstance(params, bool):
                            await send_rpc(session, device_id, "setPumpStatus", params)

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

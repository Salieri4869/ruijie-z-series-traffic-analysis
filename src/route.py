from fastapi import APIRouter,Request,WebSocket,WebSocketDisconnect,Depends
import asyncio
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from firewall import firewall
from config import get_settings
from models import SessionInfo,PolicyAction,StopCaptureReq,AppIP
from utils.sniffer import Sniffer
from utils.pysharkja import JaFilter
from utils.connector import manager
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


router = APIRouter()
templates = Jinja2Templates(directory="templates")
app_ip = AppIP()
executor = ProcessPoolExecutor(max_workers=1)
queue = asyncio.Queue() 
settings = get_settings()

sniffer = Sniffer(settings.sniffer_interface,settings.sniffer_filter,queue)

@router.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        "firewall.html",
        {"request": request,
        "page_title": settings.page_title,
        "welcome_message": "欢迎访问！",
        "user_count": 150
        }
    )

@router.get('/login')
async def login():
    data = await firewall.login()
    return {"msg": "登录cookie获取成功","data":data}

@router.get('/tree')
async def get_tree():
    index= await firewall.get_index()
    return index

@router.get('/get_session_info')
async def get_session_info(session_info:SessionInfo = Depends()):
    msg = await firewall.get_session_info(session_info)
    if msg == '登录状态已过期':
        return {"msg": msg}
    sessions = msg["sessions"]
    filtered_sessions = await firewall.filter_session(sessions)
    if not filtered_sessions:
        return {"msg": "未查询到相关会话信息"}
    
    ip_set = {session["目标地址"] for session in filtered_sessions}
    app_ip.update(session_info.app_desc,ip_set)
    print(app_ip)

    return filtered_sessions


@router.post('/add_policy/action')
async def add_policy_action(action: PolicyAction):
    result = await firewall.add_policy_action(action)
    return result

@router.post('/capture/start')
async def start_capture():
    if not sniffer.sniffer.running:
        sniffer.start()
        return {"msg": "抓包已开启"}
    else:
        return {"msg": "抓包正在运行中"}

@router.post('/capture/stop')
async def stop_capture(req: StopCaptureReq):
    out_put_path = "results_pcap"
    os.makedirs(out_put_path, exist_ok=True)
    file_path = Path(f"./{out_put_path}/{req.output_file}.pcap")
    try:
        sniffer.stop()
    except Exception as e:
        return {"msg": f"抓包停止失败:{e}"}
    loop = asyncio.get_running_loop()
    match req.mode:
        case 'ja':
            sniffer.save_pcap(str(file_path))
            await loop.run_in_executor(executor, JaFilter().main, file_path, list(app_ip.ip), True)
        case 'ip_filter':
            sniffer.save_filtered_pcap(req.output_file, app_ip.ip)
            pass
        case 'ja_ip_filter':
            sniffer.save_filtered_pcap(req.output_file, app_ip.ip)
            sniffer.save_pcap(str(file_path))
            await loop.run_in_executor(executor, JaFilter().main, file_path, list(app_ip.ip), True)
        case _:
            sniffer.save_pcap(str(file_path))
            pass
    
    return {"msg": f"抓包已停止,保存成功[{req.output_file}]"}

@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            packet = await queue.get() 
            await manager.broadcast(str(packet))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

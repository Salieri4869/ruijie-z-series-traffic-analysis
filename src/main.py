from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from route import router
from config import get_settings
from contextlib import asynccontextmanager
from firewall import firewall

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await firewall.login()
    await firewall.get_index()
    yield
    await firewall.logout()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应更严格
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app='main:app', host='0.0.0.0', port=8000)
    pass



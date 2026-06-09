from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_URL
from src.models import Base  # 确保 src/models/__init__.py 中定义了 Base
import src.models.user  # 注册 User 模型
import src.models.task  # 注册 Task, Tag 模型
from src.api.auth import router as auth_router
from src.api.tasks import router as tasks_router

# 数据库引擎和会话
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
Base.metadata.create_all(bind=engine)

# FastAPI 实例
app = FastAPI(title="Task Manager API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由挂载（不要重复添加 prefix，因为 router 已经定义了 prefix）
app.include_router(auth_router, tags=["auth"])
app.include_router(tasks_router, tags=["tasks"])

# 根路径健康检查
@app.get("/")
def root():
    return {"message": "Task Manager API is running"}

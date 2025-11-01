"""
水文监测系统 - 主应用入口
集成了所有统一的 API 接口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入统一的 API 模块
try:
    from api import app as api_app
    # 使用导入的 API 应用作为主应用
    app = api_app
except ImportError:
    # 如果导入失败，创建基础应用
    app = FastAPI(title="Hydrology Main Server")
    
    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        return {"status": "error", "message": "统一API模块未找到"}


if __name__ == "__main__":
    import uvicorn
    import sys
    # 不使用 reload=True，避免在 Windows 中的兼容性问题
    uvicorn.run(app, host="0.0.0.0", port=3001)

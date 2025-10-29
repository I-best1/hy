"""
数据代理应用 - LangChain 版本
导入并使用统一的 API 模块
"""

import sys
import os
from pathlib import Path

# 添加父级目录到 Python 路径以导入 api 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入统一的 API 模块
try:
    from api import app as api_app
    # 使用导入的 API 应用
    app = api_app
except ImportError as e:
    # 如果导入失败，创建基础应用并给出提示
    app = FastAPI(title="Data Agent - LangChain Version")
    
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
        return {
            "status": "error",
            "message": f"统一API模块未找到: {str(e)}",
            "detail": "请确保后端目录中有 api.py 文件"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002, reload=True)

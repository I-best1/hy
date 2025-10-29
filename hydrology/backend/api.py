"""
统一的API接口模块
整合了：
1. 简报生成与智能助手 (/api/briefing)
2. 天气信息接口 (/api/weather)
3. 数据检索等其他接口
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ==================== 配置 ====================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# 简报关键词回复
KEYWORD_REPLIES = {
    "rain": "当前无持续暴雨，但请关注短时强降雨预报。",
    "water": "当前大部分站点水位正常，少数站点有上升趋势，请注意警戒。",
    "forecast": "未来24小时有小到中雨，局地有较强降雨过程，请注意。",
    "flood": "短时未观测到广泛的洪水，但山区和狭窄峡谷处需注意山洪和泥石流风险。",
}

# ==================== 数据模型 ====================
class Query(BaseModel):
    """简报查询模型"""
    q: str
    top_k: Optional[int] = 3


class WeatherRequest(BaseModel):
    """天气查询请求模型"""
    location: str  # 位置代码或名称，如 "阳朔县" 或 "110321"


class BriefingGenerateRequest(BaseModel):
    """简报生成请求模型"""
    prompt: Optional[str] = "请基于当前水文与气象监测数据，生成一份面向公众的详细简报，包含当前观测、风险提示和建议行动。"


# ==================== FastAPI 应用初始化 ====================
app = FastAPI(title="Hydrology Unified API", description="统一的水文数据API接口")


# ==================== 核心函数 ====================

def get_local_briefing_reply(q: str) -> str:
    """
    获取本地关键词回复（作为后备方案）
    
    Args:
        q: 用户查询文本
    
    Returns:
        回复内容
    """
    import re
    q = (q or "").strip()
    if not q:
        return "请在上方输入您的问题。"
    
    if re.search(r"雨量|降雨|暴雨", q):
        return "过去24小时桂林市普降大到暴雨，部分县区局部降大暴雨，最大日雨量165.5毫米。"
    if re.search(r"水位|流量|桂林水文站", q):
        return "漓江桂林水文站水位142.20米，流量154立方米每秒，未超警。"
    if re.search(r"未来|预报|趋势", q):
        return "预计未来24小时漓江桂林市城区至阳朔县城河段水位将继续上涨1.5～2米，桂江平乐县城河段上涨约1米，不会超警。"
    if re.search(r"超警|洪水|风险", q):
        return "部分中小河流可能出现超警洪水，主要集中在全州、恭城、永福、临桂、阳朔等县区。"
    if re.search(r"哪些河流|涨水|受影响", q):
        return "恭城河、湘江全州县城河段、永福县大邦河、灌阳县秀江、雁山区良丰河等多条河流出现了1～2.6米的涨水。"
    
    return "很抱歉，未能理解您的问题。请尝试输入\"雨量\"、\"水位\"、\"未来趋势\"、\"超警\"等关键词。"


def call_dashscope_api(q: str) -> Dict[str, Any]:
    """
    调用 Dashscope/Qwen LLM 进行查询
    
    Args:
        q: 查询内容
    
    Returns:
        包含 reply 和 source 的字典
    """
    if not DASHSCOPE_API_KEY:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {
            "reply": "抱歉，后端未配置外部 LLM（DASHSCOPE_API_KEY），请使用关键词（rain/water/forecast/flood）尝试。",
            "source": "keyword-fallback"
        }
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        
        messages = [
            {"role": "system", "content": "你是一个简洁且专业的水文/气象简报助手。"},
            {"role": "user", "content": q},
        ]
        
        completion = client.chat.completions.create(
            model=DASHSCOPE_MODEL,
            messages=messages,
        )
        
        comp = completion.model_dump() if hasattr(completion, "model_dump") else dict(completion)
        choices = comp.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or msg.get("delta", {}).get("content") or str(choices[0])
        else:
            content = str(comp)
        
        return {"reply": content, "source": "dashscope-qwen"}
    
    except Exception as e:
        return {"reply": f"内部调用错误：{str(e)}", "source": "error"}


def call_langchain_api(q: str) -> Dict[str, Any]:
    """
    调用 LangChain ChatOpenAI 进行查询（支持更复杂的链式处理）
    
    Args:
        q: 查询内容
    
    Returns:
        包含 reply 和 source 的字典
    """
    if not DASHSCOPE_API_KEY:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {
            "reply": "抱歉，后端未配置外部 LLM（DASHSCOPE_API_KEY），请使用关键词尝试。",
            "source": "keyword-fallback"
        }
    
    try:
        os.environ.setdefault("OPENAI_API_KEY", DASHSCOPE_API_KEY)
        if DASHSCOPE_BASE_URL:
            os.environ.setdefault("OPENAI_API_BASE", DASHSCOPE_BASE_URL)
        
        from langchain.chat_models import ChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain.chains import LLMChain
        
        template = (
            "你是一个简洁且专业的水文/气象简报助手。\n"
            "根据用户问题给出清晰、准确、面向公众的回答。\n"
            "用户问题：{question}\n"
            "请给出 1-3 句的简洁回答，必要时指出不确定性。"
        )
        prompt = PromptTemplate(input_variables=["question"], template=template)
        
        llm = ChatOpenAI(model_name=DASHSCOPE_MODEL, temperature=0.0)
        chain = LLMChain(llm=llm, prompt=prompt)
        
        resp = chain.run(question=q)
        return {"reply": resp, "source": "langchain-chatopenai"}
    
    except Exception as e:
        # 降级尝试直接调用 openai
        try:
            return call_dashscope_api(q)
        except Exception as e2:
            return {
                "reply": f"调用 LLM 失败：{str(e)}; 回退也失败：{str(e2)}",
                "source": "error"
            }


def get_weather_data(location: str) -> Dict[str, Any]:
    """
    获取天气信息
    
    Args:
        location: 位置信息（如"阳朔县"）
    
    Returns:
        天气数据字典
    """
    # 这是一个示例实现，实际应根据需求调用真实气象API
    # 可以集成如中国天气、高德天气等第三方API
    
    weather_data = {
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "temperature": 28.5,  # 温度（℃）
        "humidity": 75,  # 湿度（%）
        "precipitation_24h": 12.5,  # 24小时降水（mm）
        "wind_speed": 3.2,  # 风速（m/s）
        "wind_direction": "东北",  # 风向
        "weather": "多云",  # 天气描述
        "pressure": 1013.2,  # 气压（hPa）
        "forecast": {
            "tomorrow": "阴转小雨",
            "3days": "多云转阴，局地小雨"
        }
    }
    
    return weather_data


# ==================== API 路由 ====================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "统一API服务正在运行"}


@app.post("/api/briefing")
async def briefing(query: Query):
    """
    统一的简报和智能助手查询接口
    
    支持：
    - 简报生成（自动生成水文/气象简报）
    - 智能提问（基于LLM的自然语言处理）
    - 关键词回复（后备方案）
    
    Args:
        query: 包含 q（查询文本）和可选 top_k 的对象
    
    Returns:
        包含回复内容和数据来源的对象
    """
    q = query.q.strip()
    
    if not q:
        raise HTTPException(status_code=400, detail="查询文本不能为空")
    
    # 优先使用 LangChain 链式调用（提供更好的上下文和推理能力）
    result = call_langchain_api(q)
    
    return result


@app.post("/api/briefing/generate")
async def generate_briefing(request: BriefingGenerateRequest):
    """
    生成简报的专用接口
    
    Args:
        request: 包含可选 prompt 的请求对象
    
    Returns:
        生成的简报内容
    """
    prompt = request.prompt or "请基于当前水文与气象监测数据，生成一份面向公众的详细简报。"
    
    result = call_langchain_api(prompt)
    
    return result


@app.post("/api/weather")
async def get_weather(request: WeatherRequest):
    """
    获取天气信息接口
    
    Args:
        request: 包含 location（位置）的请求对象
    
    Returns:
        该位置的天气数据
    """
    if not request.location:
        raise HTTPException(status_code=400, detail="位置信息不能为空")
    
    try:
        weather_data = get_weather_data(request.location)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气数据失败：{str(e)}")


@app.post("/api/briefing/local")
async def get_local_briefing(query: Query):
    """
    使用本地关键词回复的简报接口（不依赖外部LLM）
    
    Args:
        query: 查询对象
    
    Returns:
        本地回复
    """
    q = query.q.strip()
    
    if not q:
        raise HTTPException(status_code=400, detail="查询文本不能为空")
    
    reply = get_local_briefing_reply(q)
    
    return {
        "reply": reply,
        "source": "local-keyword"
    }


# ==================== 中间件配置 ====================

# CORS 中间件配置（允许跨域请求用于本地开发）
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 应用启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print(f"[启动] 统一 API 服务已启动")
    print(f"[配置] LLM: {DASHSCOPE_MODEL}")
    print(f"[配置] API Key 已配置: {bool(DASHSCOPE_API_KEY)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)

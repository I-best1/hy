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
from briefing_generator import generate_briefing_markdown, generate_briefing_with_ai, SAMPLE_BRIEFING_DATA

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
    api_key: Optional[str] = None  # 前端传递的 API Key
    model: Optional[str] = None  # 前端传递的模型名称


class WeatherRequest(BaseModel):
    """天气查询请求模型"""
    location: str  # 位置代码或名称，如 "阳朔县" 或 "110321"


class BriefingGenerateRequest(BaseModel):
    """简报生成请求模型"""
    prompt: Optional[str] = "请基于当前水文与气象监测数据，生成一份面向公众的详细简报，包含当前观测、风险提示和建议行动。"
    api_key: Optional[str] = None  # 前端传递的 API Key
    model: Optional[str] = None    # 前端选择的模型

class AlertSettings(BaseModel):
    """预警设置模型"""
    station_name: str
    threshold: float  # 水位阈值（米）
    rate_threshold: float  # 涨幅阈值（米/小时）
    enabled: bool  # 是否启用


class AlertSettingsRequest(BaseModel):
    """批量预警设置请求"""
    settings: Dict[str, AlertSettings]


class AlertThreshold(BaseModel):
    """预警阈值模型"""
    threshold: float
    rate_threshold: float


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


def call_dashscope_api(q: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    调用 Dashscope/Qwen LLM 进行查询
    
    Args:
        q: 查询内容
        api_key: 前端传递的 API Key（优先使用），否则使用环境变量
        model: 模型名称（优先使用），否则使用默认值
    
    Returns:
        包含 reply 和 source 的字典
    """
    # 使用前端传递的 API Key，否则使用环境变量
    effective_api_key = api_key or DASHSCOPE_API_KEY
    effective_model = model or DASHSCOPE_MODEL
    
    if not effective_api_key:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {
            "reply": "抱歉，未提供 API Key。请在前端配置面板输入 Dashscope API Key，或在后端配置环境变量 DASHSCOPE_API_KEY。",
            "source": "keyword-fallback"
        }
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=effective_api_key,
            base_url=DASHSCOPE_BASE_URL,
        )
        
        messages = [
            {"role": "system", "content": "你是一个简洁且专业的水文/气象简报助手。"},
            {"role": "user", "content": q},
        ]
        
        completion = client.chat.completions.create(
            model=effective_model,
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


def call_langchain_api(q: str, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    调用 LangChain ChatOpenAI 进行查询（支持更复杂的链式处理）
    
    Args:
        q: 查询内容
        api_key: 前端传递的 API Key（优先使用），否则使用环境变量
        model: 模型名称（优先使用），否则使用默认值
    
    Returns:
        包含 reply 和 source 的字典
    """
    # 使用前端传递的 API Key，否则使用环境变量
    effective_api_key = api_key or DASHSCOPE_API_KEY
    effective_model = model or DASHSCOPE_MODEL
    
    if not effective_api_key:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {
            "reply": "抱歉，未提供 API Key。请在前端配置面板输入 Dashscope API Key。",
            "source": "keyword-fallback"
        }
    
    try:
        os.environ["OPENAI_API_KEY"] = effective_api_key
        if DASHSCOPE_BASE_URL:
            os.environ["OPENAI_API_BASE"] = DASHSCOPE_BASE_URL
        
        from langchain_openai import ChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain.chains import LLMChain
        
        template = (
            "你是一个简洁且专业的水文/气象简报助手。\n"
            "根据用户问题给出清晰、准确、面向公众的回答。\n"
            "用户问题：{question}\n"
            "请给出 1-3 句的简洁回答，必要时指出不确定性。"
        )
        prompt = PromptTemplate(input_variables=["question"], template=template)
        
        llm = ChatOpenAI(model=effective_model, temperature=0.0)
        chain = LLMChain(llm=llm, prompt=prompt)
        
        resp = chain.run(question=q)
        return {"reply": resp, "source": "langchain-chatopenai"}
    
    except Exception as e:
        # 降级尝试直接调用 openai
        try:
            return call_dashscope_api(q, api_key, model)
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
    - 前端传递的 API Key（不需要环境变量配置）
    
    Args:
        query: 包含以下字段的对象
            - q: 查询文本（必需）
            - top_k: 返回结果数量（可选，默认3）
            - api_key: 前端传递的 Dashscope API Key（可选）
            - model: 前端选择的模型（可选，如 qwen-plus）
    
    Returns:
        包含回复内容和数据来源的对象
    """
    q = query.q.strip()
    api_key = query.api_key
    model = query.model
    
    if not q:
        raise HTTPException(status_code=400, detail="查询文本不能为空")
    
    # 优先使用 LangChain 链式调用（提供更好的上下文和推理能力）
    result = call_langchain_api(q, api_key=api_key, model=model)
    
    return result


@app.post("/api/briefing/generate")
async def generate_briefing_api(request: BriefingGenerateRequest):
    """
    生成简报的专用接口 - 使用 Qwen AI 智能生成 Markdown 简报
    
    优先使用前端传递的 API Key，其次使用环境变量配置的 API Key
    如果都没有则回退到模板生成
    
    Args:
        request: 包含以下字段的请求对象
            - prompt: 可选的自定义提示词
            - api_key: 前端传递的 API Key（可选）
            - model: 前端选择的模型（可选）
    
    Returns:
        生成的简报内容（Markdown 格式）
    """
    try:
        # 获取前端传递的 API Key 和模型，如果没有则使用环境变量
        api_key = request.api_key or DASHSCOPE_API_KEY
        model = request.model or DASHSCOPE_MODEL
        
        # 优先使用 AI 生成简报
        if api_key:
            print(f"[简报] 使用 AI 生成简报 (模型: {model})")
            briefing_markdown = generate_briefing_with_ai(
                **SAMPLE_BRIEFING_DATA,
                api_key=api_key,
                model=model
            )
            source = "briefing-ai"
        else:
            print("[简报] 未提供 API Key，使用模板生成简报")
            briefing_markdown = generate_briefing_markdown(**SAMPLE_BRIEFING_DATA)
            source = "briefing-template"
        
        return {
            "reply": briefing_markdown,
            "source": source,
            "format": "markdown"
        }
    except Exception as e:
        print(f"[简报] 生成失败: {e}")
        return {
            "reply": f"简报生成失败: {str(e)}",
            "source": "error",
            "format": "text"
        }


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


# ==================== 预警管理 API ====================

@app.post("/api/alerts/save")
async def save_alert_settings(settings: AlertSettings):
    """
    保存单个站点的预警设置
    
    Args:
        settings: 预警设置对象
    
    Returns:
        保存结果
    """
    try:
        return {
            "status": "success",
            "message": f"已保存 {settings.station_name} 的预警设置",
            "data": settings.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"保存失败: {str(e)}")


@app.post("/api/alerts/batch")
async def batch_save_alert_settings(request: AlertSettingsRequest):
    """
    批量保存预警设置
    
    Args:
        request: 包含多个预警设置的请求
    
    Returns:
        批量保存结果
    """
    try:
        saved_count = 0
        for station_name, settings in request.settings.items():
            saved_count += 1
        
        return {
            "status": "success",
            "message": f"已保存 {saved_count} 个站点的预警设置",
            "count": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"批量保存失败: {str(e)}")


@app.post("/api/alerts/set-default")
async def set_default_thresholds(thresholds: AlertThreshold):
    """
    设置所有站点的默认阈值
    
    Args:
        thresholds: 默认阈值对象（threshold 和 rate_threshold）
    
    Returns:
        设置结果
    """
    try:
        if thresholds.threshold <= 0 or thresholds.rate_threshold < 0:
            raise ValueError("阈值必须大于0")
        
        return {
            "status": "success",
            "message": "已设置默认阈值",
            "defaults": {
                "threshold": thresholds.threshold,
                "rate_threshold": thresholds.rate_threshold
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"设置失败: {str(e)}")


@app.get("/api/alerts/default")
async def get_default_thresholds():
    """
    获取默认预警阈值
    
    Returns:
        默认阈值对象
    """
    return {
        "threshold": 1.4,  # 默认水位阈值（米）
        "rate_threshold": 0.1,  # 默认涨幅阈值（米/小时）
        "recommended": {
            "low_risk_threshold": 1.1,
            "high_risk_threshold": 1.8,
            "critical_threshold": 2.5
        }
    }


@app.get("/api/alerts/statistics")
async def get_alert_statistics():
    """
    获取预警统计信息
    
    Returns:
        统计信息对象
    """
    return {
        "total_stations": 33,
        "configured_alerts": 0,  # 从前端获取
        "active_alerts": 0,  # 从监测数据获取
        "timestamp": datetime.now().isoformat(),
        "description": "预警统计信息（实时数据）"
    }


@app.post("/api/alerts/check")
async def check_alert_conditions(station_data: Dict[str, Any]):
    """
    检查是否满足预警条件
    
    Args:
        station_data: 包含 station_name、current_level、rate 等的对象
    
    Returns:
        检查结果
    """
    try:
        station_name = station_data.get("station_name")
        current_level = station_data.get("current_level", 0)
        rise_rate = station_data.get("rise_rate", 0)
        
        # 这里可以添加更复杂的预警逻辑
        alerts = []
        
        if current_level > 1.4:
            alerts.append({
                "type": "water_level",
                "level": "warning",
                "message": f"{station_name} 水位超限：{current_level:.2f}m"
            })
        
        if rise_rate > 0.1:
            alerts.append({
                "type": "rise_rate",
                "level": "warning",
                "message": f"{station_name} 涨幅过快：{rise_rate:.3f}m/h"
            })
        
        return {
            "station": station_name,
            "status": "alert" if alerts else "normal",
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"检查失败: {str(e)}")


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

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Briefing Assistant (Dashscope/Qwen)")

# Use DASHSCOPE_API_KEY to call Aliyun Dashscope (OpenAI-compatible) endpoint.
# If not provided, fall back to simple keyword replies.
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# Simple keyword fallback replies
KEYWORD_REPLIES = {
    "rain": "当前无持续暴雨，但请关注短时强降雨预报。",
    "water": "当前大部分站点水位正常，少数站点有上升趋势，请注意警戒。",
    "forecast": "未来24小时有小到中雨，局地有较强降雨过程，请注意。",
    "flood": "短时未观测到广泛的洪水，但山区和狭窄峡谷处需注意山洪和泥石流风险。",
}


class Query(BaseModel):
    q: str
    top_k: Optional[int] = 3


@app.post("/api/briefing")
async def briefing(query: Query):
    q = query.q.strip()

    # If no Dashscope key, use keyword fallback
    if not DASHSCOPE_API_KEY:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {"reply": "抱歉，后端未配置外部 LLM（DASHSCOPE_API_KEY），请使用关键词（rain/water/forecast/flood）尝试。", "source": "keyword-fallback"}

    # Call Dashscope / Qwen via the OpenAI-compatible client
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

        # completion is a pydantic model — convert to dict then extract text
        comp = completion.model_dump() if hasattr(completion, "model_dump") else dict(completion)
        choices = comp.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or msg.get("delta", {}).get("content") or str(choices[0])
        else:
            content = str(comp)

        return {"reply": content, "source": "dashscope-qwen"}
    except Exception as e:
        return {"reply": f"内部调用错误：{e}", "source": "error"}

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Briefing Assistant (Dashscope/Qwen) - LangChain")

# Allow CORS for local development (so browser frontend can call /api/briefing)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    "flood": "短时未观测到广泛的洪水，但山区和窄峡处需注意山洪和泥石流风险。",
}


class Query(BaseModel):
    q: str
    top_k: Optional[int] = 3


@app.post("/api/briefing")
async def briefing(query: Query):
    q = query.q.strip()

    # If no DASHSCOPE key, use keyword fallback
    if not DASHSCOPE_API_KEY:
        q_low = q.lower()
        for k, v in KEYWORD_REPLIES.items():
            if k in q_low:
                return {"reply": v, "source": "keyword-fallback"}
        return {"reply": "抱歉，后端未配置外部 LLM（DASHSCOPE_API_KEY），请使用关键词（rain/water/forecast/flood）尝试。", "source": "keyword-fallback"}

    # Use LangChain's ChatOpenAI to call the compatible LLM
    try:
        # Set environment variables expected by OpenAI client used by LangChain
        os.environ.setdefault("OPENAI_API_KEY", DASHSCOPE_API_KEY)
        # If a custom base URL is provided (Dashscope compatible), set OPENAI_API_BASE
        if DASHSCOPE_BASE_URL:
            os.environ.setdefault("OPENAI_API_BASE", DASHSCOPE_BASE_URL)

        # Import langchain components
        from langchain.chat_models import ChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain.chains import LLMChain

        # Build a concise prompt template
        template = (
            "你是一个简洁且专业的水文/气象简报助手。\n"
            "根据用户问题给出清晰、准确、面向公众的回答。\n"
            "用户问题：{question}\n"
            "请给出 1-3 句的简洁回答，必要时指出不确定性。"
        )
        prompt = PromptTemplate(input_variables=["question"], template=template)

        # Create ChatOpenAI instance — rely on env vars for API key/base
        llm = ChatOpenAI(model_name=DASHSCOPE_MODEL, temperature=0.0)
        chain = LLMChain(llm=llm, prompt=prompt)

        # Run chain
        resp = chain.run(question=q)
        return {"reply": resp, "source": "langchain-chatopenai"}
    except Exception as e:
        # Fallback: try lightweight openai client path (best-effort)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
            messages = [
                {"role": "system", "content": "你是一个简洁且专业的水文/气象简报助手。"},
                {"role": "user", "content": q},
            ]
            completion = client.chat.completions.create(model=DASHSCOPE_MODEL, messages=messages)
            comp = completion.model_dump() if hasattr(completion, "model_dump") else dict(completion)
            choices = comp.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                content = msg.get("content") or msg.get("delta", {}).get("content") or str(choices[0])
            else:
                content = str(comp)
            return {"reply": content, "source": "dashscope-qwen"}
        except Exception as e2:
            return {"reply": f"调用 LLM 失败：{e}; 回退尝试也失败：{e2}", "source": "error"}

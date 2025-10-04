Backend split: dataagent (Python) and nodeagent (Node.js)

dataagent/
- app.py          # FastAPI service that implements /api/briefing
- requirements.txt
- run.ps1         # PowerShell runner (creates venv and runs uvicorn)

nodeagent/
- index.js        # Simple Express-based briefing mock
- package.json
- run.ps1         # PowerShell runner (npm install && npm start)

Start (PowerShell):
- Dataagent: cd backend/dataagent; .\\run.ps1
- Nodeagent: cd backend/nodeagent; .\\run.ps1
# 简报助手（FastAPI + Dashscope/Qwen 优先）

该后端为水文演示提供一个轻量级的简报助手。

实现说明：

- `index.js` (Node.js/Express) — 原始的简单关键词匹配示例（保留以供参考）。
- `app.py` (FastAPI) — Python 实现：优先使用阿里 Dashscope 的 OpenAI 兼容接口（Qwen 模型）。当环境变量 `DASHSCOPE_API_KEY` 被设置时，后端会调用 Dashscope（兼容 OpenAI API）；若未设置则回退为简单关键词回复。

## 快速开始（Windows PowerShell）

1) 创建并激活虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) 推荐：只安装启动所需的精简依赖（如果你只打算使用 Dashscope，不需要安装大型本地模型依赖）

```powershell
pip install fastapi uvicorn python-dotenv openai requests
```

如果你需要 repo 中的 `requirements.txt`（包含 transformers/torch/faiss 等本地推理依赖），也可以直接：

```powershell
pip install -r requirements.txt
```

3) 设置 Dashscope（阿里）API Key

```powershell
setx DASHSCOPE_API_KEY "sk-..."
# 对当前会话临时设置可以使用： $env:DASHSCOPE_API_KEY = 'sk-...'
```

如果你使用的是非默认兼容域名或想指定模型，可以同时设置：

```powershell
setx DASHSCOPE_BASE_URL "https://dashscope.aliyuncs.com/compatible-mode/v1"
setx DASHSCOPE_MODEL "qwen-plus"
```

4) 启动 FastAPI 服务

```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

服务地址： `http://localhost:3001/api/briefing`

## 测试 API（PowerShell）

示例：用 PowerShell 的 `Invoke-RestMethod` 发送 POST 请求：

```powershell
$body = @{ q = '今天会下雨吗？' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:3001/api/briefing -Method Post -Body $body -ContentType 'application/json'
```

或者用 curl（PowerShell）:

```powershell
curl -X POST "http://localhost:3001/api/briefing" -H "Content-Type: application/json" -d '{"q":"水位有异常吗？"}'
```

## 示例：直接使用 Dashscope 客户端（Python）

若你想在本地测试如何直接调用 Dashscope（OpenAI 兼容），下面是一个与仓库 `app.py` 相同风格的示例脚本：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    base_url=os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
)

completion = client.chat.completions.create(
    model=os.getenv('DASHSCOPE_MODEL', 'qwen-plus'),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你是谁？"},
    ],
)

print(completion.model_dump_json())
```

## API 说明

POST /api/briefing
- 请求 JSON: {"q": "你的问题文本", "top_k": 3}
- 响应 JSON: {"reply": "回答文本", "source": "dashscope-qwen" | "keyword-fallback" | "error"}

## 兼容与扩展建议

- 如果后端未配置 `DASHSCOPE_API_KEY`，`app.py` 会回退到关键词回复（rain/water/forecast/flood）。
- 如果你希望使用本地模型（transformers）进行推理，请告诉我目标模型名称（如 `internlm`, `llama` 家族或其他），我可以把 `app.py` 扩展为在没有外部 Key 时加载本地模型。
- 我保留了原始 Node.js 示例 (`index.js`) 以供参考。


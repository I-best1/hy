"""
洪水预警简报生成模块
支持 Markdown 格式的完整简报生成
可调用 Qwen AI 进行智能生成
"""

from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_current_time_cn():
    """获取中文格式的当前时间"""
    now = datetime.now()
    return now.strftime("%Y年%m月%d日 %H:%M")


def generate_briefing_markdown(
    water_stations: list = None,
    rainfall_data: dict = None,
    alerts: list = None,
    weather_info: str = None
) -> str:
    """
    生成标准格式的 Markdown 洪水预警简报
    
    参数:
    - water_stations: 水文站点列表，每个站点包含 name, level, status, address
    - rainfall_data: 降雨数据字典，包含 {station_name: rainfall_24h}
    - alerts: 预警列表，每个预警包含 type, level, description
    - weather_info: 气象预报文本
    
    返回:
    - Markdown 格式的简报文本
    """
    
    current_time = get_current_time_cn()
    
    # 组织简报标题
    briefing = f"""**阳朔洪水预警简报**
**发布日期：{current_time}**
**发布单位：阳朔县水文局**

---

### 一、当前观测情况

"""
    
    # 添加水文站点信息
    if water_stations:
        briefing += "#### 水文站点监测\n\n"
        for station in water_stations:
            name = station.get('name', '未知站点')
            level = station.get('level', 0)
            status = station.get('status', '正常')
            address = station.get('address', '阳朔县')
            briefing += f"- **{name}** ({address}): 水位 {level} m，状态 {status}\n"
        briefing += "\n"
    
    # 添加降雨数据
    if rainfall_data:
        briefing += "#### 降雨观测\n\n"
        for station_name, rainfall_24h in rainfall_data.items():
            briefing += f"- **{station_name}**: 24小时累计降雨 {rainfall_24h} mm\n"
        briefing += "\n"
    
    briefing += """---

### 二、风险提示

"""
    
    # 添加风险提示
    if alerts and len(alerts) > 0:
        for idx, alert in enumerate(alerts, 1):
            alert_type = alert.get('type', '通用')
            alert_level = alert.get('level', '未定级')
            description = alert.get('description', '')
            briefing += f"{idx}. **{alert_type}风险（{alert_level}）**\n{description}\n\n"
    else:
        # 默认风险提示
        briefing += """1. **暴雨洪涝风险（高等级）**
未来三天，华南仍有持续性强降雨，累计雨量可达100～200毫米，局地超300毫米。山洪、中小河流洪水、城乡内涝和地质灾害风险极高，尤其粤北、闽西南山区需高度警惕。

2. **高温中暑风险（中等级）**
华北、黄淮等地高温天气持续，紫外线强，户外活动易引发中暑，老年人、儿童及慢性病患者应减少外出。

3. **次生灾害风险**
强降雨可能导致山体滑坡、泥石流，特别是在地形复杂、前期土壤饱和区域，请避免前往山区、河道、地质灾害隐患点。

4. **交通安全风险**
雨天道路湿滑，能见度降低，高速公路、城市主干道易发生拥堵或事故；地铁站、地下车库注意防范倒灌。

"""
    
    briefing += """---

### 三、建议行动

#### 公众应对措施：

- **居住在低洼地带、河边、山脚的居民**：密切关注水情预警，提前准备应急包（含食物、饮用水、药品、手电筒等），必要时听从政府安排及时转移。

- **出行人员**：尽量避免涉水行车，切勿强行通过积水路段；如遇车辆熄火，应立即弃车逃生。

- **户外工作者**：高温时段（11:00–15:00）暂停露天作业，做好防暑降温措施，及时补水补盐。

- **学生与家长**：雷雨期间避免户外活动，关注学校停课通知，确保上下学安全。

- **居家防范**：检查排水管道，清理阳台杂物，防止高空坠物；关闭门窗，防止雨水倒灌。

#### 特别提醒：

- 请通过官方渠道（如"中国气象局"、"水利部水情信息网"、地方应急广播）获取最新预警信息，不信谣、不传谣。

- 如遇紧急情况，请立即拨打当地应急电话（如110、119、12350）求助。

---

**后续展望**：
"""
    
    if weather_info:
        briefing += f"{weather_info}\n\n"
    else:
        briefing += """预计未来24小时内，高压系统将带来短暂晴朗天气，但新一轮冷空气将在今晚进入，伴有大风降温。请相关部门做好防御工作，公众提高警惕。

"""
    
    briefing += """
---

**生命至上，安全第一。科学防范，共度汛期。**
—— 阳朔县水文局 敬告
"""
    
    return briefing


def markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 转换为 HTML 用于前端渲染
    """
    try:
        import markdown
        html = markdown.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'toc'],
            extension_configs={
                'markdown.extensions.codehilite': {
                    'css_class': 'highlight'
                }
            }
        )
        return html
    except ImportError:
        # 如果未安装 markdown，返回原始文本并进行基本格式化
        return f"<pre>{markdown_text}</pre>"


def extract_briefing_data(system_data: dict) -> dict:
    """
    从系统数据中提取简报所需的信息
    
    参数:
    - system_data: 系统监测数据
    
    返回:
    - 简报所需的数据字典
    """
    
    water_stations = []
    rainfall_data = {}
    alerts = []
    
    # 提取水文站点数据
    if 'stations' in system_data:
        for station in system_data['stations']:
            water_stations.append({
                'name': station.get('name', ''),
                'level': station.get('level', 0),
                'status': station.get('status', '正常'),
                'address': station.get('address', '阳朔县')
            })
    
    # 提取降雨数据
    if 'rainfall' in system_data:
        rainfall_data = system_data['rainfall']
    
    # 提取预警数据
    if 'alerts' in system_data:
        alerts = system_data['alerts']
    
    return {
        'water_stations': water_stations,
        'rainfall_data': rainfall_data,
        'alerts': alerts,
        'weather_info': system_data.get('weather_info', '')
    }


# ==================== AI 简报生成 ====================

def call_qwen_api_direct(prompt: str, api_key: str, model: str, base_url: str) -> str:
    """
    直接调用 Qwen API（使用 OpenAI 兼容接口）
    
    参数:
    - prompt: 提示词
    - api_key: API Key
    - model: 模型名称
    - base_url: API 基础 URL
    
    返回:
    - AI 生成的文本
    """
    try:
        # 方案 1: 使用 openai 库
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位专业的水文气象简报专家，需要生成面向公众的洪水预警简报。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                timeout=30
            )
            
            briefing = response.choices[0].message.content
            print(f"[简报] OpenAI 客户端调用成功")
            return briefing
            
        except Exception as e:
            print(f"[简报] OpenAI 客户端失败: {e}，尝试 requests 库...")
            
            # 方案 2: 使用 requests 库
            import requests
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一位专业的水文气象简报专家。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(
                f"{base_url}/chat/completions", 
                json=payload, 
                headers=headers, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                briefing = data['choices'][0]['message']['content']
                print(f"[简报] Requests 调用成功")
                return briefing
            else:
                raise Exception(f"API 返回错误 {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"[简报] 直接 API 调用失败: {e}")
        raise


def generate_briefing_with_ai(
    water_stations: list = None,
    rainfall_data: dict = None,
    alerts: list = None,
    weather_info: str = None,
    api_key: str = None,
    model: str = None
) -> str:
    """
    使用 Qwen AI 智能生成简报
    
    参数:
    - water_stations: 水文站点数据
    - rainfall_data: 降雨数据
    - alerts: 预警数据
    - weather_info: 气象信息
    - api_key: Dashscope API Key
    - model: 模型名称（qwen-plus, qwen-turbo, qwen-max）
    
    返回:
    - AI 生成的 Markdown 简报
    """
    
    # 构建数据上下文
    current_time = get_current_time_cn()
    context = f"当前时间：{current_time}\n\n"
    context += "根据以下水文气象数据，生成一份专业的洪水预警简报（Markdown 格式）：\n\n"
    
    if water_stations:
        context += "**当前水文观测**\n"
        for station in water_stations:
            name = station.get('name', '')
            level = station.get('level', 0)
            status = station.get('status', '正常')
            address = station.get('address', '')
            context += f"- {name} ({address}): 水位 {level} m，状态 {status}\n"
        context += "\n"
    
    if rainfall_data:
        context += "**24小时降雨观测**\n"
        for location, rainfall in rainfall_data.items():
            context += f"- {location}: {rainfall} mm\n"
        context += "\n"
    
    if alerts:
        context += "**预警信息**\n"
        for alert in alerts:
            alert_type = alert.get('type', '')
            alert_level = alert.get('level', '')
            description = alert.get('description', '')
            context += f"- {alert_type} ({alert_level}): {description}\n"
        context += "\n"
    
    if weather_info:
        context += f"**气象预报**: {weather_info}\n\n"
    
    # 生成提示词
    prompt = context + f"""
请基于上述数据和当前时间（{current_time}）生成一份完整的洪水预警简报，要求：

1. **标题部分**
   - 标题：**阳朔洪水预警简报**
   - 发布日期：{current_time}
   - 发布单位：阳朔县水文局

2. **内容结构**
   - 一、当前观测情况（包含上述水文站点和降雨数据）
   - 二、风险提示（分析预警等级，说明风险）
   - 三、建议行动（针对不同人群的应对措施）
   - 后续展望

3. **格式要求**
   - 使用 Markdown 格式
   - 使用加粗、列表等格式突出重点
   - 准确、专业、面向公众

4. **内容质量**
   - 信息准确、措辞严谨
   - 包含具体的数据和建议
   - 简明扼要但内容完整

请直接生成简报内容，不需要其他说明。"""
    
    try:
        # 获取有效的 API Key 和模型
        effective_api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        effective_model = model or os.getenv("DASHSCOPE_MODEL", "qwen-plus")
        base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        if not effective_api_key:
            # 如果没有 API Key，回退到模板生成
            print("[简报] 无 API Key，使用模板生成")
            return generate_briefing_markdown(
                water_stations=water_stations,
                rainfall_data=rainfall_data,
                alerts=alerts,
                weather_info=weather_info
            )
        
        print(f"[简报] 开始 AI 调用 (模型: {effective_model})")
        
        # 直接调用 Qwen API（使用新的直接调用函数）
        briefing = call_qwen_api_direct(prompt, effective_api_key, effective_model, base_url)
        print(f"[简报] AI 生成成功，长度: {len(briefing)} 字符")
        return briefing
        
    except Exception as e:
        print(f"[简报] AI 生成失败: {e}，使用模板生成")
        return generate_briefing_markdown(
            water_stations=water_stations,
            rainfall_data=rainfall_data,
            alerts=alerts,
            weather_info=weather_info
        )


# ==================== 示例数据 ====================

SAMPLE_BRIEFING_DATA = {
    'water_stations': [
        {'name': '阳朔县水文站', 'level': 142.50, 'status': '上升', 'address': '阳朔县城'},
        {'name': '桂林水文站', 'level': 142.20, 'status': '正常', 'address': '桂林市区'},
        {'name': '平乐县水文站', 'level': 138.80, 'status': '上升', 'address': '平乐县城'}
    ],
    'rainfall_data': {
        '阳朔县': 85.5,
        '桂林市': 92.3,
        '平乐县': 76.8
    },
    'alerts': [
        {
            'type': '暴雨洪涝',
            'level': '高等级',
            'description': '未来三天，华南仍有持续性强降雨，累计雨量可达100～200毫米，局地超300毫米。山洪、中小河流洪水、城乡内涝和地质灾害风险极高。'
        },
        {
            'type': '山洪地质灾害',
            'level': '中等级',
            'description': '山体滑坡、泥石流风险增加，尤其在地形复杂、前期土壤饱和区域。'
        }
    ],
    'weather_info': '预计未来24小时内仍有大到暴雨，请做好防御工作。'
}


if __name__ == '__main__':
    # 测试简报生成
    briefing = generate_briefing_markdown(**SAMPLE_BRIEFING_DATA)
    print(briefing)
    print("\n" + "="*50 + "\n")
    print("HTML 版本:")
    print(markdown_to_html(briefing)[:500] + "...")

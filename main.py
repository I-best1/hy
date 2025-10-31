from fastapi import FastAPI
from pydantic import BaseModel
import torch
import numpy as np
import joblib
from model_definition import Net

# 初始化FastAPI应用
app = FastAPI(title="水位预测API")

# 定义输入数据模型
class PredictionRequest(BaseModel):
    # 输入为3天的5个特征值，每个特征是一个包含5个元素的列表
    features: list[list[float]] = [
        [0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0]
    ]

# 模型配置参数（与训练时保持一致）
input_size = 5
hidden_size = 32
num_layers = 2
dropout_rate = 0.3

# 初始化设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 加载模型
model = Net(input_size=input_size, hidden_size=hidden_size, 
            num_layers=num_layers, dropout=dropout_rate)
state_dict = torch.load('./product/best_lstm_model.pth', map_location=device)
model.load_state_dict(state_dict)
model.to(device)
model.eval()  # 开启评估模式

# 加载数据标准化器
scaler_features = joblib.load('./product/scaler_features.pkl')
scaler_target = joblib.load('./product/scaler_target.pkl')

# 定义预测接口
@app.post("/predict", summary="预测水位值")
def predict(request: PredictionRequest):
    try:
        # 验证输入数据格式是否正确（3天，每天5个特征）
        if len(request.features) != 3:
            return {"error": "输入必须包含3天的特征数据"}
        for day_features in request.features:
            if len(day_features) != 5:
                return {"error": "每天的特征必须包含5个数值"}
        
        # 数据处理与预测
        features_array = np.array(request.features).reshape(-1, 5)
        features_scaled = scaler_features.transform(features_array)
        input_tensor = torch.tensor(features_scaled, dtype=torch.float32).unsqueeze(0).to(device)
        
        with torch.no_grad():
            prediction_scaled = model(input_tensor)
        
        # 反标准化并返回结果
        prediction = scaler_target.inverse_transform(
            prediction_scaled.cpu().numpy().reshape(-1, 1)
        )
        
        return {
            "predicted_water_level": round(prediction.item(), 2),
            "message": "预测成功"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Start the FastAPI server
    # The reload option is removed for production use
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
    #http://127.0.0.1:8000/docs
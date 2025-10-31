import torch
import numpy as np
import joblib
from model_definition import Net # 从model_definition中导入Net

input_size = 5
hidden_size = 32
num_layers = 2
dropout_rate = 0.3

model = Net(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers, dropout=dropout_rate)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 加载模型
state_dict = torch.load('./product/best_lstm_model.pth', map_location=device)
model.load_state_dict(state_dict)

# 加载数据标准化器
scaler_features = joblib.load('./product/scaler_features.pkl')
scaler_target = joblib.load('./product/scaler_target.pkl')

# 开启测试模式
model.eval()

def predict(features_input):
    # 将输入转换为numpy数组并重塑
    features_array = np.array(features_input).reshape(-1, 5)

    # 使用相同的标准化器进行标准化
    features_scaled = scaler_features.transform(features_array)

    # 转换为PyTorch张量并调整形状为(1, 5, 3) <--> (样本数, 时间步长, 特征数)
    input_tensor = torch.tensor(features_scaled, dtype=torch.float32).unsqueeze(0)

    # 进行预测
    with torch.no_grad():
        prediction_scaled = model(input_tensor)

    # 将预测结果反标准化到原始尺度
    prediction = scaler_target.inverse_transform(
        prediction_scaled.numpy().reshape(-1, 1)
    )

    return prediction.item()


# 示例使用
if __name__ == "__main__":
    # 输入数据（需要过去3天的五个特征值）
    # 阳朔11点的水位, 阳朔11点的流量, 阳朔日均流量，桂林日均流量，潮田日均流量
    example_input = [
        [104.42, 193, 186, 238, 12.8],  # 第1天
        [105.49, 568, 424, 343, 9.28],  # 第2天
        [104.75, 288, 292, 171, 7.93],  # 第3天
    ] # 正确值：104.56

    # example_input = [
    #     [107.42, 1660, 1620, 1180, 39.6],  # 第1天
    #     [106.79, 1250, 1240, 784, 31.6],  # 第2天
    #     [105.78, 700, 767, 484, 26.9],  # 第3天
    # ]  # 正确值：105.84

    # example_input = [
    #     [103.93, 84.9, 85.7, 33.6, 5.34],  # 第1天
    #     [103.91, 81.1, 80.3, 33.9, 5.39],  # 第2天
    #     [103.9, 79.2, 79.3, 38.7, 5.98],  # 第3天
    # ]  # 正确值：104

    predicted_value = predict(example_input)
    print(f"预测的yangshuo_flow值为: {predicted_value:.2f}")

import torch
from torch import nn


class Net(nn.Module):
    def __init__(self, input_size=5, hidden_size=32, num_layers=2, output_size=1, dropout=0.2):
        super(Net, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM层
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=dropout)

        # 全连接层
        self.linear = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # 初始隐藏状态和细胞状态
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        # LSTM前向传播
        lstm_out, _ = self.lstm(x, (h0, c0))

        # 取最后一个时间步的输出
        out = self.linear(lstm_out[:, -1, :])
        return out

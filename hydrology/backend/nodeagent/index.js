const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const port = process.env.PORT || 3001;

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// 简单的本地问答逻辑（可替换为更智能的模型或调用外部 API）
app.post('/api/briefing', (req, res) => {
  const q = (req.body.q || '').toString().trim();
  if(!q) return res.json({ ok: false, reply: '请提供问题文本（字段 q）。' });

  // 简单关键词匹配(本地演示)
  const lower = q.toLowerCase();
  if(/雨量|降雨|暴雨/.test(lower)) return res.json({ ok: true, reply: '过去24小时桂林市普降大到暴雨，部分县区局部降大暴雨，最大日雨量165.5毫米。' });
  if(/水位|流量|桂林水文站/.test(lower)) return res.json({ ok: true, reply: '漓江桂林水文站水位142.20米，流量154立方米每秒，未超警。' });
  if(/未来|预报|趋势/.test(lower)) return res.json({ ok: true, reply: '预计未来24小时漓江桂林市城区至阳朔县城河段水位将继续上涨1.5～2米，桂江平乐县城河段上涨约1米，不会超警。' });
  if(/超警|洪水|风险/.test(lower)) return res.json({ ok: true, reply: '部分中小河流可能出现超警洪水，主要集中在全州、恭城、永福、临桂、阳朔等县区。' });
  return res.json({ ok: true, reply: '抱歉，我暂时无法回答该问题。请尝试“雨量”、“水位”、“未来趋势”等关键词。' });
});

app.listen(port, ()=>{ console.log(`Hydrology agent backend listening on http://localhost:${port}`); });

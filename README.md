阳朔县洪水检测大屏管理系统 - 简易演示

说明

- 将附件中的地图图片放到 `assets/map.jpg`。如果没有图片，页面会显示空背景。
- 直接在浏览器中打开 `index.html` 即可查看演示大屏。页面使用 ECharts CDN 渲染折线图。

文件

- `index.html` - 大屏主页面，包含地图占位、站点列表、折线图等。
- `assets/README.txt` - 说明地图图片放置位置。

部署

- 本地打开：双击 `index.html` 或在浏览器中打开路径。
- 建议使用静态服务器：例如在 PowerShell 中运行 `python -m http.server 8000`（需 Python 环境），然后访问 `http://localhost:8000/`。

后续

- 可以替换地图为真实的矢量地图（GeoJSON）并用 ECharts 的地图或第三方地图 SDK 渲染。
- 可把数据接口改为真实的水文气象后台 API。

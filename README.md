# 光伏新能源工作台（GitHub Pages 版）

个人用的光伏新能源信息工作台：广东电价看板（含代理购电价/现货/绿电参考）、
分布式收益测算器、辐照预报、每日行业资讯（含招投标）、产业链价格及走势图、政策跟踪。
页面为纯静态 `index.html`（无外部 JS/CSS 依赖），数据在 `data.json`，
由 GitHub Actions 每天早上自动更新；另有 `history.json` 记录价格历史供走势图使用。

上线后的访问地址：`https://363826786-sys.github.io/pv-workbench/`

## 文件说明

| 文件 | 说明 |
|---|---|
| `index.html` | 工作台页面（单文件、纯 CSS、无外部图片），打开时读取同目录 `data.json` / `history.json` 渲染；辐照预报直接调用 Open-Meteo 免费接口 |
| `data.json` | 工作台数据：更新时间、一句话导读、电价、资讯、产业链价格、政策 |
| `history.json` | 产业链代表规格价格快照历史（每天追加、无变化不记），供走势图使用 |
| `update.py` | 每日更新脚本：拉 RSS → 写 `data.json`；价格快照追加到 `history.json` |
| `requirements.txt` | Python 依赖（`feedparser`） |
| `.github/workflows/daily.yml` | 定时任务：北京时间每天 08:50 运行更新脚本并提交 `data.json` / `history.json` |

## 上线步骤

1. 在 GitHub 新建仓库，仓库名填 **`pv-workbench`**（公开 Public）
2. 把本目录所有文件上传到仓库根目录（`index.html`、`data.json` 必须在根目录）
3. 进入仓库 **Settings → Pages**：
   - Source 选择 **Deploy from a branch**
   - Branch 选择 **main**，目录选择 **/ (root)**，点 Save
   - 等 1–2 分钟，访问 `https://363826786-sys.github.io/pv-workbench/` 即可看到工作台
4. 进入仓库 **Actions** 标签页，确认 `每日更新工作台数据` 工作流已启用
   - 它会在北京时间每天 08:50 自动运行；也可以点 **Run workflow** 手动触发一次验证

## 配置：RSS 源与分类关键词（`update.py` 顶部配置区）

```python
FEEDS = [
    ("光伏", "gnews", "光伏"),
    ("光伏", "gnews", "光伏們"),      # 光伏們公众号文章（经转载被 Google News 收录）
    ("光伏", "gnews", "索比光伏网"),  # 索比光伏网文章（经转载被 Google News 收录）
    ("储能", "gnews", "储能"),
    ("新能源", "gnews", "新能源 -汽车"),
    ("AI", "gnews", "AI 大模型"),
    ("AI", "rss", "https://www.qbitai.com/feed"),  # 量子位
    ("招投标", "gnews", "光伏 招标"),
    ("招投标", "gnews", "光伏 中标"),
    ("招投标", "gnews", "储能 招标"),
]
```

- 类型 `gnews`：填 Google News 搜索关键词，程序自动拼成 RSS 地址
- 类型 `rss`：直接填 RSS/Atom 地址
- `MAX_PER_CATEGORY`：每类最多保留条数（默认 10）
- `HOURS`：只收录最近 N 小时的资讯（默认 48）

> 当前接入的源（2026-10-10 逐个实际请求验证可用）：
> Google News RSS（光伏 / 光伏們 / 索比光伏网 / 储能 / 新能源 / AI 大模型 / 招投标三个搜索源）、量子位 `https://www.qbitai.com/feed`
>
> 曾尝试但**不可用**（无有效 RSS 或已失效，未接入）：北极星太阳能光伏网、北极星储能网、
> OFweek 太阳能光伏网、机器之心、36氪、虎嗅、新浪科技滚动 RSS；索比光伏网官网无原生 RSS，
> 改用 Google News 关键词源接入。微信公众号无官方 RSS，RSSHub 公共实例不可达，
> 光伏們/索比光伏网改用 Google News 关键词源接入；数据中心世界网暂未找到可用 feed（见下）。
>
> **数据中心世界网**：未能接入。微信文章页有反爬无法直接读取其公众号标识；
> 未找到该号对应的官网或可用 RSS。如需接入，请提供该公众号的微信号（如 gh_xxx）
> 或其官网地址，即可按上面格式加到 `FEEDS`。

## 手动维护事项

以下数据**不会**被脚本自动更新，变化时请手动改：

1. **电价**（`update.py` 顶部 `ELECTRICITY`）：峰谷分时政策、余电上网/机制电价都是政策性静态配置。
   广东分时电价或 136 号文等政策有变时，改这里，下次定时任务会自动写入 `data.json`。
   - **代理购电价**：广东电网**每月初**发布新价表，每月初手动更新 `ELECTRICITY["agency"]` 的说明文字。
2. **产业链价格**（`data.json` 的 `supply_chain`）：暂无稳定公开的机器可读来源，
   脚本每次原样保留旧值和原报价日期，**不编造新价格**。
   建议**每周**对照 InfoLink / 硅业分会周报手动更新 `data.json` 后提交；
   下一次定时任务会自动把新值追加进 `history.json` 形成走势。
3. **政策跟踪**（`data.json` 的 `policies`）：新增政策手动追加一条即可（标题+一句话解读+链接+日期）。

## 页面功能说明

- **深色模式**：右上角按钮切换，偏好保存在浏览器 localStorage，默认跟随系统。
- **资讯搜索+分类**：搜索框按标题/摘要过滤，tab 按 光伏/储能/新能源/AI/招投标 筛选。
- **收益测算器**：纯前端实时计算，默认值为广东示例值；页面明确标注"简化估算，仅供参考"。
- **辐照预报**：页面打开时直接调用 Open-Meteo 免费接口（已验证返回 `Access-Control-Allow-Origin: *`，
  GitHub Pages 可跨域调用），展示广州/深圳/佛山未来 7 天水平面总辐照（kWh/㎡/天）。
- **价格走势图**：原生 SVG 手绘（无外部图表库），以首次记录为 100 的价格指数展示
  组件/硅片/电池片/硅料涨跌；历史不足 2 期时显示"积累中"提示。

## 本地测试

```bash
pip install -r requirements.txt
python update.py   # 会更新本地 data.json，可先备份
# 然后用浏览器打开 index.html 预览（需用本地服务器，如 python -m http.server，
# 直接双击打开时 fetch data.json 可能被浏览器拦截）
```

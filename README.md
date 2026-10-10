# 光伏新能源工作台（GitHub Pages 版）

个人用的光伏新能源信息工作台：广东电价看板、每日行业资讯、产业链价格、政策跟踪。
页面为纯静态 `index.html`，数据在 `data.json`，由 GitHub Actions 每天早上自动更新。

上线后的访问地址：`https://363826786-sys.github.io/pv-workbench/`

## 文件说明

| 文件 | 说明 |
|---|---|
| `index.html` | 工作台页面（单文件、纯 CSS、无外部图片），打开时读取同目录 `data.json` 渲染 |
| `data.json` | 工作台数据：更新时间、一句话导读、电价、资讯、产业链价格、政策 |
| `update.py` | 每日更新脚本：拉 RSS → 写 `data.json` |
| `requirements.txt` | Python 依赖（`feedparser`） |
| `.github/workflows/daily.yml` | 定时任务：北京时间每天 08:50 运行更新脚本并提交 |

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
    ("储能", "gnews", "储能"),
    ("新能源", "gnews", "新能源 -汽车"),
    ("AI", "gnews", "AI 大模型"),
    ("AI", "rss", "https://www.qbitai.com/feed"),  # 量子位
]
```

- 类型 `gnews`：填 Google News 搜索关键词，程序自动拼成 RSS 地址
- 类型 `rss`：直接填 RSS/Atom 地址
- `MAX_PER_CATEGORY`：每类最多保留条数（默认 10）
- `HOURS`：只收录最近 N 小时的资讯（默认 48）

> 当前接入的源（2026-10-10 逐个实际请求验证可用）：
> Google News RSS（光伏 / 储能 / 新能源 / AI 大模型四个搜索源）、量子位 `https://www.qbitai.com/feed`
>
> 曾尝试但**不可用**（无有效 RSS 或已失效，未接入）：北极星太阳能光伏网、北极星储能网、
> 索比光伏网、OFweek 太阳能光伏网、机器之心、36氪、虎嗅、新浪科技滚动 RSS。
> 如找到新的可用行业媒体 RSS，按上面格式加到 `FEEDS` 即可（建议先在本地跑 `python update.py` 验证）。

## 手动维护事项

以下数据**不会**被脚本自动更新，变化时请手动改：

1. **电价**（`update.py` 顶部 `ELECTRICITY`）：峰谷分时政策、余电上网/机制电价都是政策性静态配置。
   广东分时电价或 136 号文等政策有变时，改这里，下次定时任务会自动写入 `data.json`。
2. **产业链价格**（`data.json` 的 `supply_chain`）：暂无稳定公开的机器可读来源，
   脚本每次原样保留旧值和原报价日期，**不编造新价格**。
   建议每周对照 InfoLink / 硅业分会周报手动更新 `data.json` 后提交。
3. **政策跟踪**（`data.json` 的 `policies`）：新增政策手动追加一条即可（标题+一句话解读+链接+日期）。

## 本地测试

```bash
pip install -r requirements.txt
python update.py   # 会更新本地 data.json，可先备份
# 然后用浏览器打开 index.html 预览（需用本地服务器，如 python -m http.server，
# 直接双击打开时 fetch data.json 可能被浏览器拦截）
```

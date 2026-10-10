#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光伏新能源工作台 - 每日数据更新脚本（GitHub Actions 调用）。

工作方式：
1. 从下方【配置区】的 RSS 源拉取近 48 小时资讯，按分类写入 data.json 的 news；
   Bing 新闻 RSS 自带发布者原文直链（国内可直接打开），无需翻墙；
2. electricity（电价）为政策性静态配置，原样保留 —— 电价政策变化时手动修改下方 ELECTRICITY；
3. supply_chain（产业链价格）暂无稳定公开的机器可读来源，原样保留旧值和原报价日期，
   不编造新价格 —— 每周对照 InfoLink / 硅业分会报价手动更新 data.json；
   每次运行会把代表规格的价格快照追加到 history.json（无变化则不追加），供页面画走势图；
4. policies（政策跟踪）原样保留，新增政策手动追加到 data.json。
"""

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser

feedparser.USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
HISTORY_FILE = BASE_DIR / "history.json"
BEIJING = timezone(timedelta(hours=8))

# ==================== 配置区（用户可改） ====================
# 每项：(分类, 类型, 内容)
#   类型 "bing"：内容为 Bing 新闻搜索关键词（程序自动拼成 RSS 地址）
#   Bing RSS 自带发布者原文直链（国内可直接打开），无需翻墙
#   类型 "rss"  ：内容为直接可用的 RSS/Atom 地址
# 下面的源已逐个实际请求验证可用；新增前请先本地跑一遍验证。
FEEDS = [
    ("光伏", "bing", "光伏"),
    ("光伏", "bing", "光伏們"),      # 光伏們公众号文章（经转载被 Google News 收录，已验证 48h 内有更新）
    ("光伏", "bing", "索比光伏网"),  # 索比光伏网文章（经转载被 Google News 收录，已验证有近 48h 更新）
    ("储能", "bing", "储能"),
    ("新能源", "bing", "新能源 -汽车"),
    ("AI", "bing", "AI 大模型"),
    ("AI", "rss", "https://www.qbitai.com/feed"),
    ("招投标", "bing", "光伏 招标"),
    ("招投标", "bing", "光伏 中标"),
    ("招投标", "bing", "储能 招标"),
]

MAX_PER_CATEGORY = 10
HOURS = 48
HISTORY_MAX = 104  # 价格快照最多保留约 2 年
# ============================================================

# 电价静态配置：政策性内容，变化时手动改这里（脚本每次原样写入 data.json）
ELECTRICITY = {
    "tou": {
        "ratio": "1.7 : 1 : 0.38",
        "peak": "10:00-12:00、14:00-19:00（共7小时）",
        "valley": "1:00-8:00、12:00-13:00（新增午间低谷）",
        "flat_note": "其余时段为平段；平段电价基准取代理购电价格",
        "note": "网传2026年优化征求意见稿口径，以正式文件为准",
        "spread": "2026年9月：珠三角六市最大峰谷价差1.3963元/kWh，全国最高；"
                  "惠州1.3134、东西两翼1.2103、粤北1.1550，四大片区全部突破1.15",
        "example": "2026年4月汕头代理购电价表示例（工商业单一制1-10kV，含税）："
                   "尖峰1.3950 / 高峰1.1215 / 平段0.6711 / 低谷0.2721 元/kWh",
    },
    "feedin": {
        "existing": "0.453元/kWh（存量项目机制电价＝广东燃煤基准价，136号文广东细则，全国最高一档）",
        "new_cap": "0.4元/kWh（增量项目竞价上限；海上风电竞价上限为燃煤基准价）",
        "spot_ref": "新能源现货结算均价约0.27元/kWh（2026年上半年，广东电力交易中心；显著低于煤电0.3892）",
        "midlong_ref": "中长期市场均价0.3784元/kWh（2026年上半年）",
        "green_ref": "绿电环境价值均价0.0182元/kWh（其中光伏0.0173）",
    },
    "agency": {
        "title": "代理购电价（月度）",
        "note": "广东电网每月初发布代理购电价表，工商业用户电价随每月代理购电价格浮动；"
                "具体数值见广东电网当月公告（示例：2026年4月汕头市电价表）",
        "update_note": "每月初手动更新",
        "url": "https://www.shantou.gov.cn/attachment/0/150/150864/2524702.pdf",
    },
    "spot": {
        "title": "电力现货参考",
        "day_ahead": "0.2815元/kWh（2026年上半年日前均价）",
        "realtime": "0.2675元/kWh（2026年上半年实时均价）",
        "settle": "0.2690元/kWh（2026年上半年新能源结算均价；显著低于煤电0.3892）",
        "date_note": "数据为2026年上半年，来源：广东电力交易中心《2026广东电力市场半年报告》",
        "url": "https://www.sohu.com/a/1071242745_122014422",
    },
    "green_trade": {
        "title": "绿电交易参考",
        "energy": "0.3763元/kWh（2026年上半年省内绿电电能量均价）",
        "env_value": "0.0182元/kWh（绿电环境价值均价；其中光伏0.0173）",
        "date_note": "数据为2026年上半年，来源：广东电力交易中心",
        "url": "https://www.sohu.com/a/1071242745_122014422",
    },
}

# 价格走势追踪的代表规格：(图例key, item关键词, spec关键词)
CHART_SERIES = [
    ("组件-TOPCon集中式", "组件", "集中式"),
    ("硅片-N型G10L", "硅片", "G10L"),
    ("电池片-TOPCon", "电池片", "TOPCon"),
    ("硅料-多晶硅", "硅料", "多晶硅"),
]


def bing_url(keyword):
    """Bing 新闻 RSS：自带发布者原文直链，国内网络可直接打开。"""
    return "https://www.bing.com/news/search?q=" + quote(keyword) + "&format=rss"


def bing_direct_url(link):
    """从 Bing apiclick 跳转链接中提取发布者原文直链（url 参数）。

    例：http://www.bing.com/news/apiclick.aspx?...&url=https%3a%2f%2fwww.sohu.com%2fa%2f...
       -> https://www.sohu.com/a/...
    提取失败时返回原链接，保证不丢数据。
    """
    if not link:
        return ""
    try:
        from urllib.parse import urlparse, parse_qs, unquote
        q = parse_qs(urlparse(link).query)
        u = q.get("url", [""])[0]
        return unquote(u) if u else link
    except Exception:
        return link


def strip_html(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def norm_title(title):
    t = re.sub(r"[\s\-—–_|丨·.,，。！？!?、；;：:「」『』\"'“”‘’（）()\[\]【】]+", "", title)
    return t.lower()


def split_source(title):
    if " - " in title:
        t, _, s = title.rpartition(" - ")
        if t.strip() and len(s.strip()) <= 12:
            return t.strip(), s.strip()
    return title.strip(), ""


def entry_datetime(entry):
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            try:
                return datetime.fromtimestamp(time.mktime(tp), tz=timezone.utc).astimezone(BEIJING)
            except Exception:
                pass
    return None


def parse_mid(price_str):
    """把 '0.64-0.70' / '5.5–7.5' / '1.20' 解析为区间中点，解析失败返回 None。"""
    s = (price_str or "").strip().replace("–", "-").replace("—", "-")
    parts = [p for p in s.split("-") if p.strip()]
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if not nums:
        return None
    return sum(nums) / len(nums)


def fetch_feed(category, kind, content):
    url = bing_url(content) if kind == "bing" else content
    try:
        fp = feedparser.parse(url)
    except Exception as e:
        print("[WARN] 拉取失败 %s %s: %s" % (category, url, e))
        return []
    cutoff = datetime.now(BEIJING) - timedelta(hours=HOURS)
    items = []
    for e in fp.entries:
        dt = entry_datetime(e)
        if dt is None or dt < cutoff:
            continue
        raw_title = strip_html(e.get("title", ""))
        if not raw_title:
            continue
        title, source = split_source(raw_title)
        source = e.get("news_source", "") or source  # Bing RSS 自带来源名
        summary = strip_html(e.get("description", ""))[:120]
        if source and summary == source:
            summary = ""
        items.append({
            "category": category,
            "title": title,
            "summary": summary,
            "source": source or ("量子位" if "qbitai" in url else ""),
            "url": bing_direct_url(e.get("link", "")),
            "date": dt.strftime("%Y-%m-%d"),
            "_ts": dt.timestamp(),
        })
    print("[INFO] %s <- %.60s... : %d 条（48h内）" % (category, url, len(items)))
    return items


def snapshot_prices(supply_chain):
    """从 supply_chain 提取代表规格的价格快照。"""
    items = []
    for key, item_kw, spec_kw in CHART_SERIES:
        match = None
        for r in supply_chain:
            if item_kw in (r.get("item") or "") and spec_kw in (r.get("spec") or ""):
                match = r
                break
        if not match:
            continue
        mid = parse_mid(match.get("price"))
        if mid is None:
            continue
        items.append({
            "key": key,
            "mid": round(mid, 4),
            "raw": match.get("price"),
            "unit": match.get("unit"),
            "quote_date": match.get("date"),
        })
    return items


def append_history(supply_chain):
    """价格快照追加到 history.json；无变化或当天已记则不追加。"""
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    hist = []
    if HISTORY_FILE.exists():
        try:
            hist = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print("[WARN] history.json 解析失败，将重建：%s" % e)
    snap_items = snapshot_prices(supply_chain)
    if not snap_items:
        print("[INFO] 本次无可追踪的价格快照，跳过 history 更新")
        return
    if hist:
        last = hist[-1]
        last_sig = json.dumps(last.get("items"), ensure_ascii=False, sort_keys=True)
        new_sig = json.dumps(snap_items, ensure_ascii=False, sort_keys=True)
        if last.get("date") == today or last_sig == new_sig:
            print("[INFO] 价格快照无变化，history.json 不追加")
            return
    hist.append({"date": today, "items": snap_items})
    hist = hist[-HISTORY_MAX:]
    HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] history.json 已追加快照：%s，共 %d 期" % (today, len(hist)))


def main():
    old = {}
    if DATA_FILE.exists():
        try:
            old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print("[WARN] 旧 data.json 解析失败，将重建：%s" % e)

    now = datetime.now(BEIJING)
    collected = {}
    for category, kind, content in FEEDS:
        collected.setdefault(category, []).extend(fetch_feed(category, kind, content))

    news = []
    for category, items in collected.items():
        seen = set()
        kept = []
        for it in sorted(items, key=lambda x: x["_ts"], reverse=True):
            key = norm_title(it["title"])
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(it)
            if len(kept) >= MAX_PER_CATEGORY:
                break
        if not kept:
            fallback = [n for n in old.get("news", []) if n.get("category") == category]
            if fallback:
                print("[INFO] %s 本次无更新，沿用旧数据 %d 条" % (category, len(fallback)))
                kept = fallback
        news.extend(kept)

    for it in news:
        it.pop("_ts", None)

    def newest(cat):
        cands = [n for n in news if n.get("category") == cat]
        return cands[0]["title"][:28] if cands else ""

    pv, ai = newest("光伏"), newest("AI")
    parts = []
    if pv:
        parts.append("光伏：" + pv)
    if ai:
        parts.append("AI：" + ai)
    digest = "；".join(parts) or old.get("digest", "")

    data = {
        "updated_at": now.isoformat(timespec="seconds"),
        "digest": digest,
        "electricity": ELECTRICITY,
        "news": news,
        "supply_chain": old.get("supply_chain", []),
        "policies": old.get("policies", []),
    }
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] data.json 已更新：news %d 条，updated_at=%s" % (len(news), data["updated_at"]))

    append_history(data["supply_chain"])


if __name__ == "__main__":
    main()

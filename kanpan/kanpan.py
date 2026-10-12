# -*- coding: utf-8 -*-
"""
八大游资 · 情绪周期看盘终端 v2.1 (cmd 版)
=====================================
v2.1 变更：全市场行情只保留沪深A股（剔除北交所）；自选股默认=最近一周涨停池
v2 变更：自选龙头梯队 → 方法论自动筛选候选
  底层选股条件（游资龙头候选）：
  【硬门槛】当日涨停(按板块阈值/剔新股/剔ST) + 流通市值20-200亿 + 现价3-40元
           + 换手3-30% + 成交额≥3亿
  【加分】连板高度(+1.5/板)、分歧转一致(昨涨停今续板+3)、板块领涨(+2)、
          妖股名字(三字+0.5/ABB+1)、人气(量比≥2 +1 / 换手8-20% +1)
  【降权】一字板×0.3、未封死×0.5、高位放量(连板≥5且换手>25%)×0.6标"高危"
          亏钱效应环境(昨涨停今均值<0)全局缩档
  【环境】上证5日线下方=弱势：仅保留首板候选加权(养家弱势三阶段)
数据源：腾讯行情(批量) + 新浪市场中心(涨停统计/行业板块/日K)
用法：  python kanpan.py          # 交互 r=刷新 q=退出 +/-=调速
        python kanpan.py --once   # 单次快照
"""
import sys, os, json, time, math, datetime, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "zt_history.json")
CFG   = os.path.join(HERE, "watchlist.json")

DEFAULT_WATCH_MAX = 25   # 默认自选池（最近一周涨停）最大展示数

def default_watch_recent(hist, days=5, limit=DEFAULT_WATCH_MAX):
    """自选股默认 = 最近一周(5个交易日)涨停板去重，按最近涨停日期倒序取前limit只"""
    dset = sorted(d for d in hist.get("dates", {}).keys() if hist["dates"].get(d))
    out, seen = [], set()
    for d in reversed(dset[-days:]):
        for code in hist["dates"].get(d, []):
            if code in seen or not is_hs_a(code): continue
            seen.add(code)
            out.append("sh" + code if code.startswith("6") else "sz" + code)
            if len(out) >= limit: return out
    return out

COLORS = {
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "cyan": "\033[36m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m",
}
def c(code, text):
    return f"{COLORS[code]}{text}{COLORS['reset']}"
def fmt_pct(v):
    if v is None: return "--"
    v = float(v)
    s = f"{v:+.2f}%"
    return c("red" if v > 0 else "green" if v < 0 else "dim", s)

# ---------- 数据获取 ----------
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
      "Referer": "https://finance.sina.com.cn/"}
def _http(url, timeout=12):
    import requests
    return requests.get(url, headers=UA, timeout=timeout)

def tencent_quotes(codes):
    out = {}
    for i in range(0, len(codes), 60):
        batch = codes[i:i+60]
        try:
            r = _http("https://qt.gtimg.cn/q=" + ",".join(batch))
        except Exception:
            continue
        for line in r.text.strip().split(";"):
            if "=" not in line: continue
            key = line.split("=")[0].split("_")[-1]
            f = line.split('"')[1].split("~")
            if len(f) < 45: continue
            try:
                out[key] = {
                    "name": f[1], "price": float(f[3]), "pct": float(f[32]),
                    "turnover": float(f[38]), "liutong_mv": float(f[44]),
                    "liangbi": float(f[49]) if len(f) > 49 and f[49] else None,
                    "zt_price": float(f[47]) if len(f) > 47 and f[47] else 0,
                }
            except (ValueError, IndexError):
                pass
    return out

def _sina_rank(page, asc):
    u = (f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
         f"Market_Center.getHQNodeData?page={page}&num=100&sort=changepercent&asc={asc}&node=hs_a&symbol=&_s_r_a=init")
    try:
        r = _http(u)
        return json.loads(r.text)
    except Exception:
        return []

def is_hs_a(code):
    """沪深A股：沪市6开头(含科创板68) / 深市0、3开头(含创业板30)；北交所(8/4/92)与B股剔除"""
    return bool(re.match(r"^(6|0|3)", code or ""))

def zt_threshold(code, name):
    if not is_hs_a(code): return None          # 非沪深A股（北交所等）不参与统计
    if re.match(r"^(N|C)", name or ""): return None
    if re.match(r"^(30|68)", code): return 19.5
    if "ST" in (name or "").upper(): return 4.8
    return 9.8

def sina_code_full(code):
    if code.startswith("6"): return "sh" + code
    if code.startswith(("0", "3")): return "sz" + code
    return "bj" + code

def fetch_market_snapshot():
    zt_list, dt_list, gain_top, lose_top = [], [], [], []
    for p in range(1, 6):
        for x in _sina_rank(p, 0):
            if not is_hs_a(x.get("code", "")): continue   # 只保留沪深A股
            if re.match(r"^(N|C)", x.get("name", "")): continue
            th = zt_threshold(x.get("code", ""), x.get("name", ""))
            if th is not None and x.get("changepercent", 0) >= th:
                zt_list.append({
                    "code": x["code"], "name": x["name"], "pct": x.get("changepercent"),
                    "price": float(x.get("trade", 0)), "turnover": float(x.get("turnoverratio", 0)),
                    "amount": float(x.get("amount", 0)), "nmc": float(x.get("nmc", 0)),
                    "high": float(x.get("high", 0)), "th": th,
                })
            if len(gain_top) < 20:
                gain_top.append(x)
    for p in range(1, 4):
        for x in _sina_rank(p, 1):
            if not is_hs_a(x.get("code", "")): continue   # 只保留沪深A股
            if re.match(r"^(N|C)", x.get("name", "")): continue
            th = zt_threshold(x.get("code", ""), x.get("name", ""))
            if th is not None and x.get("changepercent", 0) <= -th:
                dt_list.append({"code": x["code"], "name": x["name"], "pct": x.get("changepercent")})
            if len(lose_top) < 10:
                lose_top.append(x)
    sectors, sector_leaders = [], set()
    try:
        r = _http("https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php")
        m = re.search(r"=\s*(\{.*\})", r.text, re.S)
        if m:
            raw = json.loads(m.group(1).replace("'", '"'))
            items = []
            for k, v in raw.items():
                parts = v.split(",")
                if len(parts) >= 9:
                    try: items.append((parts[1], float(parts[5]), parts[8]))
                    except ValueError: pass
            items.sort(key=lambda t: -t[1])
            sectors = items[:12]
            sector_leaders = {x[2] for x in items[:5]}
    except Exception:
        pass
    return zt_list, dt_list, gain_top, lose_top, sectors, sector_leaders

def index_5d():
    """上证 5 日均线状态: (最新close, 5日均值, 强势?, 最近交易日)"""
    try:
        r = _http("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_=/CN_MarketDataService.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=6")
        m = re.search(r"\(\[(.*)\]\)", r.text, re.S)
        if not m: return None
        data = json.loads("[" + m.group(1) + "]")
        closes = [float(d["close"]) for d in data[-5:]]
        last_day = data[-1]["day"]
        return closes[-1], sum(closes) / len(closes), closes[-1] > sum(closes) / len(closes), last_day
    except Exception:
        return None

# ---------- 情绪引擎 ----------
def load_history():
    try:
        with open(CACHE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {"dates": {}}
def save_history(hist):
    with open(CACHE, "w", encoding="utf-8") as f: json.dump(hist, f, ensure_ascii=False)

def calc_lianban(hist, today, codes):
    hdays = sorted(hist.get("dates", {}).keys())
    lianban = {}
    for code in codes:
        n = 1
        for d in reversed(hdays):
            if d >= today: continue
            if code in hist["dates"].get(d, []):
                n += 1
            else:
                break
        lianban[code] = n
    return lianban

def emotion_phase(zt_n, dt_n, avg_prev, top_lianban):
    if dt_n >= 200 or (dt_n >= 80 and zt_n <= 30):
        return "冰点(绝望区·养家:敢空仓)", "cyan"
    if zt_n >= 80 and top_lianban and top_lianban >= 5 and avg_prev and avg_prev > 3:
        return "高潮(毕业照·只卖不买)", "yellow"
    if zt_n >= 50 and avg_prev and avg_prev > 1.5:
        return "主升(做主流龙头·分歧转一致)", "red"
    if zt_n >= 25 and dt_n <= 20:
        return "启动(冰点次日确认·极小仓试错)", "green"
    return "退潮(空仓不操作·就是赚钱)", "dim"

# ---------- 方法论选股打分 ----------
def score_candidates(zt_list, hist, today, sector_leaders, idx):
    """游资龙头候选：硬门槛 → 加分 → 降权，返回 (cands, lianban, avg_prev)"""
    today_codes = [x["code"] for x in zt_list]
    lianban = calc_lianban(hist, today, today_codes)
    # 昨日涨停今日表现（赚钱效应）：取最近一个"非空且非今日"交易日
    prev_days = sorted(d for d in hist.get("dates", {}).keys() if hist["dates"].get(d) and d != today)
    prev_list = hist["dates"].get(prev_days[-1], []) if prev_days else []
    avg_prev = None
    if prev_list:
        q = tencent_quotes([sina_code_full(x) for x in prev_list[:60]])
        vals = [v["pct"] for v in q.values() if v is not None]
        avg_prev = sum(vals) / len(vals) if vals else None
    # 腾讯批量补量比（候选涨停股）
    codes_full = [sina_code_full(x["code"]) for x in zt_list]
    q = tencent_quotes(codes_full)
    weak = idx is not None and not idx[2]   # 上证5日线下=弱势

    cands = []
    for x in zt_list:
        code = x["code"]
        nmc_yi = x["nmc"] / 10000.0          # 流通市值(亿)
        amount_yi = x["amount"] / 1e8        # 成交额(亿)
        # ---- 硬门槛 ----
        if not (20 <= nmc_yi <= 200): continue
        if not (3 <= x["price"] <= 40): continue
        if not (3 <= x["turnover"] <= 30): continue
        if amount_yi < 3: continue
        tq = q.get(codes_full[codes_full.index(sina_code_full(code))]) if sina_code_full(code) in q else None
        lb = lianban.get(code, 1)
        # 弱势环境：只保留首板候选（养家：弱势做新热点/回调反抽，不做高位连板）
        if weak and lb >= 2: continue
        # ---- 打分 ----
        s = 0.0
        note = []
        # 连板高度（空间板是情绪核心）
        if lb >= 2: s += 1.5 * (lb - 1)
        # 分歧转一致：昨日涨停今日续板
        if prev_list and code in prev_list:
            s += 3.0; note.append(c("red", "续板"))
        # 板块领涨（定义/定性：冰川）
        if sina_code_full(code) in sector_leaders:
            s += 2.0; note.append(c("yellow", "板块龙"))
        # 妖股名字（冰川五要素：三字/ABB）
        nm = x["name"].replace(" ", "")
        if len(nm) == 3 and re.match(r"^[\u4e00-\u9fa5]{3}$", nm):
            s += 0.5
            if nm[0] == nm[2]: s += 0.5; note.append(c("cyan", "ABB"))
        # 人气质量
        if tq and tq.get("liangbi") and tq["liangbi"] >= 2: s += 1.0
        if 8 <= x["turnover"] <= 20: s += 1.0
        # ---- 降权 / 标注 ----
        seal = x["pct"] >= x["th"] - 0.1        # 封死
        if x["turnover"] < 1.5 and seal:        # 一字板（换手极低且封死）
            s *= 0.3; note.append(c("dim", "一字"))
        elif not seal:                          # 未封死（涨幅在阈值附近没封上）
            s *= 0.5; note.append(c("yellow", "炸板"))
        if lb >= 5 and x["turnover"] > 25:      # 高位放量毕业照
            s *= 0.6; note.append(c("red", "高危"))
        cands.append({
            "code": code, "name": nm, "price": x["price"], "pct": x["pct"],
            "lb": lb, "turnover": x["turnover"],
            "liangbi": (tq["liangbi"] if tq and tq.get("liangbi") else None),
            "nmc": nmc_yi, "score": round(s, 1), "note": " ".join(note),
        })
    # 亏钱效应环境：全局缩档（只显示前8）
    limit = 8 if (avg_prev is not None and avg_prev < 0) else 15
    cands.sort(key=lambda r: -r["score"])
    return cands[:limit], lianban, avg_prev

# ---------- 渲染 ----------
def render(cfg_codes):
    lines = []
    now = datetime.datetime.now().strftime("%H:%M:%S")
    lines.append(c("bold", "╔══════════ 八大游资 · 情绪周期看盘 ══════════") + c("dim", f"   {now}"))
    idx = tencent_quotes(["sh000001", "sz399001", "sz399006", "sh000688"])
    if idx:
        lines.append("║ " + " │ ".join(
            f"{c('bold', idx[k]['name'])} {idx[k]['price']:.2f} {fmt_pct(idx[k]['pct'])}"
            for k in ("sh000001", "sz399001", "sz399006", "sh000688") if k in idx))
    zt_list, dt_list, gain_top, lose_top, sectors, sector_leaders = fetch_market_snapshot()
    hist = load_history()
    idx5 = index_5d()
    today = idx5[3] if idx5 else datetime.date.today().strftime("%Y-%m-%d")   # 真实最近交易日（周末/节假日不写错日期）
    hist.setdefault("dates", {})[today] = []
    cands, lianban, avg_prev = score_candidates(zt_list, hist, today, sector_leaders, idx5)
    top_lb = max(lianban.values()) if lianban else None
    lines.append("╠══ " + c("cyan", "情绪周期") + " ══")
    phase, ph_color = emotion_phase(len(zt_list), len(dt_list), avg_prev, top_lb)
    lines.append("║ " + c("bold", "阶段") + ": " + c(ph_color, phase))
    eff = "赚钱↑" if (avg_prev is not None and avg_prev > 0) else ("亏钱↓" if (avg_prev is not None and avg_prev < 0) else "--")
    lb_s = c("red", f"{top_lb}板") if top_lb else c("dim", "-")
    lines.append("║ " + c("bold", "涨停") + f" {c('red', str(len(zt_list)))} │ " +
                 c("bold", "跌停") + f" {c('green', str(len(dt_list)))} │ " +
                 c("bold", "空间板") + f" {lb_s} │ " +
                 c("bold", "昨涨停今") + f" {fmt_pct(avg_prev)} {eff}")
    # 游资龙头候选（方法论自动筛选）
    lines.append("╠══ " + c("cyan", "游资龙头候选") + c("dim", "(方法论自动筛选)") + " ══")
    lines.append("║ " + c("dim", "代码     名称     现价   涨跌%   连板 换手%  量比  流通市值 得分 状态"))
    if cands:
        for r in cands:
            lb2 = c("red", f"{r['lb']}板") if r["lb"] >= 2 else f"{r['lb']}板"
            lbq = f"{r['liangbi']:.2f}" if r["liangbi"] else "--"
            sc = c("red" if r["score"] >= 5 else "yellow" if r["score"] >= 3 else "dim", f"{r['score']:.1f}")
            lines.append(f"║ {r['code']:<7} {r['name']:<6} {r['price']:>7.2f} {fmt_pct(r['pct']):>9} "
                         f"{lb2:>4} {r['turnover']:>5.1f} {lbq:>5} {r['nmc']:>6.0f}亿 {sc:>5} {r['note']}")
    else:
        lines.append("║ " + c("dim", "今日无符合游资龙头条件的候选（情绪冰点/退潮时少做）"))
    # 自选池（默认=最近一周涨停池，观察昨日涨停今表现；可在 watchlist.json 自定义覆盖）
    q = tencent_quotes(cfg_codes)
    rows = [(code, q[code]) for code in cfg_codes if code in q]
    if rows:
        lines.append("╠══ " + c("cyan", "自选池") + c("dim", f"(最近一周涨停·{len(cfg_codes)}只)") + " ══")
        lines.append("║ " + c("dim", "代码      名称       现价    涨跌%  换手%  量比   流通市值"))
        rows.sort(key=lambda r: -r[1]["pct"])
        for code, v in rows:
            mv = v["liutong_mv"]
            if mv and mv >= 10000: mv_s = f"{mv/10000:.2f}万亿"
            elif mv: mv_s = f"{mv:.0f}亿"
            else: mv_s = "--"
            lbq = f"{v['liangbi']:.2f}" if v["liangbi"] else "--"
            lines.append(f"║ {code:<7} {v['name']:<7} {v['price']:>7.2f} {fmt_pct(v['pct']):>9} "
                         f"{v['turnover']:>5.1f} {lbq:>5} {mv_s:>8}")
    # 涨幅榜/跌幅榜
    lines.append("╠══ " + c("cyan", "涨幅榜 Top10") + " ══")
    for x in gain_top[:10]:
        lines.append(f"║ {x.get('code',''):<7} {x.get('name',''):<8} {x.get('trade',''):>8} {fmt_pct(x.get('changepercent'))}")
    lines.append("╠══ " + c("cyan", "跌幅榜 Top6 (亏钱效应)") + " ══")
    for x in lose_top[:6]:
        lines.append(f"║ {x.get('code',''):<7} {x.get('name',''):<8} {x.get('trade',''):>8} {fmt_pct(x.get('changepercent'))}")
    lines.append("╠══ " + c("cyan", "热点板块") + " ══")
    if sectors:
        lines.append("║ " + "  ".join(f"{c('red' if p>0 else 'green', n)}({p:+.1f}%)" for n, p, _ in sectors))
    else:
        lines.append("║ 板块数据暂不可用")
    lines.append(c("bold", "╚══════════════════════════════════════════════"))
    lines.append(c("dim", " [r]刷新  [+/-]调速  [q]退出  watchlist.json=自选池"))
    hist["dates"][today] = sorted(set(x["code"] for x in zt_list))   # 覆盖为当日沪深涨停名单（天然过滤北交所）
    save_history(hist)
    return "\n".join(lines)

def load_watchlist(cli_codes=None):
    """优先级：命令行 --codes > watchlist.json 内 codes > 最近一周涨停池(默认)"""
    if cli_codes: return cli_codes
    try:
        with open(CFG, "r", encoding="utf-8") as f:
            codes = json.load(f).get("codes")
            if codes: return codes
    except Exception:
        pass
    return default_watch_recent(load_history())

def main():
    cli_codes = None
    if "--codes" in sys.argv:
        i = sys.argv.index("--codes")
        cli_codes = sys.argv[i+1].split(",")
    once = "--once" in sys.argv
    codes = load_watchlist(cli_codes)
    try:
        from colorama import init
        init()
    except Exception:
        pass
    if once:
        print(render(codes)); return
    import msvcrt
    interval = 10
    while True:
        os.system("cls")
        try:
            print(render(codes))
        except Exception as e:
            print("刷新失败:", e)
        t0 = time.time()
        while time.time() - t0 < interval:
            if msvcrt.kbhit():
                k = msvcrt.getwch().lower()
                if k == "q": return
                if k == "+": interval = min(60, interval + 5)
                if k == "-": interval = max(3, interval - 5)
            time.sleep(0.2)

if __name__ == "__main__":
    main()

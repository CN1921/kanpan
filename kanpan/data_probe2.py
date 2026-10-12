# -*- coding: utf-8 -*-
"""数据通路测试2：腾讯批量行情 + 新浪涨跌停统计"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests

h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0", "Referer": "https://gu.qq.com/"}

# 1) 腾讯批量行情（指数+个股混合）
try:
    r = requests.get("https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000688,sh600519,sz300750",
                     headers=h, timeout=8)
    lines = [l for l in r.text.strip().split(";") if "=" in l]
    print(f"[OK] 腾讯批量行情: 返回 {len(lines)} 条")
    print(lines[0].split("~")[1:5], "| 现价~涨跌幅~换手~量比~流通市值~总市值:")
    f = lines[0].split("~")
    print("  现价:", f[3], "涨跌%:", f[32], "换手:", f[38], "量比:", f[49] if len(f) > 49 else "?",
          "流通市值(亿):", f[44] if len(f) > 44 else "?", "涨停价:", f[47] if len(f) > 47 else "?")
except Exception as e:
    print(f"[FAIL] 腾讯批量行情: {str(e)[:100]}")

# 2) 新浪涨跌停统计
for kind, name in [("zt", "涨停池"), ("dt", "跌停池")]:
    try:
        u = f"https://vip.stock.finance.sina.com.cn/q/go.php/vComStockUpDown/kind/{kind}.js"
        r = requests.get(u, headers={"User-Agent": h["User-Agent"]}, timeout=8)
        t = r.text.strip()
        # 提取家数与首条
        import re
        n = re.search(r"S_{kind}_n\s*=\s*\"?(\d+)\"?", t, re.I)
        arr = re.search(r"S_{kind}\s*=\s*\[(.*?)\];", t, re.S)
        print(f"[OK] 新浪{name}: 家数={n.group(1) if n else '?'} 原始前120字: {t[:120]}")
        if arr:
            items = arr.group(1).replace('"', "").split(",")
            print(f"      数组前12项: {items[:12]}")
    except Exception as e:
        print(f"[FAIL] 新浪{name}: {str(e)[:100]}")

# 3) 腾讯涨跌停/涨跌家数统计（qt 接口）
try:
    r = requests.get("https://qt.gtimg.cn/q=zsUpDown", headers=h, timeout=8)
    print(f"[OK] 腾讯涨跌家数: {r.text[:120]}")
except Exception as e:
    print(f"[FAIL] 腾讯涨跌家数: {str(e)[:100]}")

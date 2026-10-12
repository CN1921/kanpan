# -*- coding: utf-8 -*-
"""数据通路测试：确定 cmd 看盘工具可用的行情源"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def t(name, fn):
    try:
        r = fn()
        print(f"[OK]   {name}: {r}")
    except Exception as e:
        print(f"[FAIL] {name}: {str(e)[:100]}")

# 1) curl_cffi 直接请求东财全市场(一次5000条)
try:
    from curl_cffi import requests as creq
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=6000&po=1&np=1"
           "&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
           "&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11")
    r = creq.get(url, timeout=15, impersonate="chrome")
    j = r.json()
    data = j.get("data", {})
    t("curl_cffi东财全市场", lambda: f"diff={data.get('total')} 条, 首批{len(data.get('diff') or [])}")
except Exception as e:
    print(f"[FAIL] curl_cffi东财全市场: {str(e)[:120]}")

# 2) requests 带 UA 试东财
try:
    import requests
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
         "Referer": "https://quote.eastmoney.com/"}
    r = requests.get("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f2,f3,f12,f14", headers=h, timeout=10)
    t("requests东财带UA", lambda: f"status={r.status_code} body={r.text[:60]}")
except Exception as e:
    print(f"[FAIL] requests东财带UA: {str(e)[:100]}")

# 3) 新浪单只实时行情（快）
try:
    import requests
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    r = requests.get("https://hq.sinajs.cn/list=sh000001,sz399001", headers=h, timeout=8)
    t("新浪指数实时", lambda: r.text.split("\n")[0][:80])
except Exception as e:
    print(f"[FAIL] 新浪指数实时: {str(e)[:100]}")

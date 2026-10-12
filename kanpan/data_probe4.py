# -*- coding: utf-8 -*-
"""数据通路测试4：新浪 market center 单次拉取上限"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, json, time

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
      "Referer": "https://finance.sina.com.cn/"}

for num in (1000, 3000, 6000):
    try:
        t0 = time.time()
        u = (f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
             f"Market_Center.getHQNodeData?page=1&num={num}&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=init")
        r = requests.get(u, headers=UA, timeout=30)
        rows = json.loads(r.text)
        dt = time.time() - t0
        # 统计
        ups = sum(1 for x in rows if x.get('changepercent', 0) > 0)
        downs = sum(1 for x in rows if x.get('changepercent', 0) < 0)
        zt = [x for x in rows if x.get('changepercent', 0) >= 9.8 and 'ST' not in x.get('name', '').upper() and 'N' != x.get('name', '')[:1]]
        dt_ = [x for x in rows if x.get('changepercent', 0) <= -9.8]
        print(f"[OK] num={num}: 返回 {len(rows)} 条, 耗时 {dt:.1f}s | 上涨{ups} 下跌{downs} 涨停{len(zt)} 跌停{len(dt_)}")
        if len(rows) > 4000:
            print("     -> 一次可覆盖全市场，方案成立")
            break
    except Exception as e:
        print(f"[FAIL] num={num}: {str(e)[:100]}")

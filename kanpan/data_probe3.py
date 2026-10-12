# -*- coding: utf-8 -*-
"""数据通路测试3：新浪市场中心涨幅榜(替代涨停池) + 行业板块"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, json

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
      "Referer": "https://finance.sina.com.cn/"}

# 1) 涨幅榜第一页(按涨幅排序)
try:
    u = ("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
         "Market_Center.getHQNodeData?page=1&num=100&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=init")
    r = requests.get(u, headers=UA, timeout=10)
    rows = json.loads(r.text)
    print(f"[OK] 新浪涨幅榜: {len(rows)}条, 前3: ", [(x['code'], x['name'], x.get('changepercent')) for x in rows[:3]])
    # 统计涨停（涨幅>=9.9 且非ST）
    zt = [x for x in rows if x.get('changepercent', 0) >= 9.9 and 'ST' not in x.get('name', '').upper()]
    print(f"     第1页内涨停 {len(zt)} 只; 字段: {list(rows[0].keys())}")
except Exception as e:
    print(f"[FAIL] 新浪涨幅榜: {str(e)[:120]}")

# 2) 行业板块涨幅
for name, u in [
    ("新浪行业板块", "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"),
    ("腾讯行业板块", "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank/hotRank?type=industry"),
]:
    try:
        r = requests.get(u, headers=UA, timeout=10)
        print(f"[OK] {name}: status={r.status_code} len={len(r.text)} 前80字={r.text[:80]}")
    except Exception as e:
        print(f"[FAIL] {name}: {str(e)[:100]}")

# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests, json
UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0", "Referer": "https://finance.sina.com.cn/"}
u = ("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
     "Market_Center.getHQNodeData?page=1&num=100&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=init")
rows = json.loads(requests.get(u, headers=UA, timeout=10).text)
for x in rows[:5]:
    print(x["code"], x["name"], "price", x["trade"], "mktcap", x["mktcap"], "nmc", x["nmc"],
          "turnover", x["turnoverratio"], "amount", x["amount"], "vol", x["volume"])
# 5日K线（上证）用于大盘强弱
r = requests.get("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_=/CN_MarketDataService.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=6",
                 headers=UA, timeout=10)
print("5日K:", r.text[:220])

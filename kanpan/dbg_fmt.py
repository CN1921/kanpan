# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests
UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0", "Referer": "https://finance.sina.com.cn/"}
r = requests.get("https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php", headers=UA, timeout=10)
print("新浪板块原文:", r.text[:400])
print()
r2 = requests.get("https://qt.gtimg.cn/q=sh600519", headers=UA, timeout=10)
f = r2.text.split('"')[1].split("~")
print("茅台字段 35-52:")
for i in range(35, 53):
    if i < len(f):
        print(" ", i, repr(f[i]))

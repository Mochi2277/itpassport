#!/usr/bin/env python3
"""Diagnose independently published answer-key formats; read-only."""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
urls={
"alternative_2020":"https://it-passport.navi-index.com/past-questions/"+quote("ITパスポート試験 令和2年度 10月分")+"/",
"alternative_2021":"https://it-passport.navi-index.com/past-questions/"+quote("ITパスポート試験 令和3年度分")+"/",
"alternative_2022":"https://it-passport.navi-index.com/past-questions/"+quote("ITパスポート試験 令和4年度分")+"/",
"alternative_2023":"https://it-passport.navi-index.com/past-questions/"+quote("ITパスポート試験 令和5年度分")+"/",
"official_2022":"https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2022r04_ip_ans.pdf"
}
for label,url in urls.items():
 try:
  r=requests.get(url,timeout=18,headers={"User-Agent":"Mozilla/5.0"});s=BeautifulSoup(r.content,"html.parser");t=s.get_text(" ",strip=True)
  tables=s.find_all("table")
  print(label,"http",r.status_code,"bytes",len(r.content),"type",r.headers.get("Content-Type"),"table_count",len(tables),"title",s.title.get_text(" ",strip=True) if s.title else "",flush=True)
  print("sample:",t[:900],flush=True)
  print("tables_sample:",[x.get_text(" ",strip=True)[:500] for x in tables[:2]],flush=True)
 except Exception as e:print(label,"ERROR",str(e)[:250],flush=True)

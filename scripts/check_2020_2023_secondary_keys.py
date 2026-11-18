#!/usr/bin/env python3
"""Independently compare 2020-2023 site answer keys to a separately hosted
100-question answer listing. This is NOT direct IPA PDF verification.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
HOST="https://it-passport.navi-index.com/past-questions/"
CATEGORIES={
  2020:"ITパスポート試験 令和2年度 10月分",
  2021:"ITパスポート試験 令和3年度分",
  2022:"ITパスポート試験 令和4年度分",
  2023:"ITパスポート試験 令和5年度分",
}
KANA="アイウエ"
def current(year):
    s=(ROOT/f"questions_{year}.js").read_text("utf-8")
    return json.loads(s.split(f"window.QUESTIONS_{year} = ",1)[1].rsplit(";",1)[0])
def parse(url):
    res=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=30)
    res.raise_for_status()
    soup=BeautifulSoup(res.content,"html.parser")
    result={}
    tables=soup.find_all("table")
    for table in tables:
        for row in table.find_all("tr"):
            cells=row.find_all(["td","th"],recursive=False)
            if len(cells)<2:continue
            nr=cells[0].get_text(" ",strip=True)
            letter=cells[1].get_text(" ",strip=True)
            m=re.fullmatch(r"問\s*(\d{1,3})",nr)
            if m and letter in KANA:
                n=int(m.group(1))
                if n in result:raise RuntimeError(f"Duplicate external answer number {n}")
                result[n]=letter
    if len(result)!=100 or sorted(result)!=list(range(1,101)):
        raise RuntimeError(f"Independent answer table incomplete at {url} ({len(result)} of 100)")
    return result
def main():
    result={}
    mismatches=0
    for year,name in CATEGORIES.items():
        url=HOST+quote(name)+"/"
        secondary=parse(url)
        public=[q for q in current(year) if q["year"]==str(year)]
        if len(public)!=100:raise RuntimeError(f"Invalid site year {year}")
        different=[{"number":q["number"],"site":"アイウエ"[q["answer"]],"secondary":secondary[q["number"]]}
                   for q in public if KANA[q["answer"]]!=secondary[q["number"]]]
        mismatches+=len(different)
        result[str(year)]={"compared":100,"agreed":100-len(different),
                            "mismatches":different,"secondarySource":url,
                            "verificationLevel":"independent-secondary-website-not-official-PDF"}
    report={"summary":{"years":4,"compared":400,"agreed":400-mismatches,
                        "mismatches":mismatches,"officialIPAAnswerPDFVerified":0},
            "years":result}
    path=ROOT/"data"/"2020-2023-independent-answer-audit.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

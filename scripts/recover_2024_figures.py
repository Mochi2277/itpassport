#!/usr/bin/env python3
"""Recover missing R06 problem figures from accessible question transcriptions.
Only accepts image bytes actually present in a cited source; never creates a fabricated diagram.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"assets/questions/2024"
DATA=ROOT/"questions_2024.js"
HEADERS={"User-Agent":"Mozilla/5.0"}
TARGET=(41,60,67)
prefix="window.QUESTIONS_2024 = "

def main():
    raw=DATA.read_text("utf-8")
    start=raw.index(prefix)+len(prefix)
    end=raw.rfind(";")
    questions=json.loads(raw[start:end])
    DEST.mkdir(parents=True,exist_ok=True)
    report=[]
    for number in TARGET:
        q=next(x for x in questions if x["number"]==number and x["year"]=="2024")
        url=f"https://e-words.jp/p/e-ip-past-R06-{number}.html"
        response=requests.get(url,headers=HEADERS,timeout=35)
        response.raise_for_status()
        page=BeautifulSoup(response.content,"html.parser")
        box=page.select_one(".past-item .lp-q-box")
        if box is None:raise RuntimeError(f"No reliable question block for {number}")
        imgs=[]
        for im in box.select("img"):
            if im.find_parent("table",class_="q-options") is not None:continue
            src=urljoin(url,im.get("src") or "")
            if src.startswith("https://"):imgs.append(src)
        found=[]
        for i,url in enumerate(imgs):
            r=requests.get(url,headers=HEADERS,timeout=35)
            r.raise_for_status()
            content_type=r.headers.get("Content-Type","")
            if not content_type.startswith("image/"):continue
            extension=".png" if "png" in content_type else ".gif" if "gif" in content_type else ".jpg"
            name=f"q{number:03d}-{i+1}{extension}"
            (DEST/name).write_bytes(r.content)
            found.append(f"assets/questions/2024/{name}")
        if found:
            q["figureUrl"]=found[0]
            q["figureFiles"]=found
            q["figureAlt"]=f"令和6年度問{number}の図"
            q["figureCaption"]="公開問題の転記資料に掲載されている図（IPA原本との最終照合待ち）"
            q["visualReviewStatus"]="figure-recovered-needs-ipa-verification"
        report.append({"number":number,"images":found,"page":f"https://e-words.jp/p/e-ip-past-R06-{number}.html"})
    DATA.write_text(raw[:start]+json.dumps(questions,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    (ROOT/"data"/"2024-image-recovery.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RECOVERED",json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()

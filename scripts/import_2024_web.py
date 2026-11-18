#!/usr/bin/env python3
"""Import the 2024 IT Passport questions from the HTML transcription of IPA's release.

The official IPA question PDF is sometimes blocked to CI runners, so this uses
e-Words' HTML transcription as a transport source only. Answer keys are independently
verified against IPA's official answer sheet. Explanations are NOT reused.
Text/diagrams remain subject to editorial PDF comparison.
"""
import concurrent.futures
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
KANA="アイウエ"
ANSWER_ROWS=[
"エ イ ウ イ イ エ イ ウ ア イ イ ア エ ア ウ イ エ ウ ウ イ ウ ウ ア ウ ア",
"ア イ ア イ エ エ イ エ エ エ ア エ イ エ ア イ イ イ ア エ エ ウ イ ア エ",
"エ ア ウ ウ ウ イ ウ エ イ イ ア エ ア イ ウ エ ウ ウ イ ウ イ ウ エ エ エ",
"ウ ウ ア エ ア エ イ エ エ エ ウ エ ア ウ ア エ ウ イ ア イ ウ イ イ ウ イ"
]
KEYS=[KANA.index(v) for row in ANSWER_ROWS for v in row.split()]
assert len(KEYS)==100 and Counter(KEYS)==Counter({0:19,1:28,2:25,3:28})
IPA_PDF="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2024r06_ip_qs.pdf"
IPA_ANS="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2024r06_ip_ans.pdf"
URL="https://e-words.jp/p/e-ip-past-R06-{}.html"

def normalize(s):
    s=re.sub(r"[ \t\u3000]+"," ",s)
    s=re.sub(r"\n[ \t]*\n[ \t]*\n+","\n\n",s)
    return s.strip()

def text_with_breaks(tag):
    # Keep paragraph boundaries and original a/b/c enumeration where present.
    clone=BeautifulSoup(str(tag),"html.parser")
    for br in clone.find_all("br"):br.replace_with("\n")
    for part in clone.find_all(["p","div","li","tr"]):
        part.insert_before("\n")
        part.insert_after("\n")
    return normalize(clone.get_text(" ",strip=False))

def fetch_question(n):
    url=URL.format(n)
    for attempt in range(4):
        try:
            r=requests.get(url,timeout=35,headers={"User-Agent":"Mozilla/5.0 (compatible; ITPassportStudyRoom/1.0)"})
            r.raise_for_status()
            doc=BeautifulSoup(r.content,"html.parser")
            box=doc.select_one(".past-item .lp-q-box")
            prompt=doc.select_one(".past-item .q-question")
            option_table=doc.select_one(".past-item table.q-options")
            answer=doc.select_one(".past-item .lp-ans-mark")
            if not (box and prompt and option_table and answer):
                raise ValueError(f"Missing primary page structure for question {n}")
            rows=[]
            for tr in option_table.find_all("tr"):
                cells=tr.find_all(["th","td"],recursive=False)
                if len(cells)<2: continue
                label=normalize(cells[0].get_text(" ",strip=True))
                if label in list(KANA):
                    rows.append((label,normalize(" | ".join(text_with_breaks(td) for td in cells[1:]))))
            if [a for a,_ in rows]!=list(KANA) and n==24:
                rows=[
                  ("ア","営業日数 | 安全在庫量 | 現在の発注残"),
                  ("イ","営業日数 | 現在の発注残 | 安全在庫量"),
                  ("ウ","発注間隔 | 安全在庫量 | 現在の発注残"),
                  ("エ","発注間隔 | 現在の発注残 | 安全在庫量"),
                ]
            if [a for a,_ in rows]!=list(KANA):
                raise ValueError(f"Cannot parse all four options for question {n}: {[a for a,_ in rows]}")
            if KANA.index(normalize(answer.get_text()))!=KEYS[n-1]:
                raise ValueError(f"Official IPA answer mismatch for question {n}")
            question_text=text_with_breaks(prompt)
            if len(question_text)<12:
                raise ValueError(f"Too-short question {n}")
            if any(not v for _,v in rows):
                raise ValueError(f"Empty choice in question {n}")
            topic_node=doc.select_one(".past-item .lp-sec")
            topic=normalize(topic_node.get_text(" ",strip=True)).split("›")[-1].strip() if topic_node else ""
            # Additional source diagrams/tables may exist between question and answer options.
            others=[t for t in box.find_all("table") if "q-options" not in (t.get("class") or [])]
            embedded=box.find_all("img")
            has_extra=bool(others or embedded)
            table_rows=[]
            for table in others:
                group=[]
                for tr in table.find_all("tr"):
                    cells=[normalize(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
                    if cells:group.append(cells)
                if group:table_rows.append(group)
            field="ストラテジ系" if n<=35 else "マネジメント系" if n<=55 else "テクノロジ系"
            explanation=f"IPAの公式正答は「{KANA[KEYS[n-1]]}」です。各選択肢を比較し、正解の理由を確認しましょう。詳しいオリジナル解説は順次追加します。"
            result={
                "id":f"ipa-2024-{n:03d}","year":"2024","number":n,
                "field":field,"topic":topic or field,"q":question_text,
                "displayText":question_text,"displayTextSource":"external-transcription-needs-pdf-review",
                "choices":[v for _,v in rows],"answer":KEYS[n-1],"explanation":explanation,
                "tip":"原文PDFと照合して復習しましょう。",
                "source":"IPA 令和6年度 ITパスポート試験 公開問題",
                "sourceUrl":IPA_PDF,"answerSourceUrl":IPA_ANS,
                "adapted":True,"textTransportSource":"https://e-words.jp/p/e-ip-past-R06.html",
                "extractionStatus":"needs-pdf-review"
            }
            if table_rows:result["figureTables"]=table_rows
            if embedded:result["figureRequired"]=True
            return result,{"n":n,"options":4,"figureTables":len(table_rows),"sourceImages":len(embedded),"questionLength":len(question_text)}
        except Exception as exc:
            if attempt==3:raise
            time.sleep(2+attempt*2)
    raise AssertionError("unreachable")

def main():
    def safe(n):
        try:return fetch_question(n)
        except Exception as ex:return {"number":n,"error":str(ex)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        values=list(pool.map(safe,range(1,101)))
    failures=[v for v in values if isinstance(v,dict)]
    if failures:
        print("IMPORT_VALIDATION_FAILURES",json.dumps(failures,ensure_ascii=False))
        raise RuntimeError(f"Could not validate {len(failures)} questions")
    questions=[x for x,_ in values]
    report=[r for _,r in values]
    assert len(questions)==100
    assert [q["number"] for q in questions]==list(range(1,101))
    assert all(len(q["choices"])==4 for q in questions)
    assert all(q["answer"]==KEYS[q["number"]-1] for q in questions)
    assert all(q["q"] and len(q["q"])>10 for q in questions)
    (ROOT/"questions_2024.js").write_text("window.QUESTIONS_2024 = "+json.dumps(questions,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"2024-import-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"year":2024,"count":len(questions),"withTables":sum(bool(q.get("figureTables")) for q in questions),"needsImages":sum(bool(q.get("figureRequired")) for q in questions)},ensure_ascii=False))

if __name__=="__main__":main()

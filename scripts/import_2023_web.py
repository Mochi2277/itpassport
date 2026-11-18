#!/usr/bin/env python3
"""Extract R05 IPA questions from public HTML transcription for manual QA.
No text or answer is guessed; block publication if a question cannot be extracted.
IPA official PDF: https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2023r05_ip_qs.pdf
"""
import concurrent.futures
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, NavigableString

ROOT=Path(__file__).resolve().parents[1]
KANA="アイウエ"
BASE="https://e-words.jp/p/e-ip-past-R05-{}.html"
IPA_Q="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2023r05_ip_qs.pdf"
IPA_A="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2023r05_ip_ans.pdf"
OUTPUT=ROOT/"questions_2023.js"
IMAGE_ROOT=ROOT/"assets"/"questions"/"2023"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; ExamPublisher/1.0)"}

def normalize(s):
    s=re.sub(r"[\u3000 \t]+"," ",s)
    s=re.sub(r"[ \t]*\n[ \t]*","\n",s)
    s=re.sub(r"\n{3,}","\n\n",s)
    return s.strip()

def with_breaks(node):
    clone=BeautifulSoup(str(node),"html.parser")
    for br in clone.find_all("br"):br.replace_with("\n")
    for part in clone.find_all(["p","div","li","tr"]):
        part.insert_before("\n")
        part.insert_after("\n")
    s=clone.get_text(" ",strip=False)
    s=normalize(s)
    # Linkified technical words in source produce spaces around terms; remove only
    # whitespace adjacent to Japanese script, preserving original paragraph boundaries.
    s=re.sub(r"(?<=[\u3040-\u30ff\u3400-\u9fff々]) +(?=[^\n])","",s)
    s=re.sub(r"(?<=[^\n]) +(?=[\u3040-\u30ff\u3400-\u9fff々])","",s)
    return s

def tables_from(parent):
    tables=[]
    for tbl in parent.find_all("table"):
        if "q-options" in (tbl.get("class") or []):continue
        rows=[]
        for tr in tbl.find_all("tr"):
            cells=[normalize(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"],recursive=False)]
            if cells:rows.append(cells)
        if rows:tables.append(rows)
    return tables

def fetch(n):
    url=BASE.format(n)
    for attempt in range(3):
        try:
            res=requests.get(url,timeout=40,headers=HEADERS)
            res.raise_for_status()
            doc=BeautifulSoup(res.content,"html.parser")
            box=doc.select_one(".past-item .lp-q-box")
            prompt=doc.select_one(".past-item .q-question")
            answer=doc.select_one(".past-item .lp-ans-mark")
            opts=doc.select_one(".past-item table.q-options")
            if not all([box,prompt,answer,opts]):
                raise ValueError("Required question or answer markup unavailable")
            ak=normalize(answer.get_text())
            if ak not in KANA: raise ValueError("Invalid answer key "+ak)
            choices=[]
            for tr in opts.find_all("tr"):
                cells=tr.find_all(["th","td"],recursive=False)
                if len(cells)<2:continue
                label=normalize(cells[0].get_text(" ",strip=True))
                if label in KANA and len(label)==1:
                    choices.append((label," | ".join(with_breaks(c) for c in cells[1:])))
            # IPA combination tables: their four answers are stored in a
            # separate matrix instead of the standard q-options table.
            matrix_choices = {
                8: ["成約件数 | 売上高","成約件数 | 提案件数","提案件数 | 売上高","提案件数 | 成約件数"],
                37: ["外観 | 客観的な","経営 | 被監査側の","契約 | 経営者側の","取引 | 良心的な"],
                42: ["a | b | c","a | c | b","b | a | c","c | b | a"],
                47: ["a | b | c","a | c | b","b | a | c","c | b | a"],
                48: ["サービスレベルマネジメント | IPS","サービスレベルマネジメント | UPS","ファシリティマネジメント | IPS","ファシリティマネジメント | UPS"],
                63: ["1Tバイト | 1Tバイト","1Tバイト | 500Gバイト","500Gバイト | 1Tバイト","500Gバイト | 500Gバイト"],
                86: ["共通 | 公開","共通 | 秘密","公開 | 共通","公開 | 秘密"],
            }
            if [x[0] for x in choices] != list(KANA) and n in matrix_choices:
                choices=list(zip(list(KANA),matrix_choices[n]))
            if [x[0] for x in choices] != list(KANA):
                raise ValueError("Cannot extract 4 options, got "+str([x[0] for x in choices])+"; tableHTML="+str(opts)[:500])
            if any(not value.strip() for _,value in choices):raise ValueError("Empty choice")
            question=with_breaks(prompt)
            if len(question)<12:raise ValueError("Question too short")
            extra_tables=tables_from(box)
            imgs=[]
            for image in box.find_all("img"):
                u=urljoin(url,image.get("src") or "")
                if u.startswith("http"):imgs.append(u)
            field="ストラテジ系" if n<=35 else "マネジメント系" if n<=55 else "テクノロジ系"
            tax=doc.select_one(".past-item .lp-sec")
            topic=normalize(tax.get_text(" ",strip=True)).split("›")[-1].strip() if tax else field
            obj={"id":f"ipa-2023-{n:03d}","year":"2023","number":n,
                 "field":field,"topic":topic,"q":question,"displayText":question,
                 "displayTextSource":"external-transcription-needs-pdf-review",
                 "choices":[v for _,v in choices],"answer":KANA.index(ak),
                 "explanation":f"正解は「{ak}」です。解説は校閲後に追加します。まず公式問題・正答PDFも確認してください。",
                 "tip":"IPA公式問題・正答PDFで復習してください。",
                 "source":"IPA 令和5年度 ITパスポート試験 公開問題","sourceUrl":IPA_Q,
                 "answerSourceUrl":IPA_A,"textTransportSource":url,
                 "adapted":True,"extractionStatus":"needs-pdf-review"}
            if extra_tables:obj["figureTables"]=extra_tables
            if imgs:obj["figureRequired"]=True;obj["_imageSources"]=imgs
            return obj,{"number":n,"choices":4,"figureTables":len(extra_tables),
                        "images":imgs,"length":len(question)}
        except Exception as e:
            if attempt==2:raise RuntimeError(f"Question {n}: {e}") from e
            time.sleep(1+attempt*2)

def main():
    # This is an initial-import script only: never overwrite the published,
    # manually corrected data on a subsequent workflow run.
    if OUTPUT.exists():
        existing=OUTPUT.read_text(encoding="utf-8")
        if existing.startswith("window.QUESTIONS_2023 = ") or "window.QUESTIONS_2023 = " in existing:
            try:
                contents=existing.split("window.QUESTIONS_2023 = ",1)[1].rsplit(";",1)[0]
                if len(json.loads(contents))==100:
                    print("SKIP: published 100-question data exists; review/edit it directly")
                    return
            except Exception: pass
    def safe(n):
        try:return fetch(n)
        except Exception as e:return {"number":n,"error":str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:
        results=list(workers.map(safe,range(1,101)))
    errors=[r for r in results if isinstance(r,dict)]
    if errors:
        print("IMPORT_ERRORS",json.dumps(errors,ensure_ascii=False))
        raise SystemExit(f"Missing or invalid questions: {len(errors)}")
    questions=[v[0] for v in results]
    report=[v[1] for v in results]
    # Download referenced original diagram files as static assets.
    IMAGE_ROOT.mkdir(parents=True,exist_ok=True)
    for q in questions:
        imgs=q.pop("_imageSources",[])
        if imgs:
            # The first linked figure is displayed; store all assets for audit.
            local=[]
            for index,src in enumerate(imgs):
                r=requests.get(src,timeout=40,headers=HEADERS);r.raise_for_status()
                if not r.headers.get("Content-Type","").startswith("image/"):
                    raise RuntimeError(f"Image download was not an image: {q['number']}")
                suffix=".png" if "png" in r.headers["Content-Type"] else ".gif" if "gif" in r.headers["Content-Type"] else ".jpg"
                file=IMAGE_ROOT/f"q{q['number']:03d}-{index+1}{suffix}"
                file.write_bytes(r.content)
                local.append(f"assets/questions/2023/{file.name}")
            q["figureUrl"]=local[0];q["figureAlt"]=f"令和5年度問{q['number']}の図"
            q["figureCaption"]="問題の図（公開問題の転記資料から取得）"
            q["figureFiles"]=local
    assert len(questions)==100
    assert [q["number"] for q in questions]==list(range(1,101))
    assert all(len(q["choices"])==4 for q in questions)
    assert all(q["q"] and all(q["choices"]) for q in questions)
    OUTPUT.write_text("window.QUESTIONS_2023 = "+json.dumps(questions,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"2023-import-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("IMPORT_SUCCESS",json.dumps({"count":len(questions),"withTables":sum(bool(q.get("figureTables")) for q in questions),
                                     "withImages":sum(bool(q.get("figureUrl")) for q in questions)},ensure_ascii=False))

if __name__=="__main__":main()

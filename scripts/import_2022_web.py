#!/usr/bin/env python3
"""Extract R04 IPA questions from public HTML transcription for manual QA.
No text or answer is guessed; block publication if a question cannot be extracted.
IPA official PDF: https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2022r04_ip_qs.pdf
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
BASE="https://e-words.jp/p/e-ip-past-R04-{}.html"
IPA_Q="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2022r04_ip_qs.pdf"
IPA_A="https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2022r04_ip_ans.pdf"
OUTPUT=ROOT/"questions_2022.js"
IMAGE_ROOT=ROOT/"assets"/"questions"/"2022"
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
            # Combination answer matrices: extract actual cells rather than
            # inventing replacements for unseen source choices.
            if [x[0] for x in choices] != list(KANA):
                for matrix in box.find_all("table"):
                    if matrix is opts:continue
                    matrix_rows=[]
                    for tr in matrix.find_all("tr"):
                        cells=tr.find_all(["th","td"],recursive=False)
                        if len(cells)<2:continue
                        label=normalize(cells[0].get_text(" ",strip=True))
                        if label in KANA and len(label)==1:
                            matrix_rows.append((label," | ".join(with_breaks(cell) for cell in cells[1:])))
                    if [t[0] for t in matrix_rows]==list(KANA) and all(v for _,v in matrix_rows):
                        choices=matrix_rows
                        break
            if [x[0] for x in choices] != list(KANA):
                raise ValueError("Cannot extract 4 options, got "+str([x[0] for x in choices])+"; tableHTML="+str(opts)[:500])
            if n==32:
                # IPA original: all four options are visual process diagrams.
                # The SVG versions were manually reconstructed by inspecting the
                # official PDF; provide them as visible option diagrams.
                choices=list(zip(list(KANA), [
                    "工程を一方向に順番に進める図",
                    "工程図と製作の間で手戻りする図",
                    "全工程を終えて最初に戻る図",
                    "製作図・工程図・製作を並行して進める図",
                ]))
            if any(not value.strip() for _,value in choices):raise ValueError("Empty choice")
            question=with_breaks(prompt)
            if len(question)<12:raise ValueError("Question too short")
            extra_tables=tables_from(box)
            # Answer matrix will appear in question prompt; keep it for context
            # but remove the duplicate from the auxiliary figure display.
            extra_tables=[t for t in extra_tables if not (len(t)==5 and [r[0] for r in t[1:]]==list(KANA))]
            imgs=[]
            for image in box.find_all("img"):
                u=urljoin(url,image.get("src") or "")
                if u.startswith("http"):imgs.append(u)
            field="ストラテジ系" if n<=35 else "マネジメント系" if n<=55 else "テクノロジ系"
            tax=doc.select_one(".past-item .lp-sec")
            topic=normalize(tax.get_text(" ",strip=True)).split("›")[-1].strip() if tax else field
            obj={"id":f"ipa-2022-{n:03d}","year":"2022","number":n,
                 "field":field,"topic":topic,"q":question,"displayText":question,
                 "displayTextSource":"external-transcription-needs-pdf-review",
                 "choices":[v for _,v in choices],"answer":KANA.index(ak),
                 "explanation":f"正解は「{ak}」です。解説は校閲後に追加します。まず公式問題・正答PDFも確認してください。",
                 "tip":"IPA公式問題・正答PDFで復習してください。",
                 "source":"IPA 令和4年度 ITパスポート試験 公開問題","sourceUrl":IPA_Q,
                 "answerSourceUrl":IPA_A,"textTransportSource":url,
                 "adapted":True,"extractionStatus":"needs-pdf-review"}
            if n==32:
                obj["choiceFigures"]=[f"assets/questions/2022/q032-choice-{i}.svg" for i in range(1,5)]
                obj["choiceFigureCaption"]="原本の図を基にした学習用再作図です。細部はIPA公式PDFでご確認ください。"
                obj["extractionStatus"]="redrawn-from-official-pdf"
            if extra_tables:obj["figureTables"]=extra_tables
            obj["answerVerification"]="transcription-answer-key-needs-official-review"
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
        if existing.startswith("window.QUESTIONS_2022 = ") or "window.QUESTIONS_2022 = " in existing:
            try:
                contents=existing.split("window.QUESTIONS_2022 = ",1)[1].rsplit(";",1)[0]
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
                local.append(f"assets/questions/2022/{file.name}")
            q["figureUrl"]=local[0];q["figureAlt"]=f"令和4年度問{q['number']}の図"
            q["figureCaption"]="問題の図（公開問題の転記資料から取得）"
            q["figureFiles"]=local
    assert len(questions)==100
    assert [q["number"] for q in questions]==list(range(1,101))
    assert all(len(q["choices"])==4 for q in questions)
    assert all(q["q"] and all(q["choices"]) for q in questions)
    OUTPUT.write_text("window.QUESTIONS_2022 = "+json.dumps(questions,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"2022-import-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("IMPORT_SUCCESS",json.dumps({"count":len(questions),"withTables":sum(bool(q.get("figureTables")) for q in questions),
                                     "withImages":sum(bool(q.get("figureUrl")) for q in questions)},ensure_ascii=False))

if __name__=="__main__":main()

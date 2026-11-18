#!/usr/bin/env python3
"""Audit seven public IT Passport exam years for missing data and answer consistency.
IPA answer keys for 2024–2026 manually transcribed from official one-page answer PDFs.
Older answer keys are NOT marked officially checked by this script.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KANA="アイウエ"
OFFICIAL_ANSWERS={
  2024:[
    "エ イ ウ イ イ エ イ ウ ア イ イ ア エ ア ウ イ エ ウ ウ イ ウ ウ ア ウ ア",
    "ア イ ア イ エ エ イ エ エ エ ア エ イ エ ア イ イ イ ア エ エ ウ イ ア エ",
    "エ ア ウ ウ ウ イ ウ エ イ イ ア エ ア イ ウ エ ウ ウ イ ウ イ ウ エ エ エ",
    "ウ ウ ア エ ア エ イ エ エ エ ウ エ ア ウ ア エ ウ イ ア イ ウ イ イ ウ イ"
  ],
  2025:[
    "ウ ウ イ エ ウ イ イ イ ウ エ エ エ ウ イ ア イ ア ア ア イ イ ウ ウ エ ア",
    "ウ イ エ イ エ イ ウ ア イ エ ア エ エ ア イ エ ア ア エ ア イ エ ア ウ ア",
    "エ ア イ ア ア ア イ ウ ア エ ウ ア ウ イ ア イ イ ウ イ エ エ イ ウ ア ウ",
    "ウ イ エ ア ウ エ ウ ウ イ イ エ ウ イ ア エ エ ア ウ イ ウ ウ ア ウ ウ ア"
  ],
  2026:[
    "ア ア ウ イ エ エ イ ウ イ エ エ エ ウ ア イ ア イ ア ア イ ウ エ イ ア エ",
    "ア イ イ ウ ア ウ ウ ウ ア エ ウ エ イ ウ ア ウ イ イ イ イ ウ ウ ウ ア ウ",
    "エ ア イ ウ ウ エ ウ ア ウ ア イ エ ウ ウ エ イ イ エ ウ エ ア イ エ ア エ",
    "エ ウ エ ウ エ ア ア ア エ エ エ ア ア イ ウ ウ イ ア イ イ ア イ ウ イ ウ"
  ]
}
def read(year):
    path=ROOT/("questions.js" if year==2025 else f"questions_{year}.js")
    s=path.read_text("utf-8")
    header="window.QUESTIONS = " if year==2025 else f"window.QUESTIONS_{year} = "
    return json.loads(s.split(header,1)[1].rsplit(";",1)[0])

def check():
    findings=[]
    score=[]
    ids=set()
    fingerprints=defaultdict(list)
    for year in range(2020,2027):
        questions=read(year)
        public=[x for x in questions if x.get("year")==str(year)]
        bynum={x.get("number"):x for x in public}
        verified=0
        key=[c for row in OFFICIAL_ANSWERS.get(year,[]) for c in row.split()]
        if key and len(key)!=100:raise AssertionError(f"{year}: invalid reference answer count")
        if len(public)!=100:
            findings.append(dict(severity="error",year=year,code="wrong-count",count=len(public)))
        for n in range(1,101):
            q=bynum.get(n)
            if q is None:
                findings.append(dict(severity="error",year=year,number=n,code="missing-question"))
                continue
            if q["id"] in ids:findings.append(dict(severity="error",year=year,number=n,code="duplicate-id"))
            ids.add(q["id"])
            cs=q.get("choices",[])
            if len(cs)!=4 or not all(str(x).strip() for x in cs):
                findings.append(dict(severity="error",year=year,number=n,code="invalid-choices"))
            if q.get("answer") not in (0,1,2,3):
                findings.append(dict(severity="error",year=year,number=n,code="invalid-answer"))
            if not q.get("q") or not q.get("explanation"):
                findings.append(dict(severity="error",year=year,number=n,code="missing-text-or-explanation"))
            if q.get("field")!=("ストラテジ系" if n<=35 else "マネジメント系" if n<=55 else "テクノロジ系"):
                findings.append(dict(severity="error",year=year,number=n,code="wrong-field"))
            if key and 0<=q.get("answer",-1)<=3:
                if KANA[q["answer"]]!=key[n-1]:
                    findings.append(dict(severity="error",year=year,number=n,code="official-answer-mismatch",expected=key[n-1],actual=KANA[q["answer"]]))
                else:verified+=1
            if q.get("figureRequired") and not (q.get("figureUrl") or q.get("choiceFigures") or q.get("figureTables")):
                findings.append(dict(severity="warning",year=year,number=n,code="missing-required-figure"))
            if q.get("figureRequired") and not (q.get("figureUrl") or q.get("choiceFigures")):
                findings.append(dict(severity="warning",year=year,number=n,code="unverified-figure-visibility"))
            paths=[]
            paths+=([q["figureUrl"]] if q.get("figureUrl") else [])
            paths+=q.get("figureFiles",[])
            paths+=q.get("choiceFigures",[])
            for path in set(paths):
                if not (ROOT/path).is_file():
                    findings.append(dict(severity="error",year=year,number=n,code="missing-image-file",path=path))
            if q.get("choiceFigures") and len(q["choiceFigures"])!=4:
                findings.append(dict(severity="error",year=year,number=n,code="incomplete-option-figures"))
            if q.get("figureTables"):
                for table in q["figureTables"]:
                    if not table or any(not isinstance(row,list) for row in table):
                        findings.append(dict(severity="error",year=year,number=n,code="invalid-figure-table"))
            fingerprint=re.sub(r"\s+","",q["q"])
            fingerprints[fingerprint].append((year,n))
        score.append(dict(year=year,count=len(public),officialAnswerMatches=verified,officialAnswerReferenceAvailable=bool(key)))
    for refs in fingerprints.values():
        if len(refs)>1:
            findings.append(dict(severity="info",code="same-question-text-across-years",references=refs))
    summary={"publicQuestionCount":sum(x["count"] for x in score),"years":score,
             "errors":sum(x["severity"]=="error" for x in findings),
             "warnings":sum(x["severity"]=="warning" for x in findings),
             "findings":findings}
    return summary

if __name__=="__main__":
    result=check()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if result["errors"] else 0)

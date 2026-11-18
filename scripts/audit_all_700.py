#!/usr/bin/env python3
"""Data-level audit of all seven public-year question sets.

This does NOT certify fidelity to the IPA original, completeness of diagrams,
or correctness of original explanations. A passing exit code only certifies
structural invariants and explicitly enumerated text/table checks.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
YEARS=range(2020,2027)

def load(year):
    path=ROOT/("questions.js" if year==2025 else f"questions_{year}.js")
    text=path.read_text(encoding="utf-8")
    marker="window.QUESTIONS = " if year==2025 else f"window.QUESTIONS_{year} = "
    if marker not in text:
        raise AssertionError(f"{path}: unexpected JavaScript assignment")
    rows=json.loads(text.split(marker,1)[1].strip().removesuffix(";"))
    return [q for q in rows if q.get("year")==str(year)]

def main():
    errors=[]
    warnings=[]
    rows=[]
    for year in YEARS:
        questions=load(year)
        numbers=Counter(q.get("number") for q in questions)
        if len(questions)!=100: errors.append(f"{year}: {len(questions)} questions (expected 100)")
        for n in range(1,101):
            if numbers[n]!=1: errors.append(f"{year} Q{n}: number appears {numbers[n]} times")
        for q in questions:
            number=q.get("number")
            ident=f"{year}-Q{number}"
            opts=q.get("choices")
            if not isinstance(opts,list) or len(opts)!=4 or not all(isinstance(o,str) and o.strip() for o in opts):
                errors.append(f"{ident}: not four nonempty string options")
            if type(q.get("answer")) is not int or q["answer"] not in (0,1,2,3):
                errors.append(f"{ident}: answer index invalid")
            if not isinstance(q.get("q"),str) or not q["q"].strip():
                errors.append(f"{ident}: no stem")
            if not isinstance(q.get("explanation"),str) or not q["explanation"].strip():
                errors.append(f"{ident}: no explanation")
            tables=q.get("figureTables",[])
            for i,table in enumerate(tables):
                if not isinstance(table,list) or not table:
                    errors.append(f"{ident}: invalid table {i}"); continue
                widths={len(row) for row in table}
                if len(widths)>1: warnings.append(f"{ident}: table {i} unequal row widths")
                if any(not isinstance(row,list) for row in table):
                    errors.append(f"{ident}: invalid table row {i}")
            if q.get("figureRequired") and not (q.get("figureUrl") or q.get("figureTables") or q.get("choiceFigures") or q.get("choiceTables")):
                errors.append(f"{ident}: flagged required figure is absent")
            if "\ufffd" in (q.get("q","")+" ".join(opts or [])):
                errors.append(f"{ident}: unicode replacement marker")
            if re.search(r"e[ 　]+nd(?:if|for|while)\b",q.get("q",""),re.I):
                warnings.append(f"{ident}: suspicious split keyword")
            if isinstance(q.get("explanation"),str) and len(q["explanation"])<28:
                warnings.append(f"{ident}: short explanation ({len(q['explanation'])} characters)")
            rows.append({"year":year,"number":number,"id":q.get("id"),"fourOptions":isinstance(opts,list) and len(opts)==4,
                         "hasExplanation":bool(q.get("explanation")),"hasFigure":bool(q.get("figureUrl") or q.get("choiceFigures")),
                         "hasTable":bool(q.get("figureTables") or q.get("choiceTables")),
                         "officialTextExactMatchCertified":False,
                         "officialAnswerKeyDirectlyVerified":year>=2024,
                         "explanationSemanticReviewCertified":False})
    summary={"total":len(rows),"yearCounts":{str(y):sum(x["year"]==y for x in rows) for y in YEARS},
             "errors":errors,"warnings":warnings,
             "scope":"Static repository checks only; no assertion of original PDF word-for-word fidelity.",
             "rows":rows}
    target=ROOT/"data"/"700-question-audit-matrix.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="rows"},ensure_ascii=False,indent=2))
    raise SystemExit(1 if errors else 0)

if __name__=="__main__":
    main()

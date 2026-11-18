#!/usr/bin/env python3
"""Inventory content-level editorial risks; do not confuse an automated pass with
full comparison to the authoritative IPA original PDF.
"""
import json
import re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(y):
    txt=(ROOT/("questions.js" if y==2025 else f"questions_{y}.js")).read_text("utf-8")
    prefix="window.QUESTIONS = " if y==2025 else f"window.QUESTIONS_{y} = "
    return [q for q in json.loads(txt.split(prefix,1)[1].rsplit(";",1)[0]) if q.get("year")==str(y)]
def classify(q):
    issues=[]
    y=q["year"];n=q["number"]
    if not q.get("q"):issues.append("missing-question")
    if any(not str(x).strip() for x in q.get("choices",[])):issues.append("blank-choice")
    if len(q.get("choices",[]))!=4:issues.append("not-four-options")
    if "\r" in q.get("q",""):issues.append("carriage-return")
    if "\ufffd" in q.get("q","") or any("\ufffd" in x for x in q.get("choices",[])):issues.append("invalid-encoding")
    if "校閲後に追加" in q.get("explanation",""):issues.append("placeholder-explanation")
    if len(q.get("explanation",""))<24:issues.append("short-explanation")
    if q.get("figureRequired") and not(q.get("figureUrl") or q.get("choiceFigures") or q.get("figureTables")):issues.append("required-figure-unavailable")
    if q.get("figureRequired") and not(q.get("figureUrl") or q.get("choiceFigures")):issues.append("diagram-required-but-only-table")
    if q.get("figureTables"):
        for table in q["figureTables"]:
            if not table or len(table)<1:issues.append("empty-table")
    if q.get("choiceFigures") and len(q["choiceFigures"])!=4:issues.append("incomplete-choice-figures")
    if re.search(r"[a-zA-Z0-9]\s*÷\s*$",q.get("q","")):issues.append("truncated-expression")
    if y=="2025" and q.get("explanationStatus")=="prior-independent-explanation-needs-recheck-after-stem-restoration":
        issues.append("explanation-recheck-after-stem-restoration")
    if q.get("displayTextSource")!="ipa-pdf-verified":
        issues.append("ipa-original-text-not-certified")
    return issues

def main():
    rows=[]
    for y in range(2020,2027):
        for q in load(y):
            flags=classify(q)
            rows.append({"year":y,"number":q["number"],"id":q["id"],"flags":flags,
                         "hasFigure":bool(q.get("figureUrl") or q.get("choiceFigures")),
                         "hasTable":bool(q.get("figureTables") or q.get("choiceTables")),
                         "explanationPresent":bool(q.get("explanation"))})
    byIssue=Counter(issue for row in rows for issue in row["flags"])
    report={"total":len(rows),"issueCounts":dict(sorted(byIssue.items())),
            "issuesRequiringAttention":[row for row in rows if any(x not in
             ("ipa-original-text-not-certified","explanation-recheck-after-stem-restoration")
             for x in row["flags"])],
            "yearCounts":{str(y):sum(row["year"]==y for row in rows) for y in range(2020,2027)},
            "methodology":"Static field and content-risk checks only; NOT manual checking all 700 against original IPA PDFs."}
    (ROOT/"data"/"content-quality-inventory.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"total":report["total"],"issueCounts":report["issueCounts"],"attention":report["issuesRequiringAttention"][:30]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()

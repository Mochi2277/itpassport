#!/usr/bin/env python3
"""Replace paraphrased R07 question stems/choices with externally transcribed public questions.
Preserve question IDs, original pedagogical notes, and all 12 custom items.
Never claim exact IPA PDF verification; official key comparison applies to answer letters only.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/"questions.js"
stage=ROOT/"questions_2025_source.js"

def get(path,prefix):
    content=path.read_text(encoding="utf-8")
    return json.loads(content.split(prefix,1)[1].rsplit(";",1)[0])

def main():
    current=get(target,"window.QUESTIONS = ")
    source=get(stage,"window.QUESTIONS_2025 = ")
    originals=[q for q in current if q.get("year")=="2025"]
    if len(originals)==100 and all(q.get("displayTextSource")=="external-transcription-needs-ipa-pdf-review" for q in originals):
        print("SKIP: R07 already restored and edited; preserve the existing published dataset")
        return
    custom=[q for q in current if q.get("year")!="2025"]
    if len(originals)!=100 or len(source)!=100 or len(custom)!=12:
        raise RuntimeError(f"Unexpected counts old={len(originals)}, source={len(source)}, custom={len(custom)}")
    if any(q["number"]!=i+1 for i,q in enumerate(source)):
        raise RuntimeError("Question source not contiguous 1-100")
    result=[]
    changes=[]
    for before, after in zip(originals, source):
        if before["number"]!=after["number"] or before["id"]!=after["id"]:
            raise RuntimeError("Question ID or order mismatch")
        if before["answer"]!=after["answer"]:
            raise RuntimeError(f"Answer key mismatch in question {before['number']}: {before['answer']} vs {after['answer']}")
        q=dict(before)
        for field in ["q","displayText","choices","source","sourceUrl","answerSourceUrl",
                      "textTransportSource","figureTables","figureUrl","figureFiles","figureRequired",
                      "choiceFigures","figureCaption","figureAlt","extractionStatus","topic"]:
            q.pop(field,None)
            if field in after:q[field]=after[field]
        q["displayTextSource"]="external-transcription-needs-ipa-pdf-review"
        q["answerVerification"]="official-answer-key-compared"
        q["adapted"]=True
        q["explanationStatus"]="prior-independent-explanation-needs-recheck-after-stem-restoration"
        q["tip"]="IPA公式PDFも参照して設問条件と図表を確認してください。"
        if before.get("q")!=q.get("q") or before.get("choices")!=q.get("choices"):
            changes.append(q["number"])
        result.append(q)
    result.extend(custom)
    if len(result)!=112:raise RuntimeError("Unexpected output count")
    target.write_text("/* R07 100 questions restored from published HTML transcription; exact IPA PDF review pending. */\nwindow.QUESTIONS = "+json.dumps(result,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    report={"year":2025,"sourceQuestions":100,"changedQuestions":len(changes),
            "changedNumbers":changes,"customPreserved":len(custom),
            "officialAnswerMatches":100,
            "officialStemProofread":0,
            "explanationsRequireNewReview":100,
            "warning":"This process transcribes e-Words, not the authoritative IPA PDF byte-by-byte."}
    (ROOT/"data"/"2025-source-restoration-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()

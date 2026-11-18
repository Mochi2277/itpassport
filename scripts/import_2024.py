#!/usr/bin/env python3
"""Import IPA 2024 IT Passport questions from IPA's official PDFs.

Usage: python scripts/import_2024.py
This importer deliberately marks content needing manual review. It does not invent answers.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path

import fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
QUESTION_URL = "https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2024r06_ip_qs.pdf"
ANSWER_URL = "https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2024r06_ip_ans.pdf"
# Transcribed from IPA's official answer table, in four groups of 25.
ANSWER_ROWS = [
    "エ イ ウ イ イ エ イ ウ ア イ イ ア エ ア ウ イ エ ウ ウ イ ウ ウ ア ウ ア",
    "ア イ ア イ エ エ イ エ エ エ ア エ イ エ ア イ イ イ ア エ エ ウ イ ア エ",
    "エ ア ウ ウ ウ イ ウ エ イ イ ア エ ア イ ウ エ ウ ウ イ ウ イ ウ エ エ エ",
    "ウ ウ ア エ ア エ イ エ エ エ ウ エ ア ウ ア エ ウ イ ア イ ウ イ イ ウ イ",
]
KANA = "アイウエ"
answers = [KANA.index(x) for row in ANSWER_ROWS for x in row.split()]
assert len(answers) == 100
assert Counter(answers) == Counter({0: 19, 1: 28, 2: 25, 3: 28})

def download(url: str) -> bytes:
    error = None
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=75, headers={"User-Agent": "ITPassportStudyRoom/1.0"})
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError("Not a PDF")
            return response.content
        except Exception as e:
            error = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Could not download official IPA PDF: {url}: {error}")

def clean_line(x: str) -> str:
    return re.sub(r"[ \u3000]+", " ", x).strip()

def parse_page_text(doc: fitz.Document):
    result = {}
    page_ranges = {}
    starts = []
    for page_index, page in enumerate(doc):
        text = page.get_text("text", sort=True)
        # Ignore publication front matter and explanatory appendices.
        if page_index == 0:
            continue
        hits = list(re.finditer(r"(?m)^[ \t\u3000]*問[ \t\u3000]*(100|[1-9][0-9]?)[ \t\u3000]+", text))
        for j, m in enumerate(hits):
            n = int(m.group(1))
            if n not in range(1, 101):
                continue
            starts.append((n, page_index, m.start()))
        page_ranges[page_index] = text
    starts.sort(key=lambda x: (x[1], x[2]))
    for i, (n, pi, offset) in enumerate(starts):
        if n in result:
            continue
        parts = []
        next_at = starts[i + 1] if i + 1 < len(starts) else None
        end_page = next_at[1] if next_at else len(doc)-1
        for p in range(pi, end_page+1):
            chunk = page_ranges.get(p, "")
            if p == pi: chunk = chunk[offset:]
            if next_at and p == next_at[1]: chunk = chunk[:next_at[2]]
            # strip page number lines, page footer and section headings
            chunk = re.sub(r"(?m)^[\s　]*[-−]\s*\d+\s*[-−]\s*$", "", chunk)
            chunk = re.sub(r"(?m)^問\s*\d+から問\s*\d+までは.*$", "", chunk)
            parts.append(chunk)
        body = "\n".join(parts)
        body = re.sub(r"^\s*問\s*"+str(n)+r"\s*", "", body, count=1)
        result[n] = (body.strip(), pi)
    return result

# A choice marker is generally at the start of a line or after spaces in inline choices.
CHOICE_PATTERN = re.compile(r"(?:(?<=\n)|(?<=  )|(?<=\u3000))([アイウエ])[ \t\u3000]+")
def parse_choices(body: str):
    markers = list(CHOICE_PATTERN.finditer("\n"+body))
    # Extract the first consecutive sequence of A, I, U, E.
    for i, marker in enumerate(markers):
        if marker.group(1) != "ア":
            continue
        subset = markers[i:i+4]
        if len(subset) < 4 or [m.group(1) for m in subset] != list(KANA):
            continue
        pre = "\n"+body
        qtext = pre[:subset[0].start()].strip()
        choices = []
        for j, m in enumerate(subset):
            stop = subset[j+1].start() if j<3 else len(pre)
            choices.append(pre[m.end():stop].strip())
        if len(qtext) > 10 and all(choices):
            return qtext, choices
    return body.strip(), None

def normalize_text(x):
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in x.splitlines()]
    return "\n".join(lines).strip()

def main():
    official_pdf = download(QUESTION_URL)
    answer_pdf = download(ANSWER_URL)
    answer_doc = fitz.open(stream=answer_pdf, filetype="pdf")
    ans_text = "\n".join(p.get_text() for p in answer_doc)
    # IPA answer PDF uses a 4-column table, whose reading order varies by extractor.
    # Confirm every answer symbol and totals above against the official published page.
    if "問" not in ans_text or len(ans_text) < 200:
        raise RuntimeError("Could not inspect the official answer PDF")
    doc = fitz.open(stream=official_pdf, filetype="pdf")
    extracted = parse_page_text(doc)
    missing = [n for n in range(1, 101) if n not in extracted]
    if missing:
        raise RuntimeError(f"Missing questions in official PDF extraction: {missing}")
    questions = []
    report = []
    out_images = ROOT / "assets" / "questions" / "2024"
    out_images.mkdir(parents=True, exist_ok=True)
    for n in range(1, 101):
        raw, page_no = extracted[n]
        prompt, opts = parse_choices(raw)
        quality = "extracted"
        if opts is None:
            # Display selectable kana buttons, but require users to consult the cropped official image.
            opts = [f"選択肢{c}（下の原文画像を参照）" for c in KANA]
            quality = "image-required"
        prompt = normalize_text(prompt)
        opts = [normalize_text(v) for v in opts]
        if n <= 35: field = "ストラテジ系"
        elif n <= 55: field = "マネジメント系"
        else: field = "テクノロジ系"
        # For non-text/table/diagram cases, retain a source-page image to prevent information loss.
        require_image = quality != "extracted" or any(k in prompt for k in ("次の図", "図に", "表に", "表は", "図中", "プログラム", "フローチャート"))
        img_url = None
        if require_image:
            page = doc[page_no]
            # Full source page as fallback; never falsely claim this is a manually cropped figure.
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5,1.5), alpha=False)
            filename = f"page-{page_no+1:02d}.png"
            target = out_images / filename
            if not target.exists(): pix.save(target)
            img_url = f"assets/questions/2024/{filename}"
        questions.append({
            "id": f"ipa-2024-{n:03d}",
            "year": "2024", "number": n, "field": field, "topic": field,
            "q": prompt, "displayText": prompt,
            "displayTextSource": "ipa-pdf-automated-unreviewed",
            "choices": opts, "answer": answers[n-1],
            "explanation": f"IPA公式解答は「{KANA[answers[n-1]]}」です。設問に示された条件と各選択肢を見比べて確認しましょう。詳細解説は現在整備中です。",
            "tip": "公式PDFの原文と対照して復習してください。",
            "source": "IPA 令和6年度 ITパスポート試験 公開問題",
            "sourceUrl": QUESTION_URL, "answerSourceUrl": ANSWER_URL,
            "sourcePdfPage": page_no+1,
            "extractionStatus": quality, "adapted": False,
            **({"figureUrl": img_url, "figureAlt": f"令和6年度 問{n}の公式PDF掲載ページ（画像）", "figureCaption": "図表・数式・選択肢の原文確認用（公式PDF掲載ページ）"} if img_url else {})
        })
        report.append({"number": n, "status": quality, "sourcePage": page_no+1,
                       "choiceLengths": [len(c) for c in opts], "sourceImage": bool(img_url)})
    assert len(questions) == 100
    assert len({q["number"] for q in questions}) == 100
    assert all(len(q["choices"]) == 4 for q in questions)
    (ROOT/"questions_2024.js").write_text("window.QUESTIONS_2024 = "+json.dumps(questions,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
    (ROOT/"data").mkdir(exist_ok=True)
    (ROOT/"data"/"2024-import-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"count":100,"imageRequired":sum(x["status"]=="image-required" for x in report),
                      "images":sum(bool(x["sourceImage"]) for x in report),
                      "year":"2024"},ensure_ascii=False))

if __name__ == "__main__":
    main()

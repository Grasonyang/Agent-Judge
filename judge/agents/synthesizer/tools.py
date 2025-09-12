import os
from datetime import datetime
from typing import Dict, Any, List

# ===== 將 final_report_json → Markdown，並寫檔 =====
def render_final_report_md(final_report: Dict[str, Any], out_dir: str = "outputs") -> Dict[str, Any]:
    """
    將 Synthesizer 產生的 FinalReport(JSON) 轉為 Markdown，並寫檔。
    回傳 { "path": <檔案路徑>, "bytes": <大小> }
    """
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"final_report_{ts}.md"
    fpath = os.path.join(out_dir, fname)

    fr = final_report
    lines: List[str] = []
    lines.append(f"# 最終分析報告｜{fr.get('topic','')}\n")
    if fr.get("jury_score") is not None:
        lines.append(f"> **Jury 總分**：{fr['jury_score']}｜**摘要**：{fr.get('jury_brief','')}\n")
    lines.append(f"**總結**：{fr.get('overall_assessment','')}\n")

    # 關鍵證據
    lines.append("## 關鍵證據（Digest）")
    for i, e in enumerate(fr.get("evidence_digest", []), 1):
        lines.append(f"{i}. {e}")

    # 立場總結
    lines.append("\n## 各方重點（Stake Summaries）")
    for s in fr.get("stake_summaries", []):
        lines.append(f"### {s.get('side','(unknown)')}")
        lines.append(f"- **核心主張**：{s.get('thesis','')}")
        sp = s.get("strongest_points", [])
        if sp:
            lines.append("- **最強論點**：")
            for p in sp: lines.append(f"  - {p}")
        wk = s.get("weaknesses", [])
        if wk:
            lines.append("- **主要缺口**：")
            for w in wk: lines.append(f"  - {w}")

    # 核心爭點
    lines.append("\n## 核心爭點（Contentions）")
    for c in fr.get("key_contentions", []):
        lines.append(f"### {c.get('question','')}")
        if c.get("what_advocates_say"):
            lines.append("- 正方認為：")
            for a in c["what_advocates_say"]:
                lines.append(f"  - {a}")
        if c.get("what_skeptics_say"):
            lines.append("- 反方認為：")
            for s in c["what_skeptics_say"]:
                lines.append(f"  - {s}")
        if c.get("what_devil_pushed"):
            lines.append("- 極端質疑者推進：")
            for d in c["what_devil_pushed"]:
                lines.append(f"  - {d}")
        lines.append(f"- **目前狀態**：{c.get('status','')}\n")

    # 風險與未決
    if fr.get("risks"):
        lines.append("## 風險與緩解")
        for r in fr["risks"]:
            lines.append(f"- **{r.get('name','')}**：{r.get('why','')}"
                         f"{'｜緩解：'+r['mitigation'] if r.get('mitigation') else ''}")
    if fr.get("open_questions"):
        lines.append("\n## 未決問題")
        for q in fr["open_questions"]:
            lines.append(f"- {q}")

    # 附錄
    if fr.get("appendix_links"):
        lines.append("\n## 附錄連結")
        for l in fr["appendix_links"]:
            lines.append(f"- {l}")

    md = "\n".join(lines) + "\n"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(md)
    return {"path": fpath, "bytes": len(md)}

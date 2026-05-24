import argparse
import json
import os
import re
import time
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any, Dict, List

import pandas as pd
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_CSV = BASE_DIR / "transcription_result" / "transcripts.csv"
KB_DIR = BASE_DIR / "previous_knowledge_base"
OUT_DIR = BASE_DIR / "processed_knowledge_base"

PRODUCT_CATEGORY = "家庭K歌与影音一体机"
K_TOKEN_BASE_URL = "https://ai.ktokenhub.app"
K_TOKEN_API_KEY = os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
GENERATION_MODEL = "gpt-5.4"


def clean_text(value: Any) -> str:
    """清洗文本内容：处理空值、去除多余空白字符，并返回适合后续分析的标准字符串。"""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def llm_client() -> OpenAI:
    """创建并返回 OpenAI 客户端：优先读取 K_TOKEN_API_KEY，其次读取 OPENAI_API_KEY。"""
    if not K_TOKEN_API_KEY:
        raise RuntimeError("请设置环境变量 K_TOKEN_API_KEY 或 OPENAI_API_KEY。")
    return OpenAI(api_key=K_TOKEN_API_KEY, base_url=K_TOKEN_BASE_URL)


def safe_json_loads(text: str) -> Dict[str, Any]:
    """安全解析 LLM 返回的 JSON 文本：自动去除 Markdown 代码块并提取 JSON 主体。"""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean).strip()
        clean = re.sub(r"```$", "", clean).strip()
    match = re.search(r"\{.*\}", clean, re.S)
    if match:
        clean = match.group(0)
    return json.loads(clean)


def llm_tag_case(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """调用大模型对单条视频脚本进行结构化标签分析，包括钩子、卖点、场景、CTA 等创意标签。"""
    transcript = clean_text(raw_record["transcript_text"])
    high_score_reasons = [item["reason"] for item in raw_record["high_score_indicators"]]
    prompt = f"""
你是短视频广告脚本结构化标注专家。请基于口播文本和高分原因，为一个家庭K歌与影音一体机爆款视频做开放式创作标签标注。
只输出 JSON，不要 Markdown，不要解释。

视频ID：{raw_record['video_id']}
产品类型：{PRODUCT_CATEGORY}

口播文本：
{transcript[:5000]}

高分指标与原因：
{json.dumps(raw_record['high_score_indicators'], ensure_ascii=False)}

请输出严格 JSON，字段如下：
{{
  "video_id": "{raw_record['video_id']}",
  "product_category": "{PRODUCT_CATEGORY}",
  "best_for": ["根据证据自由填写，例如 completion_rate、roi、balanced，不确定可写 unknown"],
  "script_pattern_free": "用一句短语概括脚本结构，不要受固定枚举限制",
  "hook_type_free": ["自由标签，描述开头钩子类型"],
  "story_type_free": ["自由标签，描述内容叙事/呈现类型"],
  "persona_free": ["自由标签，描述出镜/叙述身份或口吻"],
  "scene_free": ["自由标签，描述使用或拍摄场景"],
  "product_display_free": ["自由标签，描述产品如何被展示"],
  "pain_points_free": ["自由标签，描述用户痛点"],
  "selling_points_free": ["自由标签，描述产品卖点"],
  "proof_methods_free": ["自由标签，描述如何证明卖点"],
  "cta_type_free": ["自由标签，描述转化引导方式"],
  "tag_confidence": {{
    "overall": 0.0,
    "hook_type_free": 0.0,
    "story_type_free": 0.0,
    "product_display_free": 0.0,
    "proof_methods_free": 0.0,
    "cta_type_free": 0.0
  }},
  "segments": [
    {{
      "stage": "hook/setup/proof/value/cta",
      "estimated_time": "例如 0-3s",
      "voiceover": "对应口播原文片段，尽量短",
      "function": "这个片段在脚本中的作用",
      "tags": ["片段标签"]
    }}
  ],
  "source_evidence": {{
    "transcript_excerpt": "支持标签判断的口播摘录",
    "high_score_reasons": {json.dumps(high_score_reasons, ensure_ascii=False)}
  }}
}}

要求：
1. 标签必须基于证据，不要臆造视频中没有的信息。
2. 不要使用预设枚举思维；请用最贴近该视频的自然语言短标签。
3. 数组字段可以多选，但每个字段最多 5 个标签。
4. tag_confidence 使用 0-1 小数，表示证据充分程度。
5. segments 至少包含 hook、proof、cta 三类；如果原文没有明确 CTA，请在 cta_type_free 写“弱转化引导/未明确”。
"""
    response = llm_client().responses.create(model=GENERATION_MODEL, input=prompt)
    text = getattr(response, "output_text", None) or str(response)
    data = safe_json_loads(text)
    data["tagger"] = "llm"
    data["model"] = GENERATION_MODEL
    return data


def build_layers(limit: int = 0, sleep_sec: float = 0.2) -> Dict[str, int]:
    """构建知识库主流程：读取转写结果与高分指标，调用 LLM 生成结构化创意标签并输出文件。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    transcripts = pd.read_csv(TRANSCRIPTS_CSV)
    transcripts = transcripts[transcripts["status"].eq("success")].copy()
    transcripts["join_id"] = transcripts["video_id"].astype(str).str.extract(r"^(\d+)")[0]

    all_details = pd.read_csv(KB_DIR / "all_high_score_details.csv")
    all_details["join_id"] = all_details["video_id"].astype(str)
    completion_details = pd.read_csv(KB_DIR / "completion_rate_high_score_details.csv")
    completion_details["join_id"] = completion_details["video_id"].astype(str)
    roi_details = pd.read_csv(KB_DIR / "roi_high_score_details.csv")
    roi_details["join_id"] = roi_details["video_id"].astype(str)

    if limit > 0:
        transcripts = transcripts.head(limit)

    records = []
    structured = []
    errors = []
    for idx, (_, row) in enumerate(transcripts.iterrows(), 1):
        join_id = str(row["join_id"])
        transcript = clean_text(row["transcript_text"])
        detail_rows = all_details[all_details["join_id"].eq(join_id)]
        completion_rows = completion_details[completion_details["join_id"].eq(join_id)]
        roi_rows = roi_details[roi_details["join_id"].eq(join_id)]

        high_score_indicators = [
            {
                "indicator_id": str(r["indicator_id"]),
                "indicator_name": str(r["indicator_name"]),
                "score": int(r["score"]),
                "reason": clean_text(r["reason"]),
            }
            for _, r in detail_rows.iterrows()
        ]
        raw_record = {
            "video_id": join_id,
            "source_video_id": row["video_id"],
            "file_name": row["file_name"],
            "source_path": row["source_path"],
            "product_category": PRODUCT_CATEGORY,
            "transcript_text": transcript,
            "high_score_indicators": high_score_indicators,
            "completion_indicator_count": int(len(completion_rows)),
            "roi_indicator_count": int(len(roi_rows)),
        }
        records.append(raw_record)

        try:
            tagged = llm_tag_case(raw_record)
            tagged["best_for_from_metrics"] = infer_best_for(len(completion_rows), len(roi_rows))
            structured.append(tagged)
            print(f"[llm-tag] {idx}/{len(transcripts)} ok video_id={join_id}", flush=True)
        except Exception as exc:
            error_record = {
                "video_id": join_id,
                "product_category": PRODUCT_CATEGORY,
                "tagger": "llm",
                "status": "error",
                "error": str(exc),
                "source_evidence": {
                    "transcript_excerpt": transcript[:500],
                    "high_score_reasons": [item["reason"] for item in high_score_indicators],
                },
            }
            structured.append(error_record)
            errors.append(error_record)
            print(f"[llm-tag] {idx}/{len(transcripts)} error video_id={join_id}: {exc}", flush=True)
        time.sleep(sleep_sec)

    raw_path = OUT_DIR / "raw_evidence_cases.jsonl"
    structured_path = OUT_DIR / "structured_creative_cases.jsonl"
    raw_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    structured_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in structured), encoding="utf-8")
    inventory_path = OUT_DIR / "free_tag_inventory.json"
    inventory_path.write_text(
        json.dumps(build_free_tag_inventory(structured), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "product_category": PRODUCT_CATEGORY,
        "raw_evidence_cases": str(raw_path),
        "structured_creative_cases": str(structured_path),
        "free_tag_inventory": str(inventory_path),
        "raw_count": len(records),
        "structured_count": len(structured),
        "error_count": len(errors),
        "tagger": "llm",
        "model": GENERATION_MODEL,
        "taxonomy_mode": "open_free_tags_then_cluster",
        "join_note": "video_id is the numeric prefix shared by transcripts and knowledge_base files",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"raw_count": len(records), "structured_count": len(structured), "error_count": len(errors)}


def build_free_tag_inventory(structured_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """统计所有自由标签的出现频次，并生成标签词库及示例视频映射。"""
    tag_fields = [
        "best_for",
        "hook_type_free",
        "story_type_free",
        "persona_free",
        "scene_free",
        "product_display_free",
        "pain_points_free",
        "selling_points_free",
        "proof_methods_free",
        "cta_type_free",
    ]
    counters: Dict[str, Counter] = {field: Counter() for field in tag_fields}
    examples: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

    for record in structured_records:
        if record.get("status") == "error":
            continue
        video_id = str(record.get("video_id", ""))
        for field in tag_fields:
            values = record.get(field, [])
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            for value in values:
                value = clean_text(value)
                if not value:
                    continue
                counters[field][value] += 1
                if len(examples[field][value]) < 5:
                    examples[field][value].append(video_id)

    return {
        field: [
            {"tag": tag, "count": count, "example_video_ids": examples[field][tag]}
            for tag, count in counter.most_common()
        ]
        for field, counter in counters.items()
    }


def infer_best_for(completion_count: int, roi_count: int) -> List[str]:
    """根据完播率与 ROI 指标推断该视频更适合的优化方向。"""
    tags = []
    if completion_count > 0:
        tags.append("completion_rate")
    if roi_count > 0:
        tags.append("roi")
    return tags or ["balanced"]


def main():
    """程序主入口：解析命令行参数并启动知识库构建流程。"""
    global OUT_DIR
    parser = argparse.ArgumentParser(description="Build two-layer script generation knowledge base")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--limit", type=int, default=0, help="Only tag the first N successful transcripts. Use 0 for all.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between LLM tagging calls.")
    args = parser.parse_args()
    OUT_DIR = Path(args.out_dir)
    result = build_layers(limit=args.limit, sleep_sec=args.sleep)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()

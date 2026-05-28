import argparse
import json
import os
import re
import shutil
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# TypedDict extra_items patch (MUST be before langgraph import)
try:
    from typing_extensions import _TypedDictMeta
    _original_typeddict_new = _TypedDictMeta.__new__
    
    def _patched_typeddict_new(mcls, name, bases, namespace, **kwargs):
        kwargs.pop('extra_items', None)
        kwargs.pop('closed', None)
        return _original_typeddict_new(mcls, name, bases, namespace, **kwargs)
    
    _TypedDictMeta.__new__ = staticmethod(_patched_typeddict_new)
except: pass

from typing_extensions import TypedDict

import faiss
import numpy as np
import pandas as pd
from langgraph.graph import END, StateGraph
from openai import OpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR
SCRIPT_AGENT_ROOT = AGENT_DIR.parent
PROJECT_ROOT = SCRIPT_AGENT_ROOT.parent
BASE_DIR = PROJECT_ROOT
TRANSCRIPTS_CSV = SCRIPT_AGENT_ROOT / "transcription_result" / "transcripts.csv"
KB_DIR = SCRIPT_AGENT_ROOT / "knowledge_base" / "previous"
PROCESSED_KB_DIR = SCRIPT_AGENT_ROOT / "knowledge_base" / "rag"
EVALUATION_STANDARD_PATH = SCRIPT_AGENT_ROOT / "knowledge_base" / "evaluation_standard.json"
LOCAL_VECTOR_DIR = SCRIPT_AGENT_ROOT / "vector_db" / "local_vector_fallback"
FAISS_VECTOR_DIR = SCRIPT_AGENT_ROOT / "vector_db"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

K_TOKEN_BASE_URL = os.getenv("K_TOKEN_BASE_URL", "https://ai.ktokenhub.app")
K_TOKEN_API_KEY = os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
GENERATION_MODEL = "gpt-5.4"
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-v4"
VECTOR_BACKEND = "faiss"


class ScriptAgentState(TypedDict, total=False):
    """LangGraph 共享状态定义：记录用户需求、检索结果、策划案、脚本、评分、修复证据和执行轨迹。"""
    user_input: str
    objective: str
    duration_sec: int
    characters: List[Dict[str, Any]]
    product_selling_points: str
    parsed_brief: Dict[str, Any]
    retrieved_cases: List[Dict[str, Any]]
    retrieved_fragments: List[Dict[str, Any]]
    strategy_rules: List[Dict[str, Any]]
    planning: Dict[str, Any]
    draft_script: Dict[str, Any]
    evaluation: Dict[str, Any]
    repair_evidence: List[Dict[str, Any]]
    final_script: Dict[str, Any]
    final_output: Dict[str, Any]
    trace: List[str]


def _clip(text: Any, n: int = 800) -> str:
    """清洗并截断文本：将任意输入转为字符串、压缩空白字符，并限制最大长度，便于放入提示词或向量文档。"""
    text = "" if pd.isna(text) else str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[:n].rstrip() + "..."


def _safe_json_loads(text: str) -> Any:
    """解析模型返回的 JSON：自动去除 Markdown 代码块，提取 JSON 对象或数组后再反序列化。"""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean).strip()
        clean = re.sub(r"```$", "", clean).strip()
    match = re.search(r"(\{.*\}|\[.*\])", clean, re.S)
    if match:
        clean = match.group(1)
    return json.loads(clean)


def generation_client() -> OpenAI:
    """创建文本生成模型客户端：优先读取 K_TOKEN_API_KEY，其次读取 OPENAI_API_KEY。"""
    if not K_TOKEN_API_KEY:
        raise RuntimeError("请设置环境变量 K_TOKEN_API_KEY 或 OPENAI_API_KEY。")
    return OpenAI(api_key=K_TOKEN_API_KEY, base_url=K_TOKEN_BASE_URL)


def embedding_client() -> OpenAI:
    """创建向量模型客户端：读取 DASHSCOPE_API_KEY 环境变量。"""
    if not DASHSCOPE_API_KEY:
        raise RuntimeError("请设置环境变量 DASHSCOPE_API_KEY。")
    return OpenAI(api_key=DASHSCOPE_API_KEY, base_url=EMBEDDING_BASE_URL)


def embed_texts(client: OpenAI, texts: List[str], batch_size: int = 10) -> List[List[float]]:
    """批量生成文本向量：调用 embedding 模型，校验向量有效性，并进行归一化处理。"""
    vectors: List[List[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in response.data:
            vector = np.asarray(item.embedding, dtype=np.float32)
            if not np.isfinite(vector).all():
                raise ValueError("Embedding contains NaN or Inf values.")
            norm = float(np.linalg.norm(vector))
            if norm <= 1e-12:
                raise ValueError("Embedding norm is zero.")
            vectors.append((vector / norm).astype(float).tolist())
        time.sleep(0.1)
    return vectors


def llm_json(prompt: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """调用生成模型并解析 JSON：失败时可返回 fallback，同时保留原始模型输出便于排查。"""
    client = generation_client()
    response = client.responses.create(model=GENERATION_MODEL, input=prompt)
    text = getattr(response, "output_text", None) or str(response)
    try:
        return _safe_json_loads(text)
    except Exception:
        if fallback is not None:
            fallback["raw_model_output"] = text
            return fallback
        raise


def load_evaluation_standard() -> Dict[str, Any]:
    """读取完整内容评价标准库 JSON 文件，供脚本评分节点使用。"""
    candidates = [
        EVALUATION_STANDARD_PATH,
        SCRIPT_AGENT_ROOT / "knowledge_base" / "evaluation_standard.json",
        BASE_DIR / "script_agent" / "knowledge_base" / "evaluation_standard.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"找不到内容评价标准库，已检查：\n{searched}")


def compact_evaluation_standard() -> Dict[str, Any]:
    """压缩评价标准库：只保留评分所需的维度、指标、描述和评分规则，减少提示词长度。"""
    framework = load_evaluation_standard()["evaluation_framework"]
    compact = {
        "name": framework.get("name"),
        "version": framework.get("version"),
        "score_range": framework.get("score_range"),
        "dimensions": [],
    }
    for dim in framework.get("dimensions", []):
        compact["dimensions"].append(
            {
                "dimension_id": dim.get("dimension_id"),
                "dimension_name": dim.get("dimension_name"),
                "description": dim.get("description"),
                "indicators": [
                    {
                        "indicator_id": ind.get("indicator_id"),
                        "indicator_name": ind.get("indicator_name"),
                        "description": ind.get("description"),
                        "scoring_criteria": ind.get("scoring_criteria"),
                    }
                    for ind in dim.get("indicators", [])
                ],
            }
        )
    return compact


def load_source_tables() -> Dict[str, Any]:
    """加载原始知识库表格和策略规则：包括转写文本、高分指标明细、完播率和 ROI 规则。"""
    transcripts = pd.read_csv(TRANSCRIPTS_CSV)
    transcripts = transcripts[transcripts["status"].eq("success")].copy()
    transcripts["join_id"] = transcripts["video_id"].astype(str).str.extract(r"^(\d+)")[0]

    all_details = pd.read_csv(KB_DIR / "all_high_score_details.csv")
    all_details["join_id"] = all_details["video_id"].astype(str)
    completion_details = pd.read_csv(KB_DIR / "completion_rate_high_score_details.csv")
    completion_details["join_id"] = completion_details["video_id"].astype(str)
    roi_details = pd.read_csv(KB_DIR / "roi_high_score_details.csv")
    roi_details["join_id"] = roi_details["video_id"].astype(str)

    completion_rules = json.loads((KB_DIR / "completion_rate_knowledge_base.json").read_text(encoding="utf-8"))
    roi_rules = json.loads((KB_DIR / "roi_knowledge_base.json").read_text(encoding="utf-8"))

    return {
        "transcripts": transcripts,
        "all_details": all_details,
        "completion_details": completion_details,
        "roi_details": roi_details,
        "completion_rules": completion_rules,
        "roi_rules": roi_rules,
    }


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """读取 JSONL 文件：逐行解析为字典列表，用于加载处理后的案例、片段和标签数据。"""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def processed_kb_is_ready() -> bool:
    """检查处理后的知识库是否已生成：判断结构化案例和原始证据 JSONL 是否同时存在。"""
    return (
        (PROCESSED_KB_DIR / "structured_creative_cases.jsonl").exists()
        and (PROCESSED_KB_DIR / "raw_evidence_cases.jsonl").exists()
    )


def _json_text(value: Any, max_chars: int = 1600) -> str:
    """将任意对象转为中文友好的 JSON 字符串，并按长度截断以适配提示词和向量文档。"""
    return _clip(json.dumps(value, ensure_ascii=False), max_chars)


def normalize_tag_dimension_name(name: Any) -> str:
    """去掉内部打标字段里的 free 后缀，让向量库中的维度命名更容易理解。"""
    return str(name).replace("_free", "")


def build_processed_vector_documents() -> Dict[str, List[Dict[str, Any]]]:
    """基于处理后的知识库构造向量文档：生成案例、脚本片段和策略规则三类检索材料。"""
    structured_cases = load_jsonl(PROCESSED_KB_DIR / "structured_creative_cases.jsonl")
    raw_cases = load_jsonl(PROCESSED_KB_DIR / "raw_evidence_cases.jsonl")
    raw_by_id = {str(item.get("video_id")): item for item in raw_cases}

    video_cases: List[Dict[str, Any]] = []
    fragments: List[Dict[str, Any]] = []

    for case in structured_cases:
        video_id = str(case.get("video_id", ""))
        raw = raw_by_id.get(video_id, {})
        transcript = raw.get("transcript_text") or case.get("source_evidence", {}).get("transcript_excerpt", "")
        high_score_indicators = raw.get("high_score_indicators", [])
        best_for = case.get("best_for", [])
        if not isinstance(best_for, list):
            best_for = [str(best_for)]

        case_doc = "\n".join(
            [
                f"product_category: {case.get('product_category', '')}",
                f"video_id: {video_id}",
                f"best_for: {_json_text(best_for, 300)}",
                f"script_pattern: {case.get('script_pattern_free', '')}",
                f"hook_type: {_json_text(case.get('hook_type_free', []), 500)}",
                f"story_type: {_json_text(case.get('story_type_free', []), 500)}",
                f"persona: {_json_text(case.get('persona_free', []), 500)}",
                f"scene: {_json_text(case.get('scene_free', []), 500)}",
                f"product_display: {_json_text(case.get('product_display_free', []), 700)}",
                f"pain_points: {_json_text(case.get('pain_points_free', []), 700)}",
                f"selling_points: {_json_text(case.get('selling_points_free', []), 700)}",
                f"proof_methods: {_json_text(case.get('proof_methods_free', []), 700)}",
                f"cta_type: {_json_text(case.get('cta_type_free', []), 500)}",
                f"segments: {_json_text(case.get('segments', []), 2200)}",
                f"transcript_excerpt: {_clip(transcript, 1800)}",
                f"high_score_indicators: {_json_text(high_score_indicators, 1400)}",
            ]
        )
        video_cases.append(
            {
                "id": f"processed_case_{video_id}",
                "document": case_doc,
                "metadata": {
                    "video_id": video_id,
                    "doc_type": "processed_video_case",
                    "best_for": ",".join(map(str, best_for)),
                    "segment_count": len(case.get("segments", []) or []),
                    "indicator_count": len(high_score_indicators),
                },
            }
        )

        target_labels = sorted(set(map(str, best_for + ["all"])))
        target_text = ",".join(target_labels)
        for seg_idx, segment in enumerate(case.get("segments", []) or []):
            stage = str(segment.get("stage", "")).lower() or "segment"
            segment_doc = "\n".join(
                [
                    f"video_id: {video_id}",
                    f"best_for: {target_text}",
                    "fragment_source: structured_segment",
                    f"stage: {stage}",
                    f"estimated_time: {segment.get('estimated_time', '')}",
                    f"voiceover: {segment.get('voiceover', '')}",
                    f"function: {segment.get('function', '')}",
                    f"tags: {_json_text(segment.get('tags', []), 500)}",
                    f"case_pattern: {case.get('script_pattern_free', '')}",
                ]
            )
            fragments.append(
                {
                    "id": f"processed_segment_{video_id}_{seg_idx}",
                    "document": segment_doc,
                    "metadata": {
                        "video_id": video_id,
                        "target": "all",
                        "fragment_type": stage,
                        "indicator_id": "",
                        "indicator_name": "",
                        "score": 6,
                    },
                }
            )

        for ind_idx, indicator in enumerate(high_score_indicators):
            score = int(indicator.get("score", 0) or 0)
            indicator_doc = "\n".join(
                [
                    f"video_id: {video_id}",
                    f"best_for: {target_text}",
                    "fragment_source: high_score_indicator",
                    f"indicator: {indicator.get('indicator_id', '')} {indicator.get('indicator_name', '')}",
                    f"score: {score}",
                    f"reason: {indicator.get('reason', '')}",
                    f"transcript_excerpt: {_clip(transcript, 900)}",
                ]
            )
            fragments.append(
                {
                    "id": f"processed_indicator_{video_id}_{indicator.get('indicator_id', '')}_{ind_idx}",
                    "document": indicator_doc,
                    "metadata": {
                        "video_id": video_id,
                        "target": "all",
                        "fragment_type": "indicator",
                        "indicator_id": str(indicator.get("indicator_id", "")),
                        "indicator_name": str(indicator.get("indicator_name", "")),
                        "score": score,
                    },
                }
            )

    rules: List[Dict[str, Any]] = []
    inventory_path = PROCESSED_KB_DIR / "free_tag_inventory.json"
    if inventory_path.exists():
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        for key, values in inventory.items():
            if not isinstance(values, list):
                continue
            dimension_name = normalize_tag_dimension_name(key)
            rules.append(
                {
                    "id": f"processed_tag_inventory_{dimension_name}",
                    "document": f"tag_dimension: {dimension_name}\ntop_tags: {_json_text(values[:20], 2600)}",
                    "metadata": {"target": "all", "rule_type": "tag_inventory", "dimension": dimension_name},
                }
            )

    return {"video_cases": video_cases, "script_fragments": fragments, "strategy_rules": rules}


def infer_fragment_type(indicator_name: str) -> str:
    """根据指标名称推断脚本片段类型，如 hook、setup、cta、retention 或 proof。"""
    name = str(indicator_name).lower()
    if "hook" in name or "0-3" in name:
        return "hook"
    if "setup" in name or "铺垫" in name or "信任" in name:
        return "setup"
    if "cta" in name or "互动" in name or "引导" in name:
        return "cta"
    if "悬念" in name or "反差" in name:
        return "retention"
    if "产品" in name or "颜值" in name or "安装" in name or "展示" in name:
        return "proof"
    return "proof"


def rule_docs(rule_json: Dict[str, Any], target: str) -> List[Dict[str, Any]]:
    """将策略规则 JSON 转为可向量化文档：提取总结、推荐策略和跨指标洞察。"""
    docs = []
    summary = rule_json.get("summary", {})
    if summary:
        docs.append(
            {
                "id": f"rule_{target}_summary",
                "document": f"{summary.get('core_insight', '')}\n{summary.get('key_finding', '')}",
                "metadata": {"target": target, "rule_type": "summary"},
            }
        )
    recommendations = rule_json.get("content_strategy_recommendations", [])
    if isinstance(recommendations, list):
        for idx, item in enumerate(recommendations):
            docs.append(
                {
                    "id": f"rule_{target}_recommendation_{idx}",
                    "document": str(item),
                    "metadata": {"target": target, "rule_type": "recommendation"},
                }
            )
    insights = rule_json.get("cross_indicator_insights", {})
    docs.append(
        {
            "id": f"rule_{target}_cross_insights",
            "document": json.dumps(insights, ensure_ascii=False),
            "metadata": {"target": target, "rule_type": "cross_indicator_insights"},
        }
    )
    return docs


def build_vector_documents() -> Dict[str, List[Dict[str, Any]]]:
    """构建向量库文档入口：优先使用处理后知识库，否则回退到原始转写和高分指标表。"""
    if processed_kb_is_ready():
        return build_processed_vector_documents()

    data = load_source_tables()
    transcripts = data["transcripts"]
    all_details = data["all_details"]

    grouped = all_details.groupby("join_id").agg(
        indicators=("indicator_name", lambda x: "；".join(sorted(set(map(str, x))))),
        reasons=("reason", lambda x: "；".join(map(str, x))),
        avg_score=("score", "mean"),
        indicator_count=("indicator_id", "count"),
    ).reset_index()

    cases_df = transcripts.merge(grouped, on="join_id", how="left")
    video_cases = []
    for _, row in cases_df.iterrows():
        doc = (
            f"产品类目：家庭K歌与影音一体机\n"
            f"视频ID：{row['join_id']}\n"
            f"口播全文：{_clip(row.get('transcript_text'), 1600)}\n"
            f"高分指标：{_clip(row.get('indicators'), 500)}\n"
            f"高分原因：{_clip(row.get('reasons'), 1000)}"
        )
        video_cases.append(
            {
                "id": f"case_{row['join_id']}",
                "document": doc,
                "metadata": {
                    "video_id": str(row["join_id"]),
                    "doc_type": "video_case",
                    "avg_score": 0.0 if pd.isna(row.get("avg_score")) else float(row.get("avg_score")),
                    "indicator_count": 0 if pd.isna(row.get("indicator_count")) else int(row.get("indicator_count")),
                },
            }
        )

    fragments = []
    for source, df, target in [
        ("completion_rate", data["completion_details"], "completion_rate"),
        ("roi", data["roi_details"], "roi"),
        ("all", data["all_details"], "all"),
    ]:
        for i, row in df.reset_index(drop=True).iterrows():
            fragment_type = infer_fragment_type(row["indicator_name"])
            doc = (
                f"目标：{target}\n"
                f"片段类型：{fragment_type}\n"
                f"指标：{row['indicator_id']} {row['indicator_name']}\n"
                f"分数：{row['score']}\n"
                f"可复用原因：{row['reason']}"
            )
            fragments.append(
                {
                    "id": f"fragment_{source}_{row['join_id']}_{row['indicator_id']}_{i}",
                    "document": doc,
                    "metadata": {
                        "video_id": str(row["join_id"]),
                        "target": target,
                        "fragment_type": fragment_type,
                        "indicator_id": str(row["indicator_id"]),
                        "indicator_name": str(row["indicator_name"]),
                        "score": int(row["score"]),
                    },
                }
            )

    rules = rule_docs(data["completion_rules"], "completion_rate") + rule_docs(data["roi_rules"], "roi")
    return {"video_cases": video_cases, "script_fragments": fragments, "strategy_rules": rules}


def metadata_matches_where(metadata: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
    """判断文档元数据是否满足过滤条件，支持普通相等匹配和 $in 列表匹配。"""
    if not where:
        return True
    for key, expected in where.items():
        actual = metadata.get(key)
        if isinstance(expected, dict) and "$in" in expected:
            if actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False
    return True


def build_local_vector_db() -> Dict[str, int]:
    """建设本地文件型向量库：保存文档 JSONL 和对应的 NumPy embedding 矩阵，作为 FAISS 不可用时的备用方案。"""
    client = embedding_client()
    docs_by_collection = build_vector_documents()
    if LOCAL_VECTOR_DIR.exists():
        shutil.rmtree(LOCAL_VECTOR_DIR)
    LOCAL_VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}

    for collection_name, docs in docs_by_collection.items():
        counts[collection_name] = len(docs)
        all_embeddings: List[List[float]] = []
        docs_path = LOCAL_VECTOR_DIR / f"{collection_name}.jsonl"
        with docs_path.open("w", encoding="utf-8") as f:
            for start in range(0, len(docs), 10):
                batch = docs[start : start + 10]
                texts = [d["document"] for d in batch]
                all_embeddings.extend(embed_texts(client, texts))
                for doc in batch:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                print(f"[index] {collection_name}: {min(start + len(batch), len(docs))}/{len(docs)}")

        embeddings = np.asarray(all_embeddings, dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-12)
        np.savez_compressed(LOCAL_VECTOR_DIR / f"{collection_name}.npz", embeddings=embeddings)

    return counts


def build_faiss_vector_db() -> Dict[str, int]:
    """建设 FAISS 向量库：生成归一化 embedding，创建内积索引并写入本地文件。"""
    client = embedding_client()
    docs_by_collection = build_vector_documents()
    if FAISS_VECTOR_DIR.exists():
        shutil.rmtree(FAISS_VECTOR_DIR)
    FAISS_VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}

    for collection_name, docs in docs_by_collection.items():
        counts[collection_name] = len(docs)
        all_embeddings: List[List[float]] = []
        docs_path = FAISS_VECTOR_DIR / f"{collection_name}.jsonl"
        with docs_path.open("w", encoding="utf-8") as f:
            for start in range(0, len(docs), 10):
                batch = docs[start : start + 10]
                texts = [d["document"] for d in batch]
                all_embeddings.extend(embed_texts(client, texts))
                for doc in batch:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                print(f"[index] {collection_name}: {min(start + len(batch), len(docs))}/{len(docs)}")

        embeddings = np.asarray(all_embeddings, dtype=np.float32)
        if embeddings.ndim != 2 or len(embeddings) != len(docs):
            raise RuntimeError(f"Invalid FAISS embeddings for {collection_name}.")
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(FAISS_VECTOR_DIR / f"{collection_name}.index"))

    return counts


def build_vector_db() -> Dict[str, int]:
    """根据 VECTOR_BACKEND 配置建设向量库：默认使用 FAISS，备用方案为本地文件型向量库。"""
    if VECTOR_BACKEND == "faiss":
        return build_faiss_vector_db()
    return build_local_vector_db()


def active_vector_dir() -> Path:
    """返回当前启用的向量库目录，便于命令行输出和结果追踪。"""
    if VECTOR_BACKEND == "faiss":
        return FAISS_VECTOR_DIR
    return LOCAL_VECTOR_DIR


def query_faiss_collection(
    collection_name: str,
    query: str,
    top_k: int,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """查询 FAISS 向量集合：对 query 做 embedding，相似度检索后按元数据条件过滤。"""
    docs_path = FAISS_VECTOR_DIR / f"{collection_name}.jsonl"
    index_path = FAISS_VECTOR_DIR / f"{collection_name}.index"
    if not docs_path.exists() or not index_path.exists():
        raise FileNotFoundError(f"FAISS collection is missing: {collection_name}. Run --build-index first.")

    docs = load_jsonl(docs_path)
    index = faiss.read_index(str(index_path))
    query_embedding = np.asarray(embed_texts(embedding_client(), [query])[0], dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    search_k = min(max(top_k * 8, top_k), len(docs))
    scores, indices = index.search(query_embedding, search_k)

    rows: List[Dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        doc = docs[int(idx)]
        metadata = doc.get("metadata", {})
        if not metadata_matches_where(metadata, where):
            continue
        rows.append(
            {
                "id": doc["id"],
                "document": doc["document"],
                "metadata": metadata,
                "distance": float(1.0 - score),
            }
        )
        if len(rows) >= top_k:
            break
    return rows


def query_local_collection(
    collection_name: str,
    query: str,
    top_k: int,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """查询简易本地向量集合：用矩阵点积计算相似度，并返回最相关文档。"""
    docs_path = LOCAL_VECTOR_DIR / f"{collection_name}.jsonl"
    embeddings_path = LOCAL_VECTOR_DIR / f"{collection_name}.npz"
    if not docs_path.exists() or not embeddings_path.exists():
        raise FileNotFoundError(f"Vector collection is missing: {collection_name}. Run --build-index first.")

    docs = load_jsonl(docs_path)
    embeddings = np.load(embeddings_path)["embeddings"]
    query_embedding = np.asarray(embed_texts(embedding_client(), [query])[0], dtype=np.float32)
    query_embedding = query_embedding / max(float(np.linalg.norm(query_embedding)), 1e-12)
    scores = embeddings @ query_embedding

    ranked = np.argsort(-scores)
    rows: List[Dict[str, Any]] = []
    for idx in ranked:
        doc = docs[int(idx)]
        metadata = doc.get("metadata", {})
        if not metadata_matches_where(metadata, where):
            continue
        rows.append(
            {
                "id": doc["id"],
                "document": doc["document"],
                "metadata": metadata,
                "distance": float(1.0 - scores[int(idx)]),
            }
        )
        if len(rows) >= top_k:
            break
    return rows


def query_collection(
    collection_name: str,
    query: str,
    top_k: int,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """统一向量检索入口：默认调用 FAISS，非 FAISS 配置时调用本地文件型向量库。"""
    if VECTOR_BACKEND == "faiss":
        return query_faiss_collection(collection_name, query, top_k, where)
    return query_local_collection(collection_name, query, top_k, where)


def retrieve_repair_evidence(state: ScriptAgentState, evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """根据评分结果检索改写证据：针对低分指标寻找高分片段归因，用于后续脚本修复。"""
    weak_items = []
    for item in evaluation.get("dimension_scores", []):
        try:
            score = float(item.get("score", 7))
        except Exception:
            score = 7
        if score <= 4:
            weak_items.append(item)

    evidence: List[Dict[str, Any]] = []
    seen_ids = set()
    objective = state.get("objective", "balanced")
    for item in weak_items[:4]:
        indicator_id = item.get("indicator_id")
        indicator_name = item.get("indicator_name", "")
        rewrite_need = item.get("rewrite_need", "")
        query = (
            f"{state.get('parsed_brief', {}).get('raw_brief', '')} "
            f"{indicator_id} {indicator_name} {rewrite_need} 高分案例 补足改写"
        )
        where = {"indicator_id": indicator_id} if indicator_id else None
        try:
            hits = query_collection("script_fragments", query, top_k=6, where=where)
        except Exception:
            hits = query_collection("script_fragments", query, top_k=6)
        for hit in hits:
            metadata = hit.get("metadata", {})
            try:
                score = float(metadata.get("score", 0))
            except Exception:
                score = 0
            target = metadata.get("target")
            if score < 6:
                continue
            if objective != "balanced" and target not in {objective, "all", None}:
                continue
            key = hit.get("id")
            if key in seen_ids:
                continue
            seen_ids.add(key)
            hit["repair_for"] = {
                "indicator_id": indicator_id,
                "indicator_name": indicator_name,
                "rewrite_need": rewrite_need,
            }
            evidence.append(hit)
            if len(evidence) >= 10:
                return evidence
    return evidence


def infer_objective(text: str) -> str:
    """从用户需求文本中推断优化目标：识别 ROI、转化、完播、留存等关键词。"""
    if re.search(r"roi|转化|成交|下单|咨询|直播间|点击", text, re.I):
        return "roi"
    if re.search(r"完播|留存|3秒|5秒|停留|看完", text, re.I):
        return "completion_rate"
    return "balanced"


def parse_brief_node(state: ScriptAgentState) -> ScriptAgentState:
    """LangGraph 节点：解析用户 brief，确定产品、目标、时长等结构化需求。"""
    user_input = state.get("user_input", "")
    objective = state.get("objective") or infer_objective(user_input)
    duration_sec = int(state.get("duration_sec") or 30)
    parsed = {
        "product": "家庭K歌影视一体机/家庭影音产品",
        "category": "家庭K歌与影音产品",
        "objective": objective,
        "duration_sec": duration_sec,
        "raw_brief": user_input,
    }
    return {
        **state,
        "objective": objective,
        "duration_sec": duration_sec,
        "parsed_brief": parsed,
        "trace": state.get("trace", []) + [f"parse_brief objective={objective} duration={duration_sec}"],
    }


def rag_retrieval_node(state: ScriptAgentState) -> ScriptAgentState:
    """LangGraph 节点：根据结构化需求从向量库检索案例、片段和策略规则。"""
    parsed = state["parsed_brief"]
    objective = state["objective"]
    query = f"{parsed['raw_brief']} {parsed['category']} 目标 {objective}"

    cases = query_collection("video_cases", query, top_k=6)
    if objective == "balanced":
        fragments = query_collection("script_fragments", query, top_k=12)
        rules = query_collection("strategy_rules", query, top_k=5)
    else:
        fragments = query_collection(
            "script_fragments",
            query,
            top_k=12,
            where={"target": {"$in": [objective, "all"]}},
        )
        rules = query_collection("strategy_rules", query, top_k=5, where={"target": objective})

    return {
        **state,
        "retrieved_cases": cases,
        "retrieved_fragments": fragments,
        "strategy_rules": rules,
        "trace": state.get("trace", []) + [
            f"rag_retrieval vector_db={VECTOR_BACKEND} cases={len(cases)} fragments={len(fragments)} rules={len(rules)}"
        ],
    }


def planning_node(state: ScriptAgentState) -> ScriptAgentState:
    """LangGraph 节点：基于用户需求和 RAG 证据生成广告脚本策划案。"""
    
    product_selling_points = state.get("product_selling_points", "")
    selling_points_section = ""
    if product_selling_points:
        selling_points_section = f"""
产品核心卖点：
{product_selling_points}

注意：策划时请重点突出以上产品卖点。
"""
    
    prompt = f"""
你是家庭K歌与影音一体机广告的资深短视频策划。
请基于用户需求和RAG证据输出 JSON，不要输出 Markdown。

用户需求：
{state['parsed_brief']}
{selling_points_section}
检索到的爆款案例：
{json.dumps(state.get('retrieved_cases', [])[:4], ensure_ascii=False)}

检索到的策略规则：
{json.dumps(state.get('strategy_rules', [])[:5], ensure_ascii=False)}

输出 JSON 字段：
{{
  "target_user": "...",
  "creative_angle": "...",
  "core_pain": "...",
  "core_selling_point": "...",
  "script_structure": ["0-3s ...", "3-8s ..."],
  "must_use_evidence": ["..."],
  "avoid": ["..."]
}}
"""
    fallback = {
        "target_user": "想低成本把电视改造成家庭KTV/影院的家庭用户",
        "creative_angle": "痛点开场 + 一根线安装证明 + 功能效果 + 明确CTA",
        "core_pain": "外出KTV贵、传统设备复杂、家里电视闲置",
        "core_selling_point": "一根线连接电视，K歌观影戏曲健身一体化",
        "script_structure": ["Hook：反差/悬念", "Setup：建立场景/痛点", "Twist：转折/解决", "CTA：评论钩/转发/点击引导"],
        "must_use_evidence": [],
        "avoid": ["不要空泛介绍品牌", "不要开头寒暄"],
    }
    planning = llm_json(prompt, fallback=fallback)
    return {**state, "planning": planning, "trace": state.get("trace", []) + ["planning llm=gpt-5.4"]}


def script_generation_node(state: ScriptAgentState) -> ScriptAgentState:
    """LangGraph 节点：根据策划案和爆款片段生成四段式结构化短视频脚本初稿。"""
    
    characters = state.get("characters", [])
    character_info = ""
    if characters:
        char_descriptions = []
        for char in characters:
            char_id = char.get("id", "Unknown")
            char_desc = char.get("description", "")
            if not char_desc:
                config = char.get("config", {})
                char_desc = f"{config.get('ethnicity', '')} {config.get('gender', '')}, {config.get('age', '')}"
            char_descriptions.append(f"- **{char_id}**: {char_desc}")
        
        character_info = f"""
可用人物（请在 visual 字段中指定使用哪个人物）：
{chr(10).join(char_descriptions)}

注意：visual 字段需要明确说明哪个镜头使用哪个人物出镜。
"""
    
    product_selling_points = state.get("product_selling_points", "")
    selling_points_section = ""
    if product_selling_points:
        selling_points_section = f"""
产品核心卖点（请在脚本中重点展示）：
{product_selling_points}
"""
    
    prompt = f"""
你是广告短视频脚本编剧。请基于策划案和RAG证据，生成可交给后续分镜Agent使用的结构化脚本。脚本尽量描述详细，明确人物、场景、动作、道具、画面构图、文案内容和口播内容。
必须输出 JSON，不要 Markdown。

用户需求：
{state['parsed_brief']}
{selling_points_section}
策划案：
{json.dumps(state.get('planning', {}), ensure_ascii=False)}
{character_info}
可借鉴的爆款片段：
{json.dumps(state.get('retrieved_fragments', [])[:10], ensure_ascii=False)}

输出 JSON schema：
{{
  "title": "...",
  "objective": "{state['objective']}",
  "strategy_summary": "...",
  "segments": [
    {{
      "time": "按总时长分配，例如0-3s",
      "stage": "Hook",
      "purpose": "反差/悬念",
      "visual": "画面描述",
      "voiceover": "口播",
      "subtitle": "字幕",
      "shot_hint": "核心分镜提示"
    }},
    {{
      "time": "按总时长分配，例如3-8s",
      "stage": "Setup",
      "purpose": "建立场景/痛点",
      "visual": "画面描述",
      "voiceover": "口播",
      "subtitle": "字幕",
      "shot_hint": "核心分镜提示"
    }},
    {{
      "time": "按总时长分配，例如8-13s",
      "stage": "Twist",
      "purpose": "转折/解决",
      "visual": "画面描述",
      "voiceover": "口播",
      "subtitle": "字幕",
      "shot_hint": "核心分镜提示"
    }},
    {{
      "time": "按总时长分配，例如13-15s",
      "stage": "CTA",
      "purpose": "评论钩/转发/点击引导",
      "visual": "画面描述",
      "voiceover": "口播",
      "subtitle": "字幕",
      "shot_hint": "核心分镜提示"
    }}
  ],
  "retrieved_evidence_used": ["video_id或片段理由"],
  "variant_suggestions": ["..."]
}}

要求：
1. 产品围绕家庭K歌/影音一体机。
2. 不要照抄检索案例原文，要改写。
3. 必须输出四段式，segments 只能有 4 段：Hook、Setup、Twist、CTA。
4. 请根据用户要求的总时长 {state['duration_sec']} 秒合理分配每段时间，如未指定，控制在30s左右 。
5. Hook 负责反差/悬念；Setup 负责建立场景/痛点；Twist 负责转折/解决并包含安装/连接/功能演示中的至少一种证明；CTA 负责评论钩/转发/点击引导并有明确行动。
"""
    fallback = {
        "title": "一台电视，低成本改成家庭KTV",
        "objective": state["objective"],
        "strategy_summary": "基于RAG证据生成",
        "segments": [
            {"time": "0-20%", "stage": "Hook", "purpose": "反差/悬念", "visual": "", "voiceover": "", "subtitle": "", "shot_hint": ""},
            {"time": "20-50%", "stage": "Setup", "purpose": "建立场景/痛点", "visual": "", "voiceover": "", "subtitle": "", "shot_hint": ""},
            {"time": "50-85%", "stage": "Twist", "purpose": "转折/解决", "visual": "", "voiceover": "", "subtitle": "", "shot_hint": ""},
            {"time": "85-100%", "stage": "CTA", "purpose": "评论钩/转发/点击引导", "visual": "", "voiceover": "", "subtitle": "", "shot_hint": ""},
        ],
        "retrieved_evidence_used": [],
        "variant_suggestions": [],
    }
    draft = llm_json(prompt, fallback=fallback)
    return {**state, "draft_script": draft, "trace": state.get("trace", []) + ["script_generation llm=gpt-5.4"]}


def evaluation_rewrite_node(state: ScriptAgentState) -> ScriptAgentState:
    """LangGraph 节点：按评价标准给初稿评分，检索补强证据并生成最终改写脚本。"""
    evaluation_standard = compact_evaluation_standard()
    eval_prompt = f"""
你是短视频广告脚本评分Agent。请严格按照给定的内容评价标准库，对脚本进行逐指标评分。
必须输出 JSON，不要 Markdown。

优化目标：{state['objective']}
用户需求：{state['parsed_brief']}
策划案：{json.dumps(state.get('planning', {}), ensure_ascii=False)}
初稿脚本：{json.dumps(state.get('draft_script', {}), ensure_ascii=False)}

内容评价标准库：
{json.dumps(evaluation_standard, ensure_ascii=False)}

输出 JSON schema：
{{
  "evaluation": {{
    "overall_score": 0,
    "passed": true,
    "pass_criteria": "说明是否通过的依据",
    "dimension_scores": [
      {{
        "indicator_id": "D001-I001",
        "indicator_name": "Hook (0-3秒)",
        "score": 1,
        "problem": "低分问题；高分则为空",
        "rewrite_need": "需要如何补足；高分则为空"
      }}
    ],
    "hard_constraints": {{
      "has_four_part_structure": true,
      "has_hook": true,
      "has_twist_solution_or_proof": true,
      "has_cta": true,
      "has_forbidden_claim": false
    }},
    "strengths": ["..."],
    "weaknesses": ["..."],
    "rewrite_notes": ["..."]
  }}
}}

通过规则：
1. overall_score 建议按 1-100 输出。
2. 关键硬约束不满足时 passed=false。
3. 任一核心指标低于4分时 passed=false，并填写 rewrite_need。
"""
    fallback = {
        "evaluation": {
            "overall_score": 0,
            "passed": False,
            "pass_criteria": "评分模型输出解析失败",
            "dimension_scores": [],
            "hard_constraints": {},
            "strengths": [],
            "weaknesses": [],
            "rewrite_notes": ["评分失败，请检查模型输出"],
        },
    }
    scored = llm_json(eval_prompt, fallback=fallback)
    evaluation = scored.get("evaluation", scored)
    repair_evidence = retrieve_repair_evidence(state, evaluation)

    rewrite_prompt = f"""
你是短视频广告脚本改写Agent。请根据评分结果和高分案例补足证据，对初稿做定向改写。
必须输出 JSON，不要 Markdown。

用户需求：{state['parsed_brief']}
策划案：{json.dumps(state.get('planning', {}), ensure_ascii=False)}
初稿脚本：{json.dumps(state.get('draft_script', {}), ensure_ascii=False)}
评分结果：{json.dumps(evaluation, ensure_ascii=False)}
针对低分维度检索到的高分案例/片段证据：
{json.dumps(repair_evidence, ensure_ascii=False)}

改写要求：
1. 保留四段式：Hook、Setup、Twist、CTA，segments 只能有4段。
2. 只针对评分中的弱项补足，不要无关重写。
3. 参考高分证据的方法，不要照抄原文。
4. 输出 final_script，字段如下：
{{
  "final_script": {{
    "title": "...",
    "objective": "{state['objective']}",
    "segments": [
      {{"time": "按总时长分配", "stage": "Hook", "purpose": "反差/悬念", "visual": "...", "voiceover": "...", "subtitle": "...", "shot_hint": "..."}},
      {{"time": "按总时长分配", "stage": "Setup", "purpose": "建立场景/痛点", "visual": "...", "voiceover": "...", "subtitle": "...", "shot_hint": "..."}},
      {{"time": "按总时长分配", "stage": "Twist", "purpose": "转折/解决", "visual": "...", "voiceover": "...", "subtitle": "...", "shot_hint": "..."}},
      {{"time": "按总时长分配", "stage": "CTA", "purpose": "评论钩/转发/点击引导", "visual": "...", "voiceover": "...", "subtitle": "...", "shot_hint": "..."}}
    ],
    "rewrite_summary": ["说明补足了哪些弱项"],
    "repair_evidence_used": ["使用了哪些高分证据"]
  }}
}}
"""
    rewritten = llm_json(rewrite_prompt, fallback={"final_script": state.get("draft_script", {})})
    final_script = rewritten.get("final_script", state.get("draft_script", {}))

    return {
        **state,
        "evaluation": evaluation,
        "repair_evidence": repair_evidence,
        "final_script": final_script,
        "final_output": {
            "evaluation": evaluation,
            "repair_evidence": repair_evidence,
            "script": final_script,
        },
        "trace": state.get("trace", []) + [
            f"evaluation_rewrite standard=v4 repair_evidence={len(repair_evidence)}"
        ],
    }


def build_graph():
    """构建 LangGraph 工作流：串联 brief 解析、RAG 检索、策划、生成、评分改写节点。"""
    graph = StateGraph(ScriptAgentState)
    graph.add_node("parse_brief", parse_brief_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("planning", planning_node)
    graph.add_node("script_generation", script_generation_node)
    graph.add_node("evaluation_rewrite", evaluation_rewrite_node)
    graph.set_entry_point("parse_brief")
    graph.add_edge("parse_brief", "rag_retrieval")
    graph.add_edge("rag_retrieval", "planning")
    graph.add_edge("planning", "script_generation")
    graph.add_edge("script_generation", "evaluation_rewrite")
    graph.add_edge("evaluation_rewrite", END)
    return graph.compile()


def run_agent(
    brief: str, 
    objective: str, 
    duration: int, 
    characters: Optional[List[Dict]] = None,
    product_selling_points: Optional[str] = None
) -> Dict[str, Any]:
    """运行完整脚本生成 Agent：创建图工作流并传入 brief、目标、时长、可用角色和产品卖点参数。"""
    app = build_graph()
    return app.invoke(
        {
            "user_input": brief,
            "objective": objective,
            "duration_sec": duration,
            "characters": characters or [],
            "product_selling_points": product_selling_points or "",
            "trace": [],
        }
    )


def extract_final_output(result: Dict[str, Any]) -> Dict[str, Any]:
    """提取最终交付结果：只保留下游需要的策划和最终脚本，去掉评分、检索证据等调试信息。"""
    final_output = result.get("final_output") or {}
    script = dict(final_output.get("script") or result.get("final_script", {}))
    for debug_key in ["repair_evidence_used", "rewrite_summary"]:
        script.pop(debug_key, None)
    return {
        "planning": result.get("planning", {}),
        "script": script,
    }


def format_final_script_markdown(final_output: Dict[str, Any]) -> str:
    """将最终脚本转成 Markdown：便于人工查看，也方便后续交付文档直接引用。"""
    planning = final_output.get("planning", {})
    script = final_output.get("script", {})
    lines = [f"# {script.get('title', '最终脚本')}", ""]

    if planning:
        lines.append("## 最终策划")
        for key, value in planning.items():
            if isinstance(value, (list, dict)):
                value_text = json.dumps(value, ensure_ascii=False)
            else:
                value_text = str(value)
            lines.append(f"- {key}：{value_text}")
        lines.append("")

    segments = script.get("segments", [])
    if segments:
        lines.append("## 四段式脚本")
        for segment in segments:
            stage = segment.get("stage", "-")
            time_range = segment.get("time", "-")
            lines.extend(
                [
                    "",
                    f"### {stage}（{time_range}）",
                    f"- 作用：{segment.get('purpose', '')}",
                    f"- 画面：{segment.get('visual', '')}",
                    f"- 口播：{segment.get('voiceover', '')}",
                    f"- 字幕：{segment.get('subtitle', '')}",
                    f"- 镜头/剪辑：{segment.get('shot_hint', '')}",
                ]
            )
    else:
        lines.extend(["## 脚本 JSON", "```json", json.dumps(script, ensure_ascii=False, indent=2), "```"])

    rewrite_summary = script.get("rewrite_summary") or []
    if rewrite_summary:
        lines.extend(["", "## 改写摘要"])
        lines.extend(f"- {item}" for item in rewrite_summary)

    return "\n".join(lines).strip() + "\n"


def save_final_script(result: Dict[str, Any], output_dir: Path = OUTPUT_DIR / "final_script") -> Dict[str, Path]:
    """保存最终脚本专用文件：写入精简 JSON 和 Markdown，避免下游从完整调试结果中解析。"""
    final_output = extract_final_output(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "final_script.json"
    md_path = output_dir / "final_script.md"
    json_path.write_text(json.dumps(final_output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(format_final_script_markdown(final_output), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def main():
    """命令行入口：支持建设向量索引或运行 RAG 脚本生成流程，并保存输出结果。"""
    parser = argparse.ArgumentParser(description="LangGraph real RAG script agent")
    parser.add_argument("--build-index", action="store_true", help="build vector database from processed knowledge base")
    parser.add_argument("--brief", default="做一条30秒家庭K歌影视一体机广告，突出普通电视一根线变KTV、曲库多、低价送麦克风。")
    parser.add_argument("--objective", default="roi", choices=["completion_rate", "roi", "balanced"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--out", default=str(OUTPUT_DIR / "script_complete_result.json"))
    args = parser.parse_args()

    if args.build_index:
        counts = build_vector_db()
        print(
            json.dumps(
                {"indexed": counts, "vector_backend": VECTOR_BACKEND, "vector_dir": str(active_vector_dir())},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = run_agent(args.brief, args.objective, args.duration)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    final_paths = save_final_script(result)

    print("=== TRACE ===")
    for item in result.get("trace", []):
        print("-", item)
    print("\n=== EVALUATION ===")
    print(json.dumps(result.get("evaluation", {}), ensure_ascii=False, indent=2))
    print("\n=== FINAL SCRIPT ===")
    print(
        json.dumps(
            result.get(
                "final_output",
                {"evaluation": result.get("evaluation", {}), "script": result.get("final_script", {})},
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"\nSaved: {out_path}")
    print(f"Final script JSON: {final_paths['json']}")
    print(f"Final script Markdown: {final_paths['markdown']}")


if __name__ == "__main__":
    main()

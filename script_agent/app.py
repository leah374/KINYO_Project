import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# Add parent directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from script_agent.agent.script_agent import VECTOR_BACKEND, active_vector_dir, run_agent, save_final_script


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LAST_RESULT_PATH = OUTPUT_DIR / "streamlit_last_result.json"


def save_result(result: Dict[str, Any]) -> None:
    """save_result 处理本模块对应的数据、模型调用或界面逻辑。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "result": result,
    }
    LAST_RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_final_script(result)


def load_last_result() -> Dict[str, Any] | None:
    """load_last_result 处理本模块对应的数据、模型调用或界面逻辑。"""
    if not LAST_RESULT_PATH.exists():
        return None
    try:
        payload = json.loads(LAST_RESULT_PATH.read_text(encoding="utf-8"))
        return payload.get("result")
    except Exception:
        return None


def get_final_output(result: Dict[str, Any]) -> Dict[str, Any]:
    """get_final_output 处理本模块对应的数据、模型调用或界面逻辑。"""
    return result.get("final_output") or {
        "script": result.get("final_script", {}),
        "evaluation": result.get("evaluation", {}),
        "repair_evidence": result.get("repair_evidence", []),
    }


def render_script(script: Dict[str, Any]) -> None:
    """render_script 处理本模块对应的数据、模型调用或界面逻辑。"""
    if not script:
        st.info("暂无脚本结果")
        return

    st.subheader(script.get("title", "生成脚本"))
    segments = script.get("segments", [])
    if not segments:
        st.json(script)
        return

    stage_order = ["Hook", "Setup", "Twist", "CTA"]
    stage_tabs = st.tabs(stage_order)
    by_stage = {str(seg.get("stage", "")).lower(): seg for seg in segments}

    for tab, stage in zip(stage_tabs, stage_order):
        seg = by_stage.get(stage.lower())
        with tab:
            if not seg:
                st.warning(f"未生成 {stage} 段")
                continue
            cols = st.columns([1, 1, 2])
            cols[0].metric("阶段", stage)
            cols[1].metric("时间", seg.get("time", "-"))
            cols[2].write(f"**作用**：{seg.get('purpose', '-')}")
            st.write("**画面**")
            st.write(seg.get("visual", ""))
            st.write("**口播**")
            st.info(seg.get("voiceover", ""))
            st.write("**字幕**")
            st.write(seg.get("subtitle", ""))
            st.write("**镜头/剪辑提示**")
            st.write(seg.get("shot_hint", ""))

    rewrite_summary = script.get("rewrite_summary") or []
    if rewrite_summary:
        st.divider()
        st.write("**改写摘要**")
        for item in rewrite_summary:
            st.write(f"- {item}")


def render_evaluation(evaluation: Dict[str, Any]) -> None:
    """render_evaluation 处理本模块对应的数据、模型调用或界面逻辑。"""
    if not evaluation:
        st.info("暂无评分结果")
        return

    score = evaluation.get("overall_score", "-")
    passed = evaluation.get("passed", False)
    cols = st.columns(3)
    cols[0].metric("总分", score)
    cols[1].metric("是否通过", "通过" if passed else "未通过")
    cols[2].metric("评分标准", "内容标准库 v4")

    if evaluation.get("pass_criteria"):
        st.write(evaluation["pass_criteria"])

    rows = evaluation.get("dimension_scores", [])
    if rows:
        table = pd.DataFrame(rows)
        preferred_cols = ["indicator_id", "indicator_name", "score", "problem", "rewrite_need"]
        existing_cols = [col for col in preferred_cols if col in table.columns]
        st.dataframe(table[existing_cols], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.write("**优势**")
        for item in evaluation.get("strengths", []):
            st.write(f"- {item}")
    with c2:
        st.write("**弱项**")
        for item in evaluation.get("weaknesses", []):
            st.write(f"- {item}")

    notes = evaluation.get("rewrite_notes") or []
    if notes:
        st.write("**改写建议**")
        for item in notes:
            st.write(f"- {item}")


def render_evidence(items: List[Dict[str, Any]], title: str) -> None:
    """render_evidence 处理本模块对应的数据、模型调用或界面逻辑。"""
    if not items:
        st.info("暂无证据")
        return
    for idx, item in enumerate(items, start=1):
        metadata = item.get("metadata", {})
        label = f"{idx}. {item.get('id', 'evidence')} | video_id={metadata.get('video_id', '-')}"
        with st.expander(label):
            st.write("**metadata**")
            st.json(metadata)
            repair_for = item.get("repair_for")
            if repair_for:
                st.write("**补足目标**")
                st.json(repair_for)
            st.write("**内容**")
            st.write(item.get("document", ""))


def render_trace(result: Dict[str, Any]) -> None:
    """render_trace 处理本模块对应的数据、模型调用或界面逻辑。"""
    trace = result.get("trace", [])
    if not trace:
        st.info("暂无运行日志")
        return
    for item in trace:
        st.write(f"- {item}")


def main() -> None:
    """main 处理本模块对应的数据、模型调用或界面逻辑。"""
    st.set_page_config(page_title="脚本生成 Agent", layout="wide")
    st.title("脚本生成 Agent")

    with st.sidebar:
        st.header("输入")
        brief = st.text_area(
            "广告需求",
            value="做一条30秒家庭K歌影视一体机广告，目标提升转化，突出普通电视一根线变KTV、曲库多、送麦克风、适合家庭聚会和长辈娱乐。",
            height=180,
        )
        objective = st.selectbox(
            "目标",
            options=["roi", "completion_rate", "balanced"],
            index=0,
            format_func=lambda x: {"roi": "ROI 转化", "completion_rate": "完播率", "balanced": "综合"}[x],
        )
        duration = st.number_input("时长", min_value=10, max_value=120, value=30, step=5)

        st.divider()
        st.caption(f"向量后端：{VECTOR_BACKEND}")
        vector_dir = active_vector_dir()
        st.caption(f"索引目录：{vector_dir}")
        index_ready = (vector_dir / "video_cases.index").exists() or (vector_dir / "video_cases.npz").exists()
        st.caption("索引状态：已就绪" if index_ready else "索引状态：未找到")

        generate = st.button("生成脚本", type="primary", use_container_width=True, disabled=not index_ready)
        load_last = st.button("加载上次结果", use_container_width=True)

    if load_last:
        last = load_last_result()
        if last:
            st.session_state["result"] = last
        else:
            st.warning("没有找到上次结果")

    if generate:
        with st.spinner("正在检索案例、生成脚本并评分改写..."):
            result = run_agent(brief=brief, objective=objective, duration=int(duration))
            save_result(result)
            st.session_state["result"] = result

    result = st.session_state.get("result")
    if not result:
        st.info("输入需求后点击生成脚本")
        return

    final_output = get_final_output(result)
    script = final_output.get("script", {})
    evaluation = final_output.get("evaluation", {})
    repair_evidence = final_output.get("repair_evidence", [])

    tabs = st.tabs(["最终脚本", "评分", "补足证据", "检索结果", "运行日志", "原始 JSON"])
    with tabs[0]:
        render_script(script)
    with tabs[1]:
        render_evaluation(evaluation)
    with tabs[2]:
        render_evidence(repair_evidence, "补足证据")
    with tabs[3]:
        sub_tabs = st.tabs(["完整案例", "片段", "策略规则"])
        with sub_tabs[0]:
            render_evidence(result.get("retrieved_cases", []), "完整案例")
        with sub_tabs[1]:
            render_evidence(result.get("retrieved_fragments", []), "片段")
        with sub_tabs[2]:
            render_evidence(result.get("strategy_rules", []), "策略规则")
    with tabs[4]:
        render_trace(result)
    with tabs[5]:
        st.json(result)


if __name__ == "__main__":
    main()

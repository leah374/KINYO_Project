"""
Script Generation Page
AI-powered script generation using RAG and content evaluation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import streamlit as st
import pandas as pd

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase
from streamlit_app.utils.workflow_manager import WorkflowManager
from streamlit_app.components.file_manager import FileManager
from streamlit_app.components.script_editor import ScriptEditor
from streamlit_app.components.progress_tracker import ProgressTracker
from visual_agent.agent.character_generator import list_generated_characters


def render_script(script_data: dict):
    """Render script result with tabs"""
    if not script_data:
        st.info("No script generated yet")
        return
    
    planning = script_data.get("planning", {})
    script = script_data.get("script", script_data)
    segments = script.get("segments", [])
    
    if not segments:
        st.json(script_data)
        return
    
    st.subheader(script.get("title", "Generated Script"))
    
    if planning:
        st.markdown("#### Planning")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Target User**: {planning.get('target_user', 'N/A')}")
            st.markdown(f"**Core Selling Point**: {planning.get('core_selling_point', 'N/A')[:100]}...")
        with col2:
            st.markdown(f"**Creative Angle**: {planning.get('creative_angle', 'N/A')}")
            st.markdown(f"**Core Pain Point**: {planning.get('core_pain_point', 'N/A')[:100]}...")
        st.divider()
    
    st.markdown("#### Script Segments")
    
    stage_order = ["Hook", "Setup", "Twist", "CTA"]
    stage_tabs = st.tabs(stage_order)
    by_stage = {str(seg.get("stage", "")).upper(): seg for seg in segments}
    
    for tab, stage in zip(stage_tabs, stage_order):
        seg = by_stage.get(stage.upper())
        with tab:
            if not seg:
                st.warning(f"No {stage} segment generated")
                continue
            
            cols = st.columns([1, 1, 2])
            cols[0].metric("Stage", stage)
            cols[1].metric("Time", seg.get("time", "-"))
            cols[2].markdown(f"**Purpose**: {seg.get('purpose', '-')}")
            
            st.markdown("**Visual**")
            st.write(seg.get("visual", ""))
            
            st.markdown("**Voiceover**")
            st.info(seg.get("voiceover", ""))
            
            st.markdown("**Subtitle**")
            st.write(seg.get("subtitle", ""))
            
            st.markdown("**Shot Hint**")
            st.write(seg.get("shot_hint", ""))


def render_evaluation(evaluation: dict):
    """Render evaluation results"""
    if not evaluation:
        st.info("No evaluation result")
        return
    
    score = evaluation.get("overall_score", "-")
    passed = evaluation.get("passed", False)
    
    cols = st.columns(3)
    cols[0].metric("Total Score", score)
    cols[1].metric("Passed", "✓ Yes" if passed else "✗ No")
    cols[2].metric("Standard", "Content Standard v4")
    
    if evaluation.get("pass_criteria"):
        st.markdown(evaluation.get("pass_criteria"))
    
    rows = evaluation.get("dimension_scores", [])
    if rows:
        table = pd.DataFrame(rows)
        preferred_cols = ["indicator_id", "indicator_name", "score", "problem", "rewrite_need"]
        existing_cols = [col for col in preferred_cols if col in table.columns]
        st.dataframe(table[existing_cols], use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Strengths**")
        for item in evaluation.get("strengths", []):
            st.markdown(f"- {item}")
    with c2:
        st.markdown("**Weaknesses**")
        for item in evaluation.get("weaknesses", []):
            st.markdown(f"- {item}")


def render_evidence(items: list, title: str):
    """Render evidence items"""
    if not items:
        st.info(f"No {title}")
        return
    
    for idx, item in enumerate(items, start=1):
        metadata = item.get("metadata", {})
        label = f"{idx}. {item.get('id', 'evidence')} | video_id={metadata.get('video_id', '-')}"
        
        with st.expander(label):
            st.markdown("**Metadata**")
            st.json(metadata)
            
            repair_for = item.get("repair_for")
            if repair_for:
                st.markdown("**Repair Target**")
                st.json(repair_for)
            
            st.markdown("**Content**")
            st.write(item.get("document", "")[:500])


def main():
    st.set_page_config(
        page_title="脚本生成 - KINYO AI",
        page_icon="📝",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    
    config = ConfigManager()
    db = HistoryDatabase()
    workflow = WorkflowManager()
    
    st.title("📝 Script Generation")
    
    with st.sidebar:
        st.markdown("### Input Settings")
        
        brief = st.text_area(
            "Marketing Brief",
            value="做一条30秒家庭K歌影视一体机广告，目标提升转化，突出普通电视一根线变KTV、曲库多、送麦克风、适合家庭聚会和长辈娱乐。",
            height=180,
            help="Describe your product, target audience, and marketing goals"
        )
        
        objective = st.selectbox(
            "Objective",
            options=["roi", "completion_rate", "balanced"],
            index=0,
            format_func=lambda x: {"roi": "ROI / Conversion", "completion_rate": "Completion Rate", "balanced": "Balanced"}[x]
        )
        
        duration = st.number_input(
            "Duration (seconds)",
            min_value=10,
            max_value=120,
            value=30,
            step=5
        )
        
        st.divider()
        
        st.markdown("### Characters")
        characters_dir = config.get_path("assets") / "characters"
        available_chars = list_generated_characters(characters_dir)
        
        if available_chars:
            st.markdown(f"Found **{len(available_chars)}** characters")
            
            selected_chars = []
            for char in available_chars:
                char_id = char.get("id", "")
                char_desc = char.get("description", "")
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.checkbox(f"**{char_id}**", key=f"char_select_{char_id}"):
                        selected_chars.append(char)
                with col2:
                    st.caption(char_desc[:60] + "..." if len(char_desc) > 60 else char_desc)
            
            st.session_state["selected_characters"] = selected_chars
        else:
            st.info("No characters found. Generate characters first.")
            st.session_state["selected_characters"] = []
        
        st.divider()
        
        with st.expander("Advanced Options"):
            st.markdown("#### Model Settings")
            model = st.text_input(
                "Generation Model",
                value=config.get_model("script_generation")
            )
            
            st.markdown("#### Retrieval Settings")
            retrieval_top_k = st.slider("Top K Results", 1, 10, 5)
        
        st.divider()
        
        st.markdown("### Vector Index")
        vector_dir = config.get_path("script_agent") / "vector_db"
        index_ready = (vector_dir / "video_cases.index").exists() if vector_dir.exists() else False
        
        if index_ready:
            st.success("✓ Index ready")
        else:
            st.error("✗ Index not found")
            if st.button("Build Index", use_container_width=True):
                with st.spinner("Building vector index..."):
                    try:
                        from script_agent.agent.script_agent import main as build_index
                        import sys
                        sys.argv = ["script_agent.py", "--build-index"]
                        build_index()
                        st.success("Index built successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to build index: {e}")
        
        st.divider()
        
        generate = st.button("🚀 Generate Script", type="primary", use_container_width=True, disabled=not index_ready)
    
    if generate:
        selected_chars = st.session_state.get("selected_characters", [])
        
        with st.spinner("Generating script with RAG and evaluation..."):
            try:
                result = workflow.run_script_generation(
                    brief=brief,
                    objective=objective,
                    duration=duration,
                    characters=selected_chars if selected_chars else None
                )
                
                if result["success"]:
                    st.session_state["script_result"] = result["result"]
                    st.success("✓ Script generated successfully!")
                else:
                    st.error(f"Generation failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error during generation: {str(e)}")
    
    result = st.session_state.get("script_result")
    
    if not result:
        st.info("Enter your brief and click 'Generate Script' to start")
        return
    
    final_output = result.get("final_output") or {
        "script": result.get("final_script", {}),
        "evaluation": result.get("evaluation", {}),
        "repair_evidence": result.get("repair_evidence", [])
    }
    
    script = final_output.get("script", {})
    evaluation = final_output.get("evaluation", {})
    repair_evidence = final_output.get("repair_evidence", [])
    
    tabs = st.tabs(["📜 Final Script", "📊 Evaluation", "🔍 Evidence", "📖 Retrieved Cases", "📝 Editor", "💾 Export"])
    
    with tabs[0]:
        render_script(script)
    
    with tabs[1]:
        render_evaluation(evaluation)
    
    with tabs[2]:
        render_evidence(repair_evidence, "Repair Evidence")
    
    with tabs[3]:
        sub_tabs = st.tabs(["Cases", "Fragments", "Strategy Rules"])
        
        with sub_tabs[0]:
            render_evidence(result.get("retrieved_cases", []), "Retrieved Cases")
        
        with sub_tabs[1]:
            render_evidence(result.get("retrieved_fragments", []), "Retrieved Fragments")
        
        with sub_tabs[2]:
            render_evidence(result.get("strategy_rules", []), "Strategy Rules")
    
    with tabs[4]:
        edited_data = ScriptEditor.render_editor(script, key="script_editor_main")
        
        if st.button("Save Edited Script"):
            script_path = config.get_path("outputs") / "final_script" / "final_script_edited.json"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(script_path, 'w', encoding='utf-8') as f:
                json.dump(edited_data, f, ensure_ascii=False, indent=2)
            
            st.success(f"✓ Saved to {script_path}")
            SessionStateManager.set("edited_script_path", str(script_path))
    
    with tabs[5]:
        from datetime import datetime
        
        st.markdown("### Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            FileManager.download_button(result, "script_result.json", "📥 Download Full Result (JSON)")
        
        with col2:
            if script:
                FileManager.download_button(script, "final_script.json", "📥 Download Script Only (JSON)")
        
        st.divider()
        
        st.markdown("#### Save Script")
        
        col_save1, col_save2 = st.columns([3, 1])
        
        with col_save1:
            custom_name = st.text_input(
                "Filename (without extension)",
                value="",
                placeholder="Leave empty for auto-generated name",
                key="script_save_filename"
            )
        
        with col_save2:
            st.write("")
            st.write("")
            if st.button("💾 Save Script", type="primary", use_container_width=True):
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if custom_name.strip():
                    filename = f"{custom_name.strip()}_{timestamp}.json"
                else:
                    filename = f"script_{timestamp}.json"
                
                # Prepare Storyboard-compatible format
                final_output = result.get("final_output") or {
                    "script": result.get("final_script", {}),
                    "evaluation": result.get("evaluation", {}),
                    "repair_evidence": result.get("repair_evidence", [])
                }
                
                script_data = final_output.get("script", result.get("final_script", {}))
                
                # Save in Storyboard-compatible format
                storyboard_compatible = {
                    "planning": result.get("planning", {}),
                    "script": script_data
                }
                
                # Save to outputs/final_script/
                script_save_path = config.get_path("outputs") / "final_script" / filename
                script_save_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(script_save_path, 'w', encoding='utf-8') as f:
                    json.dump(storyboard_compatible, f, ensure_ascii=False, indent=2)
                
                SessionStateManager.set("last_saved_script_path", str(script_save_path))
                st.success(f"✓ Saved to `{filename}`")
        
        st.divider()
        
        st.markdown("#### Saved Scripts")
        
        final_script_dir = config.get_path("outputs") / "final_script"
        
        if final_script_dir.exists():
            script_files = sorted(
                final_script_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if script_files:
                with st.container(height=300):
                    for script_file in script_files[:20]:
                        file_mtime = datetime.fromtimestamp(script_file.stat().st_mtime)
                        file_size = script_file.stat().st_size / 1024
                        
                        col_file1, col_file2, col_file3 = st.columns([3, 2, 1])
                        
                        with col_file1:
                            st.markdown(f"**{script_file.name}**")
                        
                        with col_file2:
                            st.caption(f"{file_mtime.strftime('%Y-%m-%d %H:%M:%S')} | {file_size:.1f} KB")
                        
                        with col_file3:
                            if st.button("📄", key=f"view_{script_file.name}", help="View file"):
                                with open(script_file, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                st.session_state[f"viewing_file_{script_file.name}"] = file_content
                            
                            if st.button("📋", key=f"use_{script_file.name}", help="Use for Storyboard"):
                                SessionStateManager.set("script_file_path", str(script_file))
                                st.success(f"✓ Selected: {script_file.name}")
                        
                        if f"viewing_file_{script_file.name}" in st.session_state:
                            with st.expander(f"Preview: {script_file.name}", expanded=True):
                                st.json(json.loads(st.session_state[f"viewing_file_{script_file.name}"]))
                        
                        st.divider()
            else:
                st.info("No saved scripts yet. Generate and save a script first.")
        else:
            st.info("No saved scripts yet. Generate and save a script first.")


if __name__ == "__main__":
    main()

"""
KINYO AI Video Generation Platform - Main Application
Unified Streamlit interface for script, storyboard, and video generation
"""

import sys
from pathlib import Path

# ============================================================
# TypedDict extra_items Compatibility Patch
# This MUST be done before importing langchain-core or langgraph
# ============================================================
try:
    from typing_extensions import _TypedDictMeta
    _original_new = _TypedDictMeta.__new__
    
    def _patched_new(mcls, name, bases, namespace, **kwargs):
        # Remove unsupported parameters (Python < 3.15)
        kwargs.pop('extra_items', None)
        kwargs.pop('closed', None)
        return _original_new(mcls, name, bases, namespace, **kwargs)
    
    _TypedDictMeta.__new__ = staticmethod(_patched_new)
except Exception as e:
    print(f"[Warning] TypedDict patch failed: {e}")
# ============================================================

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase


def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="KINYO AI 视频生成平台",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/WANGKAI328/KINYO_Project',
            'Report a bug': "https://github.com/WANGKAI328/KINYO_Project/issues",
            'About': "# KINYO AI Video Generation Platform\n\nUnified interface for AI-powered video creation"
        }
    )
    
    SessionStateManager.init_session_state()
    
    config = ConfigManager()
    db = HistoryDatabase()
    
    st.sidebar.markdown("# 🎬 KINYO")
    st.sidebar.markdown("**AI 视频生成平台**")
    st.sidebar.divider()
    
    st.sidebar.markdown("### 📊 System Status")
    
    api_validation = {
        "Script": bool(config.get_api_key("k_token") or config.get_api_key("openai")),
        "Embedding": bool(config.get_api_key("dashscope")),
        "Video": bool(config.get_api_key("ark") or config.get_api_key("seedance")),
    }
    
    for feature, is_ready in api_validation.items():
        if is_ready:
            st.sidebar.success(f"✓ {feature}")
        else:
            st.sidebar.error(f"✗ {feature}")
    
    st.sidebar.divider()
    
    stats = db.get_statistics()
    st.sidebar.markdown("### 📈 Statistics")
    st.sidebar.metric("Scripts", stats.get("script_count", 0))
    st.sidebar.metric("Keyframes", stats.get("storyboard_count", 0))
    st.sidebar.metric("Videos", stats.get("video_count", 0))
    
    st.sidebar.divider()
    
    workflow_stage = SessionStateManager.get_workflow_stage()
    st.sidebar.markdown("### 🔄 Workflow")
    st.sidebar.info(f"Current: **{workflow_stage}**")
    
    st.sidebar.divider()
    
    st.sidebar.markdown("### ⚙️ Quick Actions")
    if st.sidebar.button("🧹 Clear Session", use_container_width=True):
        SessionStateManager.clear_workflow()
        st.rerun()
    
    if st.sidebar.button("📝 Go to Script Gen", use_container_width=True):
        st.switch_page("pages/3_📝_脚本生成.py")
    
    st.sidebar.divider()
    
    st.sidebar.markdown("""
    ### 📚 Documentation
    - [GitHub Repository](https://github.com/WANGKAI328/KINYO_Project)
    """)
    
    # Custom title with optional icon image
    project_root = Path(__file__).resolve().parents[1]
    logo_dir = project_root / "assets"
    title_icon_found = None
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        icon_path = logo_dir / f"title_icon{ext}"
        if icon_path.exists():
            title_icon_found = icon_path
            break
    
    if title_icon_found:
        # Display image + text side by side with tight spacing
        col1, col2 = st.columns([0.6, 11])
        with col1:
            st.image(str(title_icon_found), width=55)
        with col2:
            st.markdown("""
                <h1 style='margin-top: -8px; margin-bottom: 0px; padding-top: 0px; padding-bottom: 0px;'>
                    Welcome to KINYO AI Video Generation Platform
                </h1>
            """, unsafe_allow_html=True)
    else:
        st.title("🎮 Welcome to KINYO AI Video Generation Platform")
    
    st.markdown("""
    ### Unified AI-Powered Video Creation Pipeline
    
    This platform integrates three powerful AI agents to automate the entire video creation process:
    
    1. **📝 Script Agent**: Generate marketing scripts using RAG-based LLM
    2. **🖼️ Product Keyframes**: Generate product-focused keyframes without humans  
    3. **🎬 Video Agent**: Transform keyframes into final videos with AI
    
    ---
    """)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Quick Start", "📊 Dashboard", "🔄 Workflow", "📁 File Manager"])
    
    with tab1:
        st.markdown("### 🚀 Quick Start Guide")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            #### 1️⃣ Configure API Keys
            Go to **⚙️ Settings** page to configure:
            - K Token / OpenAI API Key
            - DashScope API Key (for embedding)
            - ARK / Seedance API Key (for video)
            """)
            if st.button("⚙️ Go to Settings", use_container_width=True):
                st.switch_page("pages/7_⚙️_设置.py")
        
        with col2:
            st.markdown("""
            #### 2️⃣ Generate Characters
            Go to **👤 Character Generation** page:
            - Create characters with face grid
            - Upload product images
            - Prepare TV screen backgrounds
            """)
            if st.button("👤 Generate Characters", use_container_width=True):
                st.switch_page("pages/2_👤_人物生成.py")
        
        with col3:
            st.markdown("""
            #### 3️⃣ Generate Script
            Go to **📝 Script Generation** page:
            - Input your marketing brief
            - Select objective (ROI/Completion Rate)
            - Click generate button
            """)
            if st.button("📝 Generate Script", use_container_width=True):
                st.switch_page("pages/3_📝_脚本生成.py")
        
        st.divider()
        
        st.markdown("### 🎯 Typical Workflow")
        
        workflow_steps = [
            ("👤 Character Agent", "Generate characters with face grid mask", "pages/2_👤_人物生成.py"),
            ("📝 Script Agent", "Generate script from brief using RAG knowledge base", "pages/3_📝_脚本生成.py"),
            ("🖼️ Product Keyframes", "Generate product-focused keyframes without humans", "pages/4_🖼️_关键帧生成.py"),
            ("🎬 Video Agent", "Generate final video with AI", "pages/5_🎬_视频生成.py")
        ]
        
        for idx, (title, desc, page) in enumerate(workflow_steps, 1):
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.markdown(f"#### Step {idx}")
            
            with col2:
                st.markdown(f"**{title}**: {desc}")
        
        st.divider()
        
        st.markdown("### 💡 Tips")
        st.info("""
        - **First time?** Start with Character Generation to create your characters
        - **Need to manage files?** Check the File Manager tab below
        - **Having issues?** Verify your API keys in Settings
        """)
    
    with tab2:
        st.markdown("### 📊 Dashboard Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Scripts Generated",
                value=stats.get("script_count", 0),
                delta=None
            )
        
        with col2:
            st.metric(
                label="Keyframes Created",
                value=stats.get("storyboard_count", 0),
                delta=None
            )
        
        with col3:
            st.metric(
                label="Videos Generated",
                value=stats.get("video_count", 0),
                delta=None
            )
        
        with col4:
            st.metric(
                label="Full Pipelines",
                value=stats.get("full_pipeline_count", 0),
                delta=None
            )
        
        st.divider()
        
        st.markdown("#### Recent Activity")
        
        history = db.get_all_history(limit=5)
        
        if history:
            for record in history:
                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])
                    
                    with col1:
                        st.text(record.get("timestamp", "")[:19].replace("T", " "))
                    
                    with col2:
                        record_type = record.get("type", "unknown")
                        brief = record.get("brief", record.get("source_file", "N/A"))[:50]
                        st.text(f"[{record_type.upper()}] {brief}...")
                    
                    with col3:
                        if record.get("file_path"):
                            st.caption(f"✓ Saved")
        else:
            st.info("No recent activity. Start generating content!")
    
    with tab3:
        st.markdown("### 🔄 Complete Workflow")
        
        from streamlit_app.components.progress_tracker import ProgressTracker
        
        stages = SessionStateManager.WORKFLOW_STAGES
        current_stage = SessionStateManager.get_workflow_stage()
        
        ProgressTracker.render_workflow_progress(stages, current_stage)
        
        st.divider()
        
        st.markdown("#### Workflow Details")
        
        stage_descriptions = {
            "initialized": "Ready to start generating content",
            "script_generated": "Script has been generated and saved",
            "storyboard_generated": "Storyboard and keyframes have been created",
            "video_generated": "Final video has been generated",
            "completed": "Complete pipeline finished successfully"
        }
        
        for stage in stages:
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if stage == current_stage:
                    st.info(f"🔄 {stage}")
                elif stages.index(stage) < stages.index(current_stage):
                    st.success(f"✓ {stage}")
                else:
                    st.text(f"⚪ {stage}")
            
            with col2:
                st.markdown(f"**{stage_descriptions.get(stage, '')}**")
    
    with tab4:
        st.markdown("### 📁 File Manager")
        
        from streamlit_app.components.file_manager import FileManager
        import pandas as pd
        
        output_files = FileManager.list_output_files("outputs")
        
        categories = ["scripts", "storyboards", "videos", "others"]
        
        for category in categories:
            files = output_files.get(category, [])
            
            if files:
                st.markdown(f"#### {category.title()} ({len(files)})")
                
                # Create a fixed-height scrollable container
                container_height = min(400, max(200, len(files) * 60))
                
                with st.container(height=container_height):
                    for file_path in files:
                        info = FileManager.file_info(file_path)
                        
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.text(info.get("name", ""))
                        
                        with col2:
                            st.caption(f"{info.get('size_mb', 0):.2f} MB")
                        
                        with col3:
                            if category == "videos":
                                try:
                                    with open(file_path, 'rb') as f:
                                        st.download_button(
                                            label="Download",
                                            data=f.read(),
                                            file_name=info.get("name", ""),
                                            mime="video/mp4",
                                            key=f"dl_{category}_{info.get('name', '')}"
                                        )
                                except Exception as e:
                                    st.caption("N/A")
                
                st.divider()


if __name__ == "__main__":
    main()

"""
Settings Page
API Key management, default parameters, and knowledge base management
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.components.api_key_manager import APIKeyManager


def render_model_settings(config: ConfigManager):
    """Render model configuration settings"""
    st.subheader("Model Configuration")
    
    models = config.get_all_config().get("models", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Language Models")
        
        script_model = st.text_input(
            "Script Generation Model",
            value=models.get("script_generation", ""),
            key="setting_script_model"
        )
        
        if st.button("Save Script Model", key="save_script_model"):
            config.set_model("script_generation", script_model)
            st.success("Script model saved!")
        
        embedding_model = st.text_input(
            "Embedding Model",
            value=models.get("embedding", ""),
            key="setting_embedding_model"
        )
        
        if st.button("Save Embedding Model", key="save_embedding_model"):
            config.set_model("embedding", embedding_model)
            st.success("Embedding model saved!")
    
    with col2:
        st.markdown("#### Media Models")
        
        image_model = st.text_input(
            "Image Generation Model",
            value=models.get("image_generation", ""),
            key="setting_image_model"
        )
        
        if st.button("Save Image Model", key="save_image_model"):
            config.set_model("image_generation", image_model)
            st.success("Image model saved!")
        
        video_model = st.text_input(
            "Video Generation Model",
            value=models.get("video_generation", ""),
            key="setting_video_model"
        )
        
        if st.button("Save Video Model", key="save_video_model"):
            config.set_model("video_generation", video_model)
            st.success("Video model saved!")


def render_default_parameters(config: ConfigManager):
    """Render default parameter settings"""
    st.subheader("Default Parameters")
    
    defaults = config.get_all_config().get("defaults", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Script Generation")
        
        script_duration = st.number_input(
            "Default Duration (sec)",
            min_value=10,
            max_value=120,
            value=defaults.get("script_duration", 30),
            step=5,
            key="setting_script_duration"
        )
        
        script_objective = st.selectbox(
            "Default Objective",
            options=["roi", "completion_rate", "balanced"],
            index=["roi", "completion_rate", "balanced"].index(defaults.get("script_objective", "roi")),
            format_func=lambda x: {"roi": "ROI / Conversion", "completion_rate": "Completion Rate", "balanced": "Balanced"}[x],
            key="setting_script_objective"
        )
    
    with col2:
        st.markdown("#### Storyboard")
        
        max_shots = st.slider(
            "Default Max Shots",
            min_value=3,
            max_value=20,
            value=defaults.get("max_shots", 10),
            step=1,
            key="setting_max_shots"
        )
    
    with col3:
        st.markdown("#### Video Generation")
        
        video_duration = st.slider(
            "Default Video Duration (sec)",
            min_value=3,
            max_value=15,
            value=defaults.get("video_duration", 5),
            step=1,
            key="setting_video_duration"
        )
        
        aspect_ratio = st.selectbox(
            "Default Aspect Ratio",
            options=["9:16", "16:9", "1:1", "4:3"],
            index=["9:16", "16:9", "1:1", "4:3"].index(defaults.get("aspect_ratio", "9:16")),
            key="setting_aspect_ratio"
        )
    
    if st.button("Save All Defaults", type="primary", use_container_width=True):
        config.set_default("script_duration", script_duration)
        config.set_default("script_objective", script_objective)
        config.set_default("max_shots", max_shots)
        config.set_default("video_duration", video_duration)
        config.set_default("aspect_ratio", aspect_ratio)
        
        SessionStateManager.set_setting("script_duration", script_duration)
        SessionStateManager.set_setting("script_objective", script_objective)
        SessionStateManager.set_setting("max_shots", max_shots)
        SessionStateManager.set_setting("video_duration", video_duration)
        SessionStateManager.set_setting("aspect_ratio", aspect_ratio)
        
        st.success("All default parameters saved!")


def render_knowledge_base_settings(config: ConfigManager):
    """Render knowledge base management settings"""
    st.subheader("Knowledge Base Management")
    
    kb_path = config.get_path("knowledge_base")
    script_agent_path = config.get_path("script_agent")
    vector_db_path = script_agent_path / "vector_db" if script_agent_path else None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Knowledge Base Directory")
        
        if kb_path and kb_path.exists():
            st.success(f"Path: {kb_path}")
            
            kb_files = list(kb_path.rglob("*"))
            file_count = len([f for f in kb_files if f.is_file()])
            
            st.metric("Files", file_count)
            
            with st.expander("View Files", expanded=False):
                for f in sorted(kb_files)[:20]:
                    if f.is_file():
                        st.text(f"  {f.relative_to(kb_path)}")
                
                if len(kb_files) > 20:
                    st.text(f"  ... and {len(kb_files) - 20} more")
        else:
            st.error(f"Knowledge base not found: {kb_path}")
    
    with col2:
        st.markdown("#### Vector Database")
        
        if vector_db_path and vector_db_path.exists():
            st.success(f"Path: {vector_db_path}")
            
            index_files = list(vector_db_path.glob("*.index"))
            npz_files = list(vector_db_path.glob("*.npz"))
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric("Index Files", len(index_files))
            
            with col_b:
                st.metric("NPZ Files", len(npz_files))
            
            if index_files:
                with st.expander("Index Files", expanded=False):
                    for f in index_files:
                        st.text(f"  {f.name}")
        else:
            st.warning(f"Vector database not found: {vector_db_path}")
    
    st.divider()
    
    st.markdown("#### Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Build Vector Index", use_container_width=True):
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
    
    with col2:
        if st.button("Refresh Statistics", use_container_width=True):
            st.rerun()
    
    with col3:
        if vector_db_path and vector_db_path.exists():
            if st.button("Open Vector DB Folder", use_container_width=True):
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    subprocess.run(["explorer", str(vector_db_path)])
                elif platform.system() == "Darwin":
                    subprocess.run(["open", str(vector_db_path)])
                else:
                    subprocess.run(["xdg-open", str(vector_db_path)])


def render_paths_settings(config: ConfigManager):
    """Render path configuration settings"""
    st.subheader("Path Configuration")
    
    paths = config.get_all_config().get("paths", {})
    
    path_data = []
    
    for name, path in paths.items():
        if path:
            path_obj = Path(path)
            exists = path_obj.exists() if path_obj else False
            
            path_data.append({
                "Name": name,
                "Path": str(path)[-50:] if path else "N/A",
                "Exists": "✓" if exists else "✗"
            })
    
    if path_data:
        import pandas as pd
        df = pd.DataFrame(path_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(
        page_title="设置 - KINYO AI",
        page_icon="⚙️",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    
    config = ConfigManager()
    
    st.title("⚙️ Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔑 API Keys",
        "🤖 Models & Parameters",
        "📚 Knowledge Base",
        "📁 Paths"
    ])
    
    with tab1:
        st.markdown("### API Keys Configuration")
        
        APIKeyManager.display_validation_status()
        
        st.divider()
        
        APIKeyManager.render_all_api_keys()
    
    with tab2:
        render_model_settings(config)
        
        st.divider()
        
        render_default_parameters(config)
    
    with tab3:
        render_knowledge_base_settings(config)
    
    with tab4:
        render_paths_settings(config)
        
        st.divider()
        
        st.markdown("### Project Root")
        
        st.code(str(config.project_root))
        
        st.markdown("### Environment File")
        
        if config.env_file.exists():
            st.success(f"Found: {config.env_file}")
        else:
            st.warning(f"Not found: {config.env_file}")
            st.info("Create a .env file to store API keys and configuration")


if __name__ == "__main__":
    main()

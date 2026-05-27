"""
Dashboard Overview Page
System status and quick access to features
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase


def main():
    st.set_page_config(
        page_title="概览 - KINYO AI",
        page_icon="📊",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    
    config = ConfigManager()
    db = HistoryDatabase()
    
    st.title("📊 Dashboard Overview")
    
    tab1, tab2, tab3 = st.tabs(["📈 Statistics", "🔧 System Status", "📂 Recent Files"])
    
    with tab1:
        st.markdown("### 📈 Generation Statistics")
        
        stats = db.get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📝 Scripts Generated",
                value=stats.get("script_count", 0)
            )
        
        with col2:
            st.metric(
                label="🖼️ Storyboards Created",
                value=stats.get("storyboard_count", 0)
            )
        
        with col3:
            st.metric(
                label="🎬 Videos Generated",
                value=stats.get("video_count", 0)
            )
        
        with col4:
            st.metric(
                label="⚡ Complete Pipelines",
                value=stats.get("full_pipeline_count", 0)
            )
        
        st.divider()
        
        st.markdown("#### Generation History")
        
        history = db.get_all_history(limit=20)
        
        if history:
            import pandas as pd
            
            df_data = []
            for record in history:
                df_data.append({
                    "Type": record.get("type", "").upper(),
                    "Timestamp": record.get("timestamp", "")[:19].replace("T", " "),
                    "Brief/Source": record.get("brief", record.get("source_file", "N/A"))[:60],
                    "File Path": record.get("file_path", "N/A")[-40:] if record.get("file_path") else "N/A"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        else:
            st.info("No generation history yet. Start creating content!")
    
    with tab2:
        st.markdown("### 🔧 System Status")
        
        st.markdown("#### API Keys Configuration")
        
        api_keys_status = {
            "K Token API": bool(config.get_api_key("k_token")),
            "OpenAI API": bool(config.get_api_key("openai")),
            "DashScope API": bool(config.get_api_key("dashscope")),
            "ARK API": bool(config.get_api_key("ark")),
            "Seedance API": bool(config.get_api_key("seedance")),
        }
        
        for api_name, is_configured in api_keys_status.items():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if is_configured:
                    st.success("✓")
                else:
                    st.error("✗")
            
            with col2:
                st.markdown(f"**{api_name}**")
        
        st.divider()
        
        st.markdown("#### Knowledge Base Status")
        
        kb_path = config.get_path("knowledge_base")
        
        if kb_path and kb_path.exists():
            st.success("✓ Knowledge base directory exists")
            
            kb_files = list(kb_path.rglob("*"))
            st.info(f"Found {len(kb_files)} files in knowledge base")
        else:
            st.warning("✗ Knowledge base directory not found")
        
        st.divider()
        
        st.markdown("#### Vector Database Status")
        
        vector_db_path = config.get_path("script_agent") / "vector_db"
        
        if vector_db_path and vector_db_path.exists():
            st.success("✓ Vector database directory exists")
            
            index_files = list(vector_db_path.glob("*.index")) + list(vector_db_path.glob("*.npz"))
            
            if index_files:
                st.info(f"Found {len(index_files)} index files")
            else:
                st.warning("No index files found. Run --build-index to create them.")
        else:
            st.warning("✗ Vector database directory not found")
        
        st.divider()
        
        st.markdown("#### Output Directory Status")
        
        outputs_path = config.get_path("outputs")
        
        if outputs_path and outputs_path.exists():
            st.success("✓ Output directory exists")
            
            import os
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(outputs_path)
                for filename in filenames
            )
            
            st.info(f"Output directory size: {total_size / (1024 * 1024):.2f} MB")
        else:
            st.warning("✗ Output directory not found")
    
    with tab3:
        st.markdown("### 📂 Recent Files")
        
        from streamlit_app.components.file_manager import FileManager
        
        output_files = FileManager.list_output_files("outputs")
        
        categories = {
            "📝 Scripts": "scripts",
            "🖼️ Storyboards": "storyboards",
            "🎬 Videos": "videos",
            "📄 Other Files": "others"
        }
        
        for category_name, category_key in categories.items():
            files = output_files.get(category_key, [])
            
            if files:
                st.markdown(f"#### {category_name} ({len(files)} files)")
                
                for file_path in files[:10]:
                    info = FileManager.file_info(file_path)
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.text(info.get("name", str(file_path)))
                    
                    with col2:
                        st.caption(f"{info.get('size_mb', 0):.2f} MB")
                    
                    with col3:
                        st.caption(info.get("modified", 0))
                
                st.divider()
        
        if not any(output_files.values()):
            st.info("No output files yet. Start generating content!")


if __name__ == "__main__":
    main()

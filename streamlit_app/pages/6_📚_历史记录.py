"""
History Page
View and manage all generation history
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
from streamlit_app.components.file_manager import FileManager


def render_history_table(history: list, db: HistoryDatabase):
    """Render history as a filterable table"""
    if not history:
        st.info("No history records found")
        return
    
    df_data = []
    for record in history:
        record_type = record.get("type", "unknown")
        
        df_data.append({
            "ID": record.get("id", 0),
            "Type": record_type.upper(),
            "Timestamp": record.get("timestamp", "")[:19].replace("T", " "),
            "Brief/Source": (record.get("brief") or record.get("source_file") or "N/A")[:60] + "...",
            "Output": (record.get("file_path") or "N/A")[-35:] if record.get("file_path") else "N/A",
            "_type": record_type
        })
    
    df = pd.DataFrame(df_data)
    
    type_filter = st.multiselect(
        "Filter by Type",
        options=["SCRIPT", "STORYBOARD", "VIDEO"],
        default=["SCRIPT", "STORYBOARD", "VIDEO"],
        key="history_type_filter"
    )
    
    if type_filter:
        df = df[df["Type"].isin(type_filter)]
    
    if df.empty:
        st.info("No records match the filter")
        return None
    
    st.dataframe(
        df[["ID", "Type", "Timestamp", "Brief/Source", "Output"]],
        use_container_width=True,
        hide_index=True
    )
    
    return df


def main():
    st.set_page_config(
        page_title="历史记录 - KINYO AI",
        page_icon="📚",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    
    config = ConfigManager()
    db = HistoryDatabase()
    
    st.title("📚 Generation History")
    
    tab1, tab2, tab3 = st.tabs(["📋 All History", "🔍 Search", "📊 Statistics"])
    
    with tab1:
        col1, col2 = st.columns([3, 1])
        
        with col2:
            limit = st.slider(
                "Records per page",
                min_value=10,
                max_value=100,
                value=50,
                step=10
            )
        
        history = db.get_all_history(limit=limit)
        
        if history:
            df = render_history_table(history, db)
        else:
            st.info("No generation history yet. Start creating content!")
    
    with tab2:
        st.markdown("### Search History")
        
        search_query = st.text_input(
            "Search Query",
            placeholder="Enter keywords to search in brief, source file...",
            key="history_search_input"
        )
        
        search_type = st.selectbox(
            "Filter by Type",
            options=["All", "Script", "Storyboard", "Video"],
            index=0,
            key="search_type_filter"
        )
        
        if st.button("Search", type="primary"):
            if search_query:
                type_filter = None if search_type == "All" else search_type.lower()
                results = db.search_history(search_query, type_filter)
                
                if results:
                    st.success(f"Found {len(results)} matching records")
                    
                    for record in results:
                        with st.expander(
                            f"{record.get('type', '').upper()} | {record.get('timestamp', '')[:19]} | ID: {record.get('id')}",
                            expanded=False
                        ):
                            brief = record.get("brief") or record.get("source_file") or "N/A"
                            st.markdown(f"**Brief/Source**: {brief[:200]}")
                else:
                    st.warning("No matching records found")
            else:
                st.warning("Please enter a search query")
    
    with tab3:
        st.markdown("### Statistics Overview")
        
        stats = db.get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📝 Scripts",
                value=stats.get("script_count", 0)
            )
        
        with col2:
            st.metric(
                label="🖼️ Storyboards",
                value=stats.get("storyboard_count", 0)
            )
        
        with col3:
            st.metric(
                label="🎬 Videos",
                value=stats.get("video_count", 0)
            )
        
        with col4:
            st.metric(
                label="⚡ Full Pipelines",
                value=stats.get("full_pipeline_count", 0)
            )
        
        st.divider()
        
        st.markdown("### Bulk Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Delete Records")
            
            delete_type = st.selectbox(
                "Type to Delete",
                options=["script", "storyboard", "video"],
                key="delete_type_select"
            )
            
            delete_id = st.number_input(
                "Record ID",
                min_value=1,
                value=1,
                step=1,
                key="delete_id_input"
            )
            
            confirm_delete = st.checkbox(
                "I confirm I want to delete this record",
                key="delete_confirm"
            )
            
            if st.button(
                "Delete Record",
                type="secondary",
                disabled=not confirm_delete,
                use_container_width=True
            ):
                if db.delete_record(delete_type, delete_id):
                    st.success("Record deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete record")
        
        with col2:
            st.markdown("#### Export History")
            
            export_format = st.selectbox(
                "Export Format",
                options=["JSON", "CSV"],
                key="export_format_select"
            )
            
            if st.button("Export All History", use_container_width=True):
                all_history = db.get_all_history(limit=1000)
                
                if all_history:
                    if export_format == "JSON":
                        export_data = json.dumps(all_history, ensure_ascii=False, indent=2)
                        filename = "generation_history.json"
                        mime = "application/json"
                    else:
                        df = pd.DataFrame(all_history)
                        export_data = df.to_csv(index=False)
                        filename = "generation_history.csv"
                        mime = "text/csv"
                    
                    st.download_button(
                        label="📥 Download Export",
                        data=export_data,
                        file_name=filename,
                        mime=mime,
                        use_container_width=True
                    )
                else:
                    st.warning("No history to export")
        
        with col3:
            st.markdown("#### Database Management")
            
            if st.button("Refresh Statistics", use_container_width=True):
                st.rerun()
            
            db_path = config.get_path("database") / "kinuyo_history.db"
            
            if db_path.exists():
                db_size = db_path.stat().st_size / (1024 * 1024)
                st.metric("Database Size", f"{db_size:.2f} MB")


if __name__ == "__main__":
    main()

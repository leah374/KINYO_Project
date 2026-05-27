"""
Session State Manager
Manages Streamlit session state for cross-page data persistence
"""

from typing import Any, Dict, Optional
import streamlit as st


class SessionStateManager:
    """Manages Streamlit session state for workflow data sharing"""
    
    WORKFLOW_STAGES = [
        "initialized",
        "script_generated",
        "storyboard_generated",
        "video_generated",
        "completed"
    ]
    
    @staticmethod
    def init_session_state():
        """Initialize all session state variables"""
        defaults = {
            "workflow_stage": "initialized",
            "current_brief": "",
            "last_script_result": None,
            "last_storyboard_result": None,
            "last_video_result": None,
            "script_file_path": None,
            "storyboard_file_path": None,
            "video_file_path": None,
            "generation_in_progress": False,
            "current_task": None,
            "progress": 0,
            "logs": [],
            "settings": {
                "script_model": "gpt-5.4",
                "script_objective": "roi",
                "script_duration": 30,
                "max_shots": 10,
                "image_model": "gpt-image-2",
                "video_duration": 5,
                "aspect_ratio": "9:16",
            }
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get session state value"""
        if key not in st.session_state:
            SessionStateManager.init_session_state()
        return st.session_state.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any):
        """Set session state value"""
        st.session_state[key] = value
    
    @staticmethod
    def get_workflow_stage() -> str:
        """Get current workflow stage"""
        return SessionStateManager.get("workflow_stage", "initialized")
    
    @staticmethod
    def set_workflow_stage(stage: str):
        """Set workflow stage"""
        if stage in SessionStateManager.WORKFLOW_STAGES:
            SessionStateManager.set("workflow_stage", stage)
    
    @staticmethod
    def advance_workflow():
        """Advance to next workflow stage"""
        current = SessionStateManager.get_workflow_stage()
        current_idx = SessionStateManager.WORKFLOW_STAGES.index(current)
        if current_idx < len(SessionStateManager.WORKFLOW_STAGES) - 1:
            next_stage = SessionStateManager.WORKFLOW_STAGES[current_idx + 1]
            SessionStateManager.set_workflow_stage(next_stage)
    
    @staticmethod
    def set_script_result(result: Dict):
        """Set script generation result"""
        st.session_state["last_script_result"] = result
        st.session_state["workflow_stage"] = "script_generated"
    
    @staticmethod
    def get_script_result() -> Optional[Dict]:
        """Get last script generation result"""
        return st.session_state.get("last_script_result")
    
    @staticmethod
    def set_storyboard_result(result: Dict):
        """Set storyboard generation result"""
        st.session_state["last_storyboard_result"] = result
        st.session_state["workflow_stage"] = "storyboard_generated"
    
    @staticmethod
    def get_storyboard_result() -> Optional[Dict]:
        """Get last storyboard generation result"""
        return st.session_state.get("last_storyboard_result")
    
    @staticmethod
    def set_video_result(result: Dict):
        """Set video generation result"""
        st.session_state["last_video_result"] = result
        st.session_state["workflow_stage"] = "video_generated"
    
    @staticmethod
    def get_video_result() -> Optional[Dict]:
        """Get last video generation result"""
        return st.session_state.get("last_video_result")
    
    @staticmethod
    def clear_workflow():
        """Clear all workflow-related session state"""
        keys_to_clear = [
            "workflow_stage",
            "last_script_result",
            "last_storyboard_result",
            "last_video_result",
            "script_file_path",
            "storyboard_file_path",
            "video_file_path",
            "generation_in_progress",
            "current_task",
            "progress",
            "logs",
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        SessionStateManager.init_session_state()
    
    @staticmethod
    def add_log(message: str):
        """Add log message"""
        if "logs" not in st.session_state:
            st.session_state["logs"] = []
        st.session_state["logs"].append(message)
    
    @staticmethod
    def get_logs() -> list:
        """Get all logs"""
        return st.session_state.get("logs", [])
    
    @staticmethod
    def clear_logs():
        """Clear all logs"""
        st.session_state["logs"] = []
    
    @staticmethod
    def set_progress(progress: int, task: Optional[str] = None):
        """Set progress percentage and current task"""
        st.session_state["progress"] = progress
        if task:
            st.session_state["current_task"] = task
    
    @staticmethod
    def get_progress() -> tuple[int, Optional[str]]:
        """Get current progress and task"""
        return (
            st.session_state.get("progress", 0),
            st.session_state.get("current_task")
        )
    
    @staticmethod
    def set_setting(key: str, value: Any):
        """Set a setting value"""
        if "settings" not in st.session_state:
            st.session_state["settings"] = {}
        st.session_state["settings"][key] = value
    
    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """Get a setting value"""
        settings = st.session_state.get("settings", {})
        return settings.get(key, default)

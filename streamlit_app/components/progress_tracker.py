"""
Progress Tracker Component
Real-time progress display with logs
"""

import time
from typing import Callable, Optional

import streamlit as st


class ProgressTracker:
    """Real-time progress tracking component"""
    
    def __init__(self, key: str = "progress"):
        self.key = key
        self.progress_bar = None
        self.status_text = None
        self.log_container = None
        self.logs = []
    
    def init(self):
        """Initialize progress tracker UI elements"""
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.log_container = st.container()
    
    def update(self, progress: int, message: Optional[str] = None):
        """Update progress"""
        if self.progress_bar:
            self.progress_bar.progress(progress)
        
        if message and self.status_text:
            self.status_text.text(message)
    
    def add_log(self, message: str):
        """Add log message"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        
        if self.log_container:
            with self.log_container:
                st.code(log_entry, language="text")
    
    def get_logs(self) -> list:
        """Get all logs"""
        return self.logs
    
    def clear(self):
        """Clear progress tracker"""
        self.logs = []
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()
        if self.log_container:
            self.log_container.empty()
    
    @staticmethod
    def render_workflow_progress(
        stages: list,
        current_stage: str,
        key: str = "workflow_progress"
    ):
        """
        Render workflow progress as a series of steps
        
        Args:
            stages: List of stage names
            current_stage: Name of current stage
        """
        stage_icons = {
            "initialized": "⚪",
            "script_generated": "✅",
            "storyboard_generated": "✅",
            "video_generated": "✅",
            "completed": "✅"
        }
        
        cols = st.columns(len(stages))
        
        for idx, (col, stage) in enumerate(zip(cols, stages)):
            with col:
                if stage == current_stage:
                    st.info(f"🔄 {stage}")
                elif stages.index(stage) < stages.index(current_stage):
                    st.success(f"✓ {stage}")
                else:
                    st.text(f"⚪ {stage}")
    
    @staticmethod
    def render_real_time_progress(
        total_steps: int,
        current_step: int,
        step_name: str,
        logs: Optional[list] = None,
        key: str = "realtime_progress"
    ):
        """
        Render real-time progress indicator
        
        Args:
            total_steps: Total number of steps
            current_step: Current step number
            step_name: Name of current step
            logs: Optional list of log messages
        """
        progress = int((current_step / total_steps) * 100)
        
        st.progress(progress)
        st.text(f"Step {current_step}/{total_steps}: {step_name}")
        
        if logs:
            with st.expander("View Logs", expanded=False):
                for log in logs[-10:]:  # Show last 10 logs
                    st.code(log, language="text")
    
    @staticmethod
    def render_spinner(message: str = "Processing..."):
        """Render context manager for spinner"""
        return st.spinner(message)
    
    @staticmethod
    def render_success(message: str, duration: int = 3):
        """Render success message temporarily"""
        success_placeholder = st.empty()
        success_placeholder.success(f"✓ {message}")
        time.sleep(duration)
        success_placeholder.empty()
    
    @staticmethod
    def render_error(message: str, duration: int = 5):
        """Render error message temporarily"""
        error_placeholder = st.empty()
        error_placeholder.error(f"✗ {message}")
        time.sleep(duration)
        error_placeholder.empty()
    
    @staticmethod
    def render_warning(message: str, duration: int = 4):
        """Render warning message temporarily"""
        warning_placeholder = st.empty()
        warning_placeholder.warning(f"⚠ {message}")
        time.sleep(duration)
        warning_placeholder.empty()
    
    @staticmethod
    def render_countdown(seconds: int, message: str = "Starting in"):
        """Render countdown timer"""
        placeholder = st.empty()
        
        for i in range(seconds, 0, -1):
            placeholder.info(f"{message} {i} seconds...")
            time.sleep(1)
        
        placeholder.empty()
    
    @staticmethod
    def render_progress_with_cancel(
        progress: int,
        message: str,
        cancel_callback: Optional[Callable] = None,
        key: str = "progress_cancel"
    ):
        """
        Render progress with cancel button
        
        Returns:
            True if cancelled, False otherwise
        """
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.progress(progress)
            st.text(message)
        
        with col2:
            if st.button("Cancel", key=key, type="secondary"):
                if cancel_callback:
                    cancel_callback()
                return True
        
        return False


from typing import Tuple

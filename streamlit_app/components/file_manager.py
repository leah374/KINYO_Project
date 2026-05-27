"""
File Manager Component
Handles file upload, selection, and preview functionality
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st


class FileManager:
    """Reusable file management component"""
    
    @staticmethod
    def select_or_upload_file(
        label: str,
        file_types: List[str],
        key: str,
        default_dir: Optional[Path] = None,
        allow_upload: bool = True,
        allow_select: bool = True
    ) -> Tuple[Optional[Path], Optional[Any]]:
        """
        Create a file selection/upload widget
        
        Returns:
            Tuple of (file_path, uploaded_file_object)
        """
        selected_path = None
        uploaded_file = None
        
        col1, col2 = st.columns(2)
        
        with col1:
            choice = st.radio(
                "Input Method",
                options=["Select from Project", "Upload File"] if allow_upload and allow_select else
                        ["Upload File"] if allow_upload else ["Select from Project"],
                key=f"{key}_choice",
                horizontal=True
            )
        
        if choice == "Select from Project" and allow_select:
            if default_dir is None:
                default_dir = Path("outputs")
            
            default_dir = Path(default_dir)
            if not default_dir.exists():
                st.warning(f"Directory not found: {default_dir}")
                return None, None
            
            files = []
            for ext in file_types:
                files.extend(default_dir.rglob(f"*{ext}"))
            
            if not files:
                st.warning(f"No files found in {default_dir}")
                return None, None
            
            file_options = [str(f.relative_to(default_dir.parent)) for f in files]
            selected = st.selectbox(
                label,
                options=file_options,
                key=f"{key}_select"
            )
            
            if selected:
                selected_path = default_dir.parent / selected
                st.info(f"Selected: {selected}")
        
        elif choice == "Upload File" and allow_upload:
            uploaded_file = st.file_uploader(
                label,
                type=file_types,
                key=f"{key}_upload"
            )
            
            if uploaded_file:
                st.success(f"Uploaded: {uploaded_file.name}")
        
        return selected_path, uploaded_file
    
    @staticmethod
    def load_json_file(file_path: Optional[Path] = None, uploaded_file: Optional[Any] = None) -> Optional[Dict]:
        """Load JSON data from file path or uploaded file"""
        try:
            if uploaded_file:
                content = uploaded_file.read()
                return json.loads(content)
            elif file_path and file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            st.error(f"Error loading file: {e}")
        
        return None
    
    @staticmethod
    def preview_json(data: Dict, title: str = "Preview", expanded: bool = False):
        """Display JSON preview in expandable section"""
        with st.expander(title, expanded=expanded):
            st.json(data)
    
    @staticmethod
    def download_button(
        data: Any,
        filename: str,
        label: str = "Download",
        mime_type: str = "application/json",
        key: Optional[str] = None
    ):
        """Create a download button for data"""
        if isinstance(data, (dict, list)):
            content = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            content = str(data)
        
        st.download_button(
            label=label,
            data=content,
            file_name=filename,
            mime=mime_type,
            key=key
        )
    
    @staticmethod
    def list_output_files(directory: str = "outputs") -> Dict[str, List[Path]]:
        """List all output files by category"""
        outputs = {
            "scripts": [],
            "storyboards": [],
            "videos": [],
            "others": []
        }
        
        output_dir = Path(directory)
        if not output_dir.exists():
            return outputs
        
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                if "final_script" in str(file_path):
                    outputs["scripts"].append(file_path)
                elif "keyframes" in str(file_path) and file_path.suffix == ".json":
                    outputs["storyboards"].append(file_path)
                elif "videos" in str(file_path) and file_path.suffix in [".mp4", ".avi", ".mov"]:
                    outputs["videos"].append(file_path)
                else:
                    outputs["others"].append(file_path)
        
        for category in outputs:
            outputs[category].sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return outputs
    
    @staticmethod
    def file_info(file_path: Path) -> Dict[str, Any]:
        """Get file information"""
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "extension": file_path.suffix
        }
    
    @staticmethod
    def delete_file(file_path: Path, confirm: bool = False) -> bool:
        """Delete a file with optional confirmation"""
        if not file_path.exists():
            return False
        
        if confirm:
            file_path.unlink()
            return True
        
        return False

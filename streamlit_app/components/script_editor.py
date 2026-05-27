"""
Script Editor Component
Interactive JSON script editor with validation
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st


class ScriptEditor:
    """Interactive script editor component"""
    
    @staticmethod
    def render_editor(
        script_data: Dict[str, Any],
        key: str = "script_editor"
    ) -> Dict[str, Any]:
        """
        Render interactive script editor
        
        Returns:
            Edited script data
        """
        st.markdown("### Script Editor")
        
        edited_data = script_data.copy()
        
        tabs = st.tabs(["Planning", "Script Segments", "Raw JSON"])
        
        with tabs[0]:
            edited_data["planning"] = ScriptEditor._edit_planning(
                script_data.get("planning", {}),
                key=f"{key}_planning"
            )
        
        with tabs[1]:
            edited_data["script"] = ScriptEditor._edit_segments(
                script_data.get("script", {}),
                key=f"{key}_segments"
            )
        
        with tabs[2]:
            edited_data = ScriptEditor._edit_raw_json(
                edited_data,
                key=f"{key}_raw"
            )
        
        return edited_data
    
    @staticmethod
    def _edit_planning(planning: Dict, key: str) -> Dict:
        """Edit planning section"""
        st.markdown("#### Planning")
        
        edited_planning = planning.copy()
        
        edited_planning["target_user"] = st.text_area(
            "Target User",
            value=planning.get("target_user", ""),
            key=f"{key}_target_user",
            height=100
        )
        
        edited_planning["core_selling_point"] = st.text_area(
            "Core Selling Point",
            value=planning.get("core_selling_point", ""),
            key=f"{key}_selling_point",
            height=100
        )
        
        edited_planning["creative_angle"] = st.text_input(
            "Creative Angle",
            value=planning.get("creative_angle", ""),
            key=f"{key}_creative_angle"
        )
        
        edited_planning["core_pain_point"] = st.text_area(
            "Core Pain Point",
            value=planning.get("core_pain_point", ""),
            key=f"{key}_pain_point",
            height=100
        )
        
        return edited_planning
    
    @staticmethod
    def _edit_segments(script: Dict, key: str) -> Dict:
        """Edit script segments"""
        st.markdown("#### Script Segments")
        
        edited_script = script.copy()
        
        if "title" in script:
            edited_script["title"] = st.text_input(
                "Title",
                value=script.get("title", ""),
                key=f"{key}_title"
            )
        
        if "objective" in script:
            edited_script["objective"] = st.text_input(
                "Objective",
                value=script.get("objective", ""),
                key=f"{key}_objective"
            )
        
        segments = script.get("segments", [])
        
        if segments:
            st.markdown("##### Segments")
            
            for idx, segment in enumerate(segments):
                with st.expander(f"Segment {idx + 1}: {segment.get('stage', 'Unknown')}", expanded=(idx == 0)):
                    edited_segment = segment.copy()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edited_segment["stage"] = st.selectbox(
                            "Stage",
                            options=["Hook", "Setup", "Twist", "CTA"],
                            index=["Hook", "Setup", "Twist", "CTA"].index(segment.get("stage", "Hook")),
                            key=f"{key}_seg{idx}_stage"
                        )
                        
                        edited_segment["time"] = st.text_input(
                            "Time",
                            value=segment.get("time", ""),
                            key=f"{key}_seg{idx}_time"
                        )
                        
                        edited_segment["purpose"] = st.text_input(
                            "Purpose",
                            value=segment.get("purpose", ""),
                            key=f"{key}_seg{idx}_purpose"
                        )
                    
                    with col2:
                        edited_segment["visual"] = st.text_area(
                            "Visual",
                            value=segment.get("visual", ""),
                            height=100,
                            key=f"{key}_seg{idx}_visual"
                        )
                        
                        edited_segment["voiceover"] = st.text_area(
                            "Voiceover",
                            value=segment.get("voiceover", ""),
                            height=100,
                            key=f"{key}_seg{idx}_voiceover"
                        )
                    
                    edited_segment["subtitle"] = st.text_input(
                        "Subtitle",
                        value=segment.get("subtitle", ""),
                        key=f"{key}_seg{idx}_subtitle"
                    )
                    
                    edited_segment["shot_hint"] = st.text_input(
                        "Shot Hint",
                        value=segment.get("shot_hint", ""),
                        key=f"{key}_seg{idx}_shot_hint"
                    )
                    
                    segments[idx] = edited_segment
        
        edited_script["segments"] = segments
        
        return edited_script
    
    @staticmethod
    def _edit_raw_json(data: Dict, key: str) -> Dict:
        """Edit raw JSON"""
        st.markdown("#### Raw JSON Editor")
        
        json_str = st.text_area(
            "JSON Content",
            value=json.dumps(data, ensure_ascii=False, indent=2),
            height=400,
            key=f"{key}_text"
        )
        
        try:
            edited_data = json.loads(json_str)
            st.success("✓ Valid JSON")
            return edited_data
        except json.JSONDecodeError as e:
            st.error(f"✗ Invalid JSON: {e}")
            return data
    
    @staticmethod
    def validate_script(script_data: Dict) -> Tuple[bool, list]:
        """Validate script data structure"""
        errors = []
        
        if "planning" not in script_data:
            errors.append("Missing 'planning' field")
        
        if "script" not in script_data:
            errors.append("Missing 'script' field")
        else:
            if "segments" not in script_data["script"]:
                errors.append("Missing 'segments' field in script")
            else:
                for idx, segment in enumerate(script_data["script"]["segments"]):
                    required_fields = ["stage", "visual", "voiceover"]
                    for field in required_fields:
                        if field not in segment:
                            errors.append(f"Segment {idx + 1} missing '{field}'")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def display_validation_errors(errors: list):
        """Display validation errors"""
        if errors:
            st.error("Validation Errors:")
            for error in errors:
                st.error(f"  • {error}")

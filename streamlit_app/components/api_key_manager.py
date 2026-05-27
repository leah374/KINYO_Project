"""
API Key Manager Component
Secure API key display, edit, and testing
"""

from typing import Dict, Optional, Tuple

import streamlit as st

from streamlit_app.utils.config import ConfigManager


class APIKeyManager:
    """Reusable API key management component"""
    
    @staticmethod
    def render_api_key_input(
        key_name: str,
        display_name: str,
        help_text: Optional[str] = None,
        test_on_save: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Render API key input field with test button
        
        Returns:
            Tuple of (success, error_message)
        """
        config = ConfigManager()
        
        current_key = config.get_api_key(key_name)
        
        masked_key = ""
        if current_key:
            masked_key = current_key[:8] + "*" * (len(current_key) - 12) + current_key[-4:] if len(current_key) > 12 else "*" * len(current_key)
        
        st.markdown(f"**{display_name}**")
        
        if current_key:
            st.caption(f"Current: `{masked_key}`")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            new_key = st.text_input(
                f"Enter new {display_name}",
                type="password",
                key=f"api_key_{key_name}_input",
                help=help_text,
                label_visibility="collapsed"
            )
        
        with col2:
            save_button = st.button("Save", key=f"save_{key_name}", use_container_width=True)
        
        with col3:
            test_button = st.button("Test", key=f"test_{key_name}", use_container_width=True)
        
        result_message = st.empty()
        
        if save_button and new_key:
            config.set_api_key(key_name, new_key, save_to_env=True)
            result_message.success(f"✓ {display_name} saved successfully!")
            return True, None
        
        if test_button:
            if not current_key and not new_key:
                result_message.error(f"✗ No API key configured")
                return False, "No API key configured"
            
            test_key = new_key if new_key else current_key
            
            with st.spinner(f"Testing {display_name}..."):
                success, message = config.test_api_connection(key_name)
            
            if success:
                result_message.success(f"✓ Connection successful: {message}")
                return True, None
            else:
                result_message.error(f"✗ Connection failed: {message}")
                return False, message
        
        return False, None
    
    @staticmethod
    def render_all_api_keys():
        """Render all API key management inputs"""
        st.subheader("API Keys Configuration")
        
        api_keys = [
            ("k_token", "K Token API Key", "Required for script generation (LLM)"),
            ("openai", "OpenAI API Key", "Alternative for script generation"),
            ("dashscope", "DashScope API Key", "Required for embedding model"),
            ("ark", "ARK API Key (Volcano)", "Required for video generation"),
            ("seedance", "Seedance API Key", "Alternative for video generation"),
        ]
        
        for key_name, display_name, help_text in api_keys:
            with st.container():
                APIKeyManager.render_api_key_input(key_name, display_name, help_text)
                st.divider()
    
    @staticmethod
    def validate_required_keys() -> Dict[str, bool]:
        """Validate which required API keys are configured"""
        config = ConfigManager()
        
        required_keys = {
            "Script Generation": ["k_token", "openai"],
            "Embedding": ["dashscope"],
            "Video Generation": ["ark", "seedance"],
        }
        
        validation_results = {}
        
        for feature, keys in required_keys.items():
            has_any = any(config.get_api_key(key) for key in keys)
            validation_results[feature] = has_any
        
        return validation_results
    
    @staticmethod
    def display_validation_status():
        """Display API key validation status"""
        validation = APIKeyManager.validate_required_keys()
        
        st.subheader("API Key Status")
        
        cols = st.columns(len(validation))
        
        for idx, (feature, is_valid) in enumerate(validation.items()):
            with cols[idx]:
                if is_valid:
                    st.success(f"✓ {feature}")
                else:
                    st.error(f"✗ {feature}")
    
    @staticmethod
    def get_masked_key(key: str) -> str:
        """Return masked version of API key"""
        if not key or len(key) < 12:
            return "*" * 8 if key else ""
        
        return key[:8] + "*" * (len(key) - 12) + key[-4:]

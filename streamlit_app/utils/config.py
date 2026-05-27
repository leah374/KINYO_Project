"""
Configuration Manager
Manages environment variables, API keys, and application settings
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv


class ConfigManager:
    """Centralized configuration management"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.project_root = Path(__file__).resolve().parents[2]
        self.env_file = self.project_root / ".env"
        
        self._load_env()
        self._init_config()
    
    def _load_env(self):
        """Load environment variables from .env file"""
        if self.env_file.exists():
            load_dotenv(self.env_file)
    
    def _init_config(self):
        """Initialize configuration with defaults"""
        self.config = {
            "api_keys": {
                "k_token": os.getenv("K_TOKEN_API_KEY", ""),
                "openai": os.getenv("OPENAI_API_KEY", ""),
                "dashscope": os.getenv("DASHSCOPE_API_KEY", ""),
                "ark": os.getenv("ARK_API_KEY", ""),
                "seedance": os.getenv("SEEDANCE_API_KEY", ""),
            },
            "models": {
                "script_generation": os.getenv("SCRIPT_MODEL", "gpt-5.4"),
                "embedding": os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
                "image_generation": os.getenv("IMAGE_MODEL", "gpt-image-2"),
                "video_generation": os.getenv("VIDEO_MODEL", "doubao-seedance-2-0-260128"),
            },
            "paths": {
                "script_agent": self.project_root / "script_agent",
                "visual_agent": self.project_root / "visual_agent",
                "video_agent": self.project_root / "video_agent",
                "outputs": self.project_root / "outputs",
                "database": self.project_root / "streamlit_app" / "database",
                "knowledge_base": self.project_root / "script_agent" / "knowledge_base",
                "assets": self.project_root / "assets",
            },
            "defaults": {
                "script_duration": 30,
                "script_objective": "roi",
                "max_shots": 10,
                "video_duration": 5,
                "aspect_ratio": "9:16",
            }
        }
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key by name"""
        return self.config["api_keys"].get(key_name)
    
    def set_api_key(self, key_name: str, value: str, save_to_env: bool = False):
        """Set API key and optionally save to .env file"""
        self.config["api_keys"][key_name] = value
        os.environ[key_name.upper() + "_API_KEY"] = value
        
        if save_to_env:
            self._save_to_env(key_name, value)
    
    def _save_to_env(self, key_name: str, value: str):
        """Save key-value pair to .env file"""
        env_key = key_name.upper() + "_API_KEY"
        
        lines = []
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        found = False
        for i, line in enumerate(lines):
            if line.startswith(env_key + "="):
                lines[i] = f"{env_key}={value}\n"
                found = True
                break
        
        if not found:
            lines.append(f"{env_key}={value}\n")
        
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def get_model(self, model_type: str) -> str:
        """Get model name by type"""
        return self.config["models"].get(model_type, "")
    
    def set_model(self, model_type: str, model_name: str):
        """Set default model for a type"""
        self.config["models"][model_type] = model_name
    
    def get_path(self, path_name: str) -> Path:
        """Get path by name"""
        path = self.config["paths"].get(path_name)
        return Path(path) if path else None
    
    def get_default(self, param_name: str) -> Any:
        """Get default parameter value"""
        return self.config["defaults"].get(param_name)
    
    def set_default(self, param_name: str, value: Any):
        """Set default parameter value"""
        self.config["defaults"][param_name] = value
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self.config
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate which API keys are configured"""
        return {
            key: bool(value) 
            for key, value in self.config["api_keys"].items()
        }
    
    def test_api_connection(self, key_name: str) -> tuple[bool, str]:
        """Test API connection for a given key"""
        key = self.config["api_keys"].get(key_name)
        
        if not key:
            return False, "API key not configured"
        
        try:
            if key_name in ["k_token", "openai"]:
                from openai import OpenAI
                client_kwargs = {"api_key": key}
                if key_name == "k_token":
                    client_kwargs["base_url"] = "https://ai.ktokenhub.app"
                client = OpenAI(**client_kwargs)
                client.models.list()
                return True, "Connection successful"
            
            elif key_name == "dashscope":
                import requests
                response = requests.get(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10
                )
                return response.status_code == 200, "Connection successful" if response.status_code == 200 else f"Failed: {response.status_code}"
            
            elif key_name in ["ark", "seedance"]:
                return True, "API key configured (test not implemented)"
            
            return False, "Unknown API key type"
        
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

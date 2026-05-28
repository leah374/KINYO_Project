"""
Workflow Manager
Manages end-to-end workflow execution and data passing between stages
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# TypedDict extra_items patch (MUST be before langgraph/script_agent import)
try:
    from typing_extensions import _TypedDictMeta
    _original_typeddict_new = _TypedDictMeta.__new__
    
    def _patched_typeddict_new(mcls, name, bases, namespace, **kwargs):
        kwargs.pop('extra_items', None)
        kwargs.pop('closed', None)
        return _original_typeddict_new(mcls, name, bases, namespace, **kwargs)
    
    _TypedDictMeta.__new__ = staticmethod(_patched_typeddict_new)
except: pass

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.database import HistoryDatabase
from streamlit_app.utils.session_state import SessionStateManager


class WorkflowManager:
    """Manages complete workflow execution"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.db = HistoryDatabase()
        self._pause_flag = False
        self._cancel_flag = False
    
    def run_script_generation(
        self,
        brief: str,
        objective: str = "roi",
        duration: int = 30,
        characters: Optional[List[Dict]] = None,
        product_selling_points: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute script generation stage"""
        from script_agent.agent.script_agent import run_agent, save_final_script
        
        if progress_callback:
            progress_callback(0, "Starting script generation...")
        
        try:
            result = run_agent(
                brief=brief,
                objective=objective,
                duration=duration,
                characters=characters,
                product_selling_points=product_selling_points
            )
            
            save_final_script(result)
            
            script_path = self.config.get_path("outputs") / "final_script" / "final_script.json"
            record_id = self.db.save_script_generation(
                brief=brief,
                result=result,
                objective=objective,
                duration=duration,
                file_path=str(script_path)
            )
            
            SessionStateManager.set_script_result(result)
            SessionStateManager.set("script_file_path", str(script_path))
            
            if progress_callback:
                progress_callback(100, "Script generation completed")
            
            return {
                "success": True,
                "result": result,
                "file_path": str(script_path),
                "record_id": record_id
            }
        
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_storyboard_generation(
        self,
        script_data: Optional[Dict] = None,
        script_file_path: Optional[str] = None,
        max_shots: int = 10,
        generate_images: bool = False,
        product_images: Optional[List[str]] = None,
        tv_screens: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute storyboard/keyframe generation stage
        
        Args:
            script_data: Script JSON data
            script_file_path: Path to script file
            max_shots: Maximum number of shots
            generate_images: Whether to generate keyframe images
            product_images: List of product image paths
            tv_screens: List of TV screen image paths
            progress_callback: Callback for progress updates
        """
        from visual_agent.agent.keyframe_storyboard_agent import run as run_storyboard
        
        if progress_callback:
            progress_callback(0, "Starting storyboard generation...")
        
        try:
            if script_data is None and script_file_path:
                import json
                with open(script_file_path, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
            
            if script_data is None:
                script_data = SessionStateManager.get_script_result()
            
            if script_data is None:
                raise ValueError("No script data available")
            
            input_path = SessionStateManager.get("script_file_path")
            if not input_path:
                input_path = self.config.get_path("outputs") / "final_script" / "final_script.json"
            
            output_dir = self.config.get_path("outputs") / "keyframes"
            
            # Get API configuration
            api_key = self.config.get_api_key("k_token") or os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("K_TOKEN_BASE_URL", "https://ai.ktokenhub.app")
            
            # Set environment variable for generate_keyframes to use
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            
            result = run_storyboard(
                input_path=Path(input_path),
                output_dir=output_dir,
                max_shots=max_shots,
                generate_images=generate_images,
                base_url=base_url,
                image_model="gpt-image-2",
                size="auto",
                quality="auto",
                sleep_sec=0.2,
                retries=2,
                overwrite=False,
                skip_shots=[],
                progress_callback=progress_callback,
                product_images=product_images or [],
                tv_screens=tv_screens or []
            )
            
            storyboard_path = output_dir / "storyboard.json"
            
            # Convert Path objects to strings for JSON serialization
            serializable_result = {k: str(v) for k, v in result.items()}
            
            record_id = self.db.save_storyboard_generation(
                result={"storyboard_path": str(storyboard_path), "paths": serializable_result},
                source_file=str(input_path),
                file_path=str(storyboard_path)
            )
            
            SessionStateManager.set_storyboard_result({"path": str(storyboard_path)})
            SessionStateManager.set("storyboard_file_path", str(storyboard_path))
            
            if progress_callback:
                progress_callback(100, "Storyboard generation completed")
            
            return {
                "success": True,
                "result": result,
                "file_path": str(storyboard_path),
                "record_id": record_id
            }
        
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_video_generation(
        self,
        storyboard_data: Optional[Dict] = None,
        storyboard_file_path: Optional[str] = None,
        keyframe_dir: Optional[str] = None,
        generate_audio: bool = True,
        concat: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute video generation stage"""
        from video_agent.agent.seedance_video_agent import run as run_video
        
        if progress_callback:
            progress_callback(0, "Starting video generation...")
        
        try:
            if storyboard_file_path is None:
                storyboard_file_path = SessionStateManager.get("storyboard_file_path")
            
            if storyboard_file_path is None:
                storyboard_file_path = self.config.get_path("outputs") / "keyframes" / "storyboard.json"
            
            if keyframe_dir is None:
                keyframe_dir = self.config.get_path("outputs") / "keyframes" / "images"
            
            output_dir = self.config.get_path("outputs") / "videos"
            
            # ARK/Seedance API key is read from environment in seedance_video_agent
            # Defaults are already set in the agent:
            # - base_url: https://ark.cn-beijing.volces.com/api/v3
            # - model: doubao-seedance-2-0-260128
            
            import argparse
            args = argparse.Namespace(
                storyboard=str(storyboard_file_path),
                keyframe_dir=str(keyframe_dir),
                output_dir=str(output_dir),
                submit=True,
                base_url=os.getenv("SEEDANCE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                model=os.getenv("SEEDANCE_MODEL", "doubao-seedance-2-0-260128"),
                ratio="9:16",
                resolution="",
                duration=self.config.get_default("video_duration") or 5,
                image_mode="base64",
                generate_audio=generate_audio,
                watermark=False,
                camera_fixed=False,
                use_last_frame=False,
                only_shots="",
                skip_shots="",
                callback_url="",
                overwrite=False,
                poll_interval=10,
                timeout=900,
                concat=concat,
                compatible_output=True
            )
            
            result = run_video(args)
            
            video_path = output_dir / "final_seedance_video_compatible.mp4"
            record_id = self.db.save_video_generation(
                result=result,
                source_file=str(storyboard_file_path),
                file_path=str(video_path)
            )
            
            SessionStateManager.set_video_result({"path": str(video_path)})
            SessionStateManager.set("video_file_path", str(video_path))
            
            if progress_callback:
                progress_callback(100, "Video generation completed")
            
            return {
                "success": True,
                "result": result,
                "file_path": str(video_path),
                "record_id": record_id
            }
        
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_full_pipeline(
        self,
        brief: str,
        objective: str = "roi",
        duration: int = 30,
        max_shots: int = 10,
        generate_audio: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute complete pipeline from brief to video"""
        start_time = time.time()
        results = {}
        
        if progress_callback:
            progress_callback(0, "Starting full pipeline...")
        
        script_result = self.run_script_generation(
            brief=brief,
            objective=objective,
            duration=duration,
            progress_callback=lambda p, m: progress_callback(int(p * 0.3), f"[Script] {m}") if progress_callback else None
        )
        
        if not script_result["success"]:
            return script_result
        
        results["script"] = script_result
        
        storyboard_result = self.run_storyboard_generation(
            script_data=script_result.get("result"),
            max_shots=max_shots,
            generate_images=True,
            progress_callback=lambda p, m: progress_callback(30 + int(p * 0.3), f"[Storyboard] {m}") if progress_callback else None
        )
        
        if not storyboard_result["success"]:
            return storyboard_result
        
        results["storyboard"] = storyboard_result
        
        video_result = self.run_video_generation(
            storyboard_file_path=storyboard_result.get("file_path"),
            generate_audio=generate_audio,
            concat=True,
            progress_callback=lambda p, m: progress_callback(60 + int(p * 0.4), f"[Video] {m}") if progress_callback else None
        )
        
        if not video_result["success"]:
            return video_result
        
        results["video"] = video_result
        
        total_duration = time.time() - start_time
        
        full_pipeline_id = self.db.save_full_pipeline(
            brief=brief,
            script_id=script_result["record_id"],
            storyboard_id=storyboard_result["record_id"],
            video_id=video_result["record_id"],
            total_duration=total_duration
        )
        
        if progress_callback:
            progress_callback(100, f"Full pipeline completed in {total_duration:.1f}s")
        
        return {
            "success": True,
            "results": results,
            "total_duration": total_duration,
            "full_pipeline_id": full_pipeline_id
        }
    
    def pause(self):
        """Pause the workflow"""
        self._pause_flag = True
    
    def resume(self):
        """Resume the workflow"""
        self._pause_flag = False
    
    def cancel(self):
        """Cancel the workflow"""
        self._cancel_flag = True
    
    def reset(self):
        """Reset workflow state"""
        self._pause_flag = False
        self._cancel_flag = False

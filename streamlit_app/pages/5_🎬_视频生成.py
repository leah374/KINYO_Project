"""
Video Generation Page
Generate video segments using Seedance with character and last frame support
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase
from streamlit_app.components.file_manager import FileManager
from video_agent.agent.video_segment_generator import (
    load_characters,
    build_initial_prompt,
    build_image_index_map,
    optimize_prompt_with_gpt,
    generate_all_segments,
    concatenate_videos_ffmpeg,
    make_compatible_video,
    SegmentConfig
)


def render_character_selection(characters_dir: Path, key_prefix: str = "char_select"):
    """
    Render character selection UI with both masked and full images
    
    Args:
        characters_dir: Directory containing character folders
        key_prefix: Prefix for widget keys
    
    Returns:
        List of selected character dictionaries with chosen image paths
    """
    characters = load_characters(characters_dir)
    
    if not characters:
        st.warning("未找到人物。请先在人物生成页面创建人物。")
        return []
    
    st.markdown(f"**已有 {len(characters)} 个人物**")
    
    selected = []
    
    for char in characters:
        char_id = char["id"]
        img_paths = char.get("image_paths", {})
        
        st.markdown(f"#### {char_id}")
        
        # Display both images side by side
        col1, col2 = st.columns(2)
        
        selected_images = []
        
        with col1:
            if "front_masked" in img_paths:
                st.image(img_paths["front_masked"], caption="front_masked (网格)", use_container_width=True)
                if st.checkbox("使用 front_masked", key=f"{key_prefix}_{char_id}_masked"):
                    selected_images.append("front_masked")
        
        with col2:
            if "front_full" in img_paths:
                st.image(img_paths["front_full"], caption="front_full (完整)", use_container_width=True)
                if st.checkbox("使用 front_full", key=f"{key_prefix}_{char_id}_full"):
                    selected_images.append("front_full")
        
        # Show character description
        if char.get("description"):
            with st.expander("人物描述", expanded=False):
                st.write(char["description"])
        
        # If user selected any image, add to selected list
        if selected_images:
            char_copy = char.copy()
            char_copy["selected_images"] = selected_images
            selected.append(char_copy)
        
        st.divider()
    
    return selected


def render_segment_config(
    segments: list, 
    selected_characters: list, 
    keyframe_dir: Path, 
    product_images: list,
    default_duration: int = 5
):
    """
    Render segment configuration UI with individual duration settings
    
    Args:
        segments: List of script segments
        selected_characters: List of selected character dictionaries
        keyframe_dir: Directory containing keyframe images
        product_images: List of uploaded product image paths
        default_duration: Default duration for each segment
    
    Returns:
        List of segment assignment dictionaries
    """
    assignments = []
    
    character_map = {c["id"]: c for c in selected_characters}
    product_map = {Path(p).stem: p for p in product_images}
    
    for idx, seg in enumerate(segments):
        stage = seg.get("stage", f"Segment {idx + 1}")
        time_range = seg.get("time", "")
        
        with st.container(border=True):
            st.markdown(f"### 🎬 {stage}")
            st.caption(f"⏱ 时间段: {time_range}")
            
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.markdown("**人物选择**")
                selected_chars = st.multiselect(
                    "选择人物",
                    options=[c["id"] for c in selected_characters],
                    default=[],
                    key=f"seg_char_{idx}",
                    label_visibility="collapsed"
                )
                
                if selected_chars:
                    char_imgs = []
                    for cid in selected_chars:
                        if cid in character_map:
                            char_info = character_map[cid]
                            for img_type in char_info.get("selected_images", ["front_full"]):
                                if img_type in char_info.get("image_paths", {}):
                                    char_imgs.append((cid, char_info["image_paths"][img_type]))
                    
                    if char_imgs:
                        with st.container(height=120):
                            img_cols = st.columns(len(char_imgs))
                            for i, (cid, img_path) in enumerate(char_imgs):
                                with img_cols[i]:
                                    st.image(img_path, width=70, caption=cid[:6])
                else:
                    st.info("未选择人物")
            
            with col_right:
                duration = st.number_input(
                    "时长(秒)",
                    min_value=3,
                    max_value=15,
                    value=default_duration,
                    step=1,
                    key=f"seg_duration_{idx}"
                )
                
                st.markdown("**产品特写**")
                product_options = ["无"] + list(product_map.keys())
                selected_product = st.selectbox(
                    "选择产品图片",
                    options=product_options,
                    index=0,
                    key=f"seg_product_{idx}",
                    label_visibility="collapsed"
                )
                
                if selected_product != "无" and selected_product in product_map:
                    st.image(product_map[selected_product], width=80)
            
            st.markdown("**关键帧**")
            keyframe_path = None
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                candidate = keyframe_dir / f"S{idx + 1:02d}{ext}"
                if candidate.exists():
                    keyframe_path = candidate
                    break
            
            if keyframe_path:
                st.image(str(keyframe_path), width=200)
            else:
                st.warning(f"未找到关键帧 S{idx + 1:02d}")
            
            assignments.append({
                "segment_idx": idx,
                "character_ids": selected_chars,
                "keyframe_path": keyframe_path,
                "duration": duration,
                "product_image": product_map.get(selected_product) if selected_product != "无" else None
            })
    
    return assignments


def render_prompt_editors(
    segments: list,
    assignments: list,
    selected_characters: list,
    character_map: dict
):
    """
    Render prompt editors for each segment with individual optimize button
    
    Args:
        segments: List of script segments
        assignments: List of segment assignments
        selected_characters: List of selected characters
        character_map: Dictionary mapping character ID to character info
    
    Returns:
        List of prompts for each segment
    """
    prompts = []
    
    for idx, (seg, assign) in enumerate(zip(segments, assignments)):
        stage = seg.get("stage", f"Segment {idx + 1}")
        
        with st.expander(f"📝 {stage} - 提示词", expanded=False):
            # Get character info
            char_infos = [character_map[cid] for cid in assign["character_ids"] if cid in character_map]
            
            # Build image index map for this segment
            has_product = assign.get("product_image") is not None
            image_index_map = build_image_index_map(
                has_keyframe=True,
                has_product=has_product,
                character_infos=char_infos
            )
            
            # Build initial prompt with image index map
            product_name = Path(assign["product_image"]).stem if assign.get("product_image") else None
            initial_prompt = build_initial_prompt(
                seg, 
                char_infos, 
                product_name=product_name or "K7家庭K歌主机",
                image_index_map=image_index_map
            )
            
            # Get current prompt from session state or use initial
            current_prompt = st.session_state.get("video_prompts", [])
            if idx < len(current_prompt) and current_prompt[idx]:
                display_prompt = current_prompt[idx]
            else:
                display_prompt = initial_prompt
            
            # Individual optimize button
            col_opt, col_info = st.columns([1, 3])
            with col_opt:
                if st.button(f"🤖 优化此片段", key=f"optimize_single_{idx}", use_container_width=True):
                    with st.spinner(f"正在优化 {stage}..."):
                        try:
                            optimized = optimize_prompt_with_gpt(
                                segment=seg,
                                character_infos=char_infos,
                                initial_prompt=display_prompt,
                                duration=assign["duration"],
                                product_image_name=product_name,
                                image_index_map=image_index_map
                            )
                            # Store both original and optimized
                            if "original_prompts" not in st.session_state:
                                st.session_state["original_prompts"] = []
                            while len(st.session_state["original_prompts"]) <= idx:
                                st.session_state["original_prompts"].append("")
                            st.session_state["original_prompts"][idx] = display_prompt
                            
                            if "video_prompts" not in st.session_state:
                                st.session_state["video_prompts"] = []
                            while len(st.session_state["video_prompts"]) <= idx:
                                st.session_state["video_prompts"].append("")
                            st.session_state["video_prompts"][idx] = optimized
                            st.success(f"✓ {stage} 优化完成")
                            st.rerun()
                        except Exception as e:
                            st.error(f"优化失败: {e}")
                            st.info("请检查 API Key 是否正确设置（K_TOKEN_API_KEY 环境变量）")
                        st.session_state["video_prompts"][idx] = optimized
                        st.rerun()
            
            with col_info:
                # Display image mapping info
                img_mapping = [f"图片{v}={k.split('_')[0] if '_' in k else k}" for k, v in sorted(image_index_map.items(), key=lambda x: x[1])]
                st.caption(f"时长: {assign['duration']}s | 人物数: {len(char_infos)} | 图片映射: {', '.join(img_mapping)}")
            
            # Show comparison if this segment was optimized
            original_prompts = st.session_state.get("original_prompts", [])
            if idx < len(original_prompts) and original_prompts[idx]:
                with st.container(border=True):
                    st.markdown("**📊 优化对比**")
                    col_before, col_after = st.columns(2)
                    with col_before:
                        st.markdown("*优化前:*")
                        st.text_area(
                            "原始提示词",
                            value=original_prompts[idx],
                            height=150,
                            key=f"original_preview_{idx}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    with col_after:
                        st.markdown("*优化后:*")
                        st.text_area(
                            "优化后提示词",
                            value=display_prompt,
                            height=150,
                            key=f"optimized_preview_{idx}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
            
            # Editable text area
            prompt = st.text_area(
                f"提示词编辑",
                value=display_prompt,
                height=200,
                key=f"prompt_editor_{idx}",
                label_visibility="collapsed"
            )
            
            # Segment info display
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"**画面**: {seg.get('visual', '-')[:50]}...")
            with col2:
                st.caption(f"**口播**: {seg.get('voiceover', '-')[:50]}...")
            
            prompts.append(prompt)
    
    return prompts


def main():
    st.set_page_config(
        page_title="视频生成 - KINYO AI",
        page_icon="🎬",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    config = ConfigManager()
    db = HistoryDatabase()
    
    st.title("🎬 视频生成")
    st.markdown("使用 Seedance API 生成连贯的视频片段")
    
    # Initialize session state
    if "video_prompts" not in st.session_state:
        st.session_state["video_prompts"] = []
    if "original_prompts" not in st.session_state:
        st.session_state["original_prompts"] = []
    if "prompts_optimized" not in st.session_state:
        st.session_state["prompts_optimized"] = False
    if "generation_mode" not in st.session_state:
        st.session_state["generation_mode"] = "batch"
    if "current_segment_idx" not in st.session_state:
        st.session_state["current_segment_idx"] = 0
    if "generated_results" not in st.session_state:
        st.session_state["generated_results"] = []
    if "last_frame_path" not in st.session_state:
        st.session_state["last_frame_path"] = None
    
    with st.sidebar:
        st.markdown("### 📄 输入源")
        
        # Script file selection
        script_path, uploaded_script = FileManager.select_or_upload_file(
            label="脚本文件",
            file_types=[".json"],
            key="video_script_file",
            default_dir=config.get_path("outputs") / "final_script"
        )
        
        # Keyframe directory selection
        st.markdown("#### 关键帧目录")
        keyframes_base = config.get_path("outputs") / "keyframes"
        
        if keyframes_base.exists():
            keyframe_dirs = sorted([d for d in keyframes_base.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
            
            if keyframe_dirs:
                dir_options = [str(d.name) for d in keyframe_dirs]
                selected_dir = st.selectbox(
                    "选择关键帧文件夹",
                    options=dir_options,
                    index=0,
                    key="keyframe_dir_select"
                )
                keyframe_dir = keyframes_base / selected_dir
            else:
                keyframe_dir = keyframes_base
                st.warning("未找到关键帧文件夹")
        else:
            keyframe_dir = keyframes_base
            st.warning("关键帧目录不存在")
        
        st.divider()
        
        # Characters directory
        st.markdown("### 👥 人物选择")
        characters_dir = config.get_path("assets") / "characters"
        
        selected_characters = render_character_selection(characters_dir)
        
        st.markdown(f"**已选择 {len(selected_characters)} 个人物**")
        
        st.divider()
        
        # Product images upload
        st.markdown("### 📦 产品特写图片")
        st.caption("上传产品特写图片，可在各segment中选择使用")
        
        product_images = st.session_state.get("product_images", [])
        
        uploaded_products = st.file_uploader(
            "上传产品图片",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="product_uploader"
        )
        
        if uploaded_products:
            import tempfile
            product_images = []
            temp_dir = Path(tempfile.gettempdir()) / "kinyo_products"
            temp_dir.mkdir(exist_ok=True)
            
            for uploaded in uploaded_products:
                save_path = temp_dir / uploaded.name
                save_path.write_bytes(uploaded.getvalue())
                product_images.append(str(save_path))
            
            st.session_state["product_images"] = product_images
        
        if product_images:
            st.markdown(f"**已上传 {len(product_images)} 张产品图片**")
            cols = st.columns(min(4, len(product_images)))
            for i, img_path in enumerate(product_images[:4]):
                with cols[i]:
                    st.image(img_path, width=60, caption=Path(img_path).stem[:8])
        
        st.divider()
        
        # Video parameters
        st.markdown("### ⚙️ 视频参数")
        
        default_duration = st.number_input(
            "默认片段时长(秒)",
            min_value=3,
            max_value=15,
            value=config.get_default("video_duration") or 5,
            step=1
        )
        
        generate_audio = st.checkbox(
            "生成音频",
            value=True,
            help="使用AI生成音频"
        )
        
        concat_videos = st.checkbox(
            "拼接视频",
            value=True,
            help="生成后自动拼接所有片段"
        )
        
        make_compatible = st.checkbox(
            "生成兼容格式",
            value=True,
            help="重新编码为广泛兼容的格式"
        )
        
        st.divider()
        
        # Output settings
        st.markdown("### 📁 输出设置")
        
        folder_name = st.text_input(
            "输出文件夹名称",
            placeholder="留空使用时间戳",
            key="video_output_folder"
        )
        
        if not folder_name.strip():
            folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.caption(f"输出路径: `outputs/videos/{folder_name}/`")
    
    # Load script data
    script_data = None
    
    if uploaded_script:
        script_data = FileManager.load_json_file(uploaded_file=uploaded_script)
    elif script_path:
        script_data = FileManager.load_json_file(file_path=script_path)
    else:
        # Try to get from session state
        script_data = SessionStateManager.get_script_result()
    
    if not script_data:
        st.info("请先选择或生成脚本文件")
        return
    
    # Parse segments
    script = script_data.get("script", script_data)
    if isinstance(script, str):
        try:
            script = json.loads(script)
        except:
            script = {}
    
    segments = script.get("segments", [])
    
    if not segments:
        st.error("脚本中没有找到 segments")
        return
    
    # Build character map
    character_map = {c["id"]: c for c in selected_characters}
    
    # Get product images from session state
    product_images = st.session_state.get("product_images", [])
    
    # Main area: Segment configuration
    st.markdown("## 🎬 Segment 配置")
    st.markdown(f"共 {len(segments)} 个片段")
    
    # Segment configuration (includes duration for each segment)
    assignments = render_segment_config(segments, selected_characters, keyframe_dir, product_images, default_duration)
    
    st.markdown("---")
    
    # Prompt section
    st.markdown("## 📝 提示词编辑")
    
    # Initialize prompts if not already done
    if len(st.session_state["video_prompts"]) != len(segments):
        st.session_state["video_prompts"] = []
        for idx, (seg, assign) in enumerate(zip(segments, assignments)):
            char_infos = [character_map[cid] for cid in assign["character_ids"] if cid in character_map]
            initial_prompt = build_initial_prompt(seg, char_infos)
            st.session_state["video_prompts"].append(initial_prompt)
    
    # Render prompt editors
    prompts = render_prompt_editors(segments, assignments, selected_characters, character_map)
    
    # Update session state
    st.session_state["video_prompts"] = prompts
    
    # Optimize buttons
    st.markdown("### 🔄 提示词优化")
    st.caption(f"优化模型: **gpt-5.4** (KToken)")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🤖 AI优化所有提示词", type="secondary", use_container_width=True):
            with st.spinner("正在优化提示词..."):
                optimized_prompts = []
                original_prompts = []
                progress_bar = st.progress(0)
                
                for idx, (seg, assign, prompt) in enumerate(zip(segments, assignments, prompts)):
                    progress_bar.progress(int((idx + 1) / len(segments) * 100))
                    
                    char_infos = [character_map[cid] for cid in assign["character_ids"] if cid in character_map]
                    product_name = Path(assign["product_image"]).stem if assign.get("product_image") else None
                    
                    # Build image index map
                    has_product = assign.get("product_image") is not None
                    image_index_map = build_image_index_map(
                        has_keyframe=True,
                        has_product=has_product,
                        character_infos=char_infos
                    )
                    
                    original_prompts.append(prompt)
                    optimized = optimize_prompt_with_gpt(
                        segment=seg,
                        character_infos=char_infos,
                        initial_prompt=prompt,
                        duration=assign["duration"],
                        product_image_name=product_name,
                        image_index_map=image_index_map
                    )
                    optimized_prompts.append(optimized)
                
                st.session_state["video_prompts"] = optimized_prompts
                st.session_state["original_prompts"] = original_prompts
                st.session_state["prompts_optimized"] = True
                st.success("✓ 提示词优化完成")
                st.rerun()
    
    with col2:
        if st.button("🔄 重置提示词", use_container_width=True):
            st.session_state["video_prompts"] = []
            st.session_state["original_prompts"] = []
            st.session_state["prompts_optimized"] = False
            st.rerun()
    
    # Generate video section
    st.markdown("---")
    st.markdown("## 🎬 生成视频")
    
    # Generation mode selection
    st.markdown("### 选择生成模式")
    
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        if st.button("📦 批量生成", type="primary" if st.session_state["generation_mode"] == "batch" else "secondary", use_container_width=True):
            st.session_state["generation_mode"] = "batch"
            st.rerun()
    
    with col_mode2:
        if st.button("🔄 逐个生成", type="primary" if st.session_state["generation_mode"] == "step" else "secondary", use_container_width=True):
            st.session_state["generation_mode"] = "step"
            st.session_state["current_segment_idx"] = 0
            st.session_state["generated_results"] = []
            st.session_state["last_frame_path"] = None
            st.rerun()
    
    st.caption(f"当前模式: **{'批量生成' if st.session_state['generation_mode'] == 'batch' else '逐个生成'}**")
    
    # Reset button for step mode
    if st.session_state["generation_mode"] == "step" and st.session_state["generated_results"]:
        if st.button("🔄 重置逐个生成进度", use_container_width=True):
            st.session_state["current_segment_idx"] = 0
            st.session_state["generated_results"] = []
            st.session_state["last_frame_path"] = None
            st.rerun()
    
    # Validate configuration
    missing_keyframes = []
    for idx, assign in enumerate(assignments):
        if not assign.get("keyframe_path"):
            missing_keyframes.append(f"S{idx + 1:02d}")
    
    if missing_keyframes:
        st.warning(f"缺少关键帧: {', '.join(missing_keyframes)}")
    
    # Check API keys
    ark_api_key = config.get_api_key("ark") or os.getenv("ARK_API_KEY") or os.getenv("SEEDANCE_API_KEY")
    
    if not ark_api_key:
        st.error("请先在设置页面配置 ARK_API_KEY")
    
    # ==================== BATCH MODE ====================
    if st.session_state["generation_mode"] == "batch":
        generate_button = st.button("🎬 开始批量生成", type="primary", use_container_width=True, disabled=not ark_api_key or bool(missing_keyframes))
        
        if generate_button:
            output_dir = config.get_path("outputs") / "videos" / folder_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build segment configs
            segment_configs = []
            
            for idx, (seg, assign, prompt) in enumerate(zip(segments, assignments, prompts)):
                # Get character image paths
                char_paths = []
                for cid in assign["character_ids"]:
                    if cid in character_map:
                        char_info = character_map[cid]
                        # Use selected images
                        for img_type in char_info.get("selected_images", ["front_full"]):
                            if img_type in char_info.get("image_paths", {}):
                                char_paths.append(Path(char_info["image_paths"][img_type]))
                
                # Get product image path
                product_path = None
                if assign.get("product_image"):
                    product_path = Path(assign["product_image"])
                
                segment_configs.append(SegmentConfig(
                    segment_idx=idx,
                    stage=seg.get("stage", f"Segment {idx + 1}"),
                    time=seg.get("time", ""),
                    keyframe_path=assign["keyframe_path"],
                    character_paths=char_paths,
                    prompt=prompt,
                    duration=assign["duration"],
                    product_image_path=product_path
                ))
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            logs = []
            
            def progress_callback(percent, message):
                progress_bar.progress(percent)
                status_text.text(message)
                logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
            
            # Generate all segments
            try:
                result = generate_all_segments(
                    segments_config=segment_configs,
                    output_dir=output_dir,
                    api_key=ark_api_key,
                    generate_audio=generate_audio,
                    progress_callback=progress_callback
                )
                
                if result["success"]:
                    # Save prompts
                    prompts_path = output_dir / "prompts.json"
                    prompts_data = {
                        "segments": [
                            {
                                "segment_idx": idx,
                                "stage": seg.get("stage", ""),
                                "prompt": prompt,
                                "characters": assign["character_ids"]
                            }
                            for idx, (seg, assign, prompt) in enumerate(zip(segments, assignments, prompts))
                        ],
                        "optimized": st.session_state.get("prompts_optimized", False)
                    }
                    prompts_path.write_text(json.dumps(prompts_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    
                    # Concatenate videos if requested
                    if concat_videos:
                        progress_callback(95, "正在拼接视频...")
                        
                        video_paths = [
                            Path(r["video_path"])
                            for r in result["results"]
                            if Path(r["video_path"]).exists()
                        ]
                        
                        if video_paths:
                            final_path = output_dir / "final_video.mp4"
                            concatenate_videos_ffmpeg(video_paths, final_path)
                            
                            if make_compatible:
                                compatible_path = output_dir / "final_video_compatible.mp4"
                                make_compatible_video(final_path, compatible_path)
                    
                    progress_callback(100, "完成！")
                    
                    st.success(f"✓ 生成完成！共 {len(result['results'])} 个片段")
                    
                    # Save result to session state
                    st.session_state["video_result"] = result
                    st.session_state["video_output_dir"] = str(output_dir)
                    
                else:
                    st.error(f"生成失败: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                st.error(f"生成出错: {str(e)}")
    
    # ==================== STEP MODE ====================
    else:
        output_dir = config.get_path("outputs") / "videos" / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        current_idx = st.session_state["current_segment_idx"]
        generated_results = st.session_state["generated_results"]
        
        # Check if all segments are done
        if current_idx >= len(segments):
            st.success("🎉 所有片段已生成完成！")
            
            # Show all generated videos
            st.markdown("### 📺 已生成的片段")
            for r in generated_results:
                video_path = Path(r["video_path"])
                if video_path.exists():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.video(str(video_path))
                    with col2:
                        st.caption(f"**{r['stage']}**")
            
            # Concatenate option
            if concat_videos and len(generated_results) > 1:
                if st.button("🔗 拼接所有片段", type="primary", use_container_width=True):
                    with st.spinner("正在拼接视频..."):
                        video_paths = [Path(r["video_path"]) for r in generated_results if Path(r["video_path"]).exists()]
                        
                        if video_paths:
                            final_path = output_dir / "final_video.mp4"
                            concatenate_videos_ffmpeg(video_paths, final_path)
                            
                            if make_compatible:
                                compatible_path = output_dir / "final_video_compatible.mp4"
                                make_compatible_video(final_path, compatible_path)
                            
                            st.success("✓ 拼接完成！")
                            st.session_state["video_output_dir"] = str(output_dir)
                            st.rerun()
        
        else:
            # Show current segment info
            seg = segments[current_idx]
            assign = assignments[current_idx]
            prompt = prompts[current_idx]
            duration = assign["duration"]
            
            st.markdown(f"### 当前片段: {seg.get('stage', f'Segment {current_idx + 1}')} ({seg.get('time', '')})")
            
            # Display segment details
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**进度**: {current_idx + 1} / {len(segments)}")
                st.markdown(f"**时长**: {duration} 秒")
                st.markdown(f"**人物**: {', '.join(assign['character_ids']) if assign['character_ids'] else '无'}")
                
                st.markdown("**提示词预览**:")
                st.text(prompt[:300] + "..." if len(prompt) > 300 else prompt)
            
            with col2:
                if assign.get("keyframe_path"):
                    st.image(str(assign["keyframe_path"]), caption="关键帧", use_container_width=True)
                
                # Show previous result if exists
                if generated_results:
                    st.caption(f"✓ 已完成 {len(generated_results)} 个片段")
            
            # Generate button for current segment
            generate_single = st.button(f"🎬 生成片段 {current_idx + 1}", type="primary", use_container_width=True, disabled=not ark_api_key or not assign.get("keyframe_path"))
            
            if generate_single:
                # Get character image paths
                char_paths = []
                for cid in assign["character_ids"]:
                    if cid in character_map:
                        char_info = character_map[cid]
                        # Use selected images
                        for img_type in char_info.get("selected_images", ["front_full"]):
                            if img_type in char_info.get("image_paths", {}):
                                char_paths.append(Path(char_info["image_paths"][img_type]))
                
                # Get product image path
                product_path = None
                if assign.get("product_image"):
                    product_path = Path(assign["product_image"])
                
                # Build segment config
                segment_config = SegmentConfig(
                    segment_idx=current_idx,
                    stage=seg.get("stage", f"Segment {current_idx + 1}"),
                    time=seg.get("time", ""),
                    keyframe_path=assign["keyframe_path"],
                    character_paths=char_paths,
                    prompt=prompt,
                    duration=duration,
                    product_image_path=product_path
                )
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(percent, message):
                    progress_bar.progress(percent)
                    status_text.text(message)
                
                try:
                    # Generate single segment
                    from video_agent.agent.video_segment_generator import generate_segment_video, download_file
                    
                    progress_callback(10, "正在生成视频...")
                    
                    video_url = generate_segment_video(
                        keyframe_path=segment_config.keyframe_path,
                        character_paths=segment_config.character_paths,
                        prompt=segment_config.prompt,
                        duration=segment_config.duration,
                        api_key=ark_api_key,
                        product_image_path=segment_config.product_image_path,
                        generate_audio=generate_audio
                    )
                    
                    progress_callback(60, "正在下载视频...")
                    
                    # Download video
                    video_path = output_dir / f"S{current_idx + 1:02d}.mp4"
                    download_file(video_url, video_path)
                    
                    progress_callback(100, "完成！")
                    
                    # Save result
                    result_item = {
                        "segment_idx": current_idx,
                        "stage": segment_config.stage,
                        "video_path": str(video_path),
                        "success": True
                    }
                    
                    generated_results.append(result_item)
                    st.session_state["generated_results"] = generated_results
                    st.session_state["current_segment_idx"] = current_idx + 1
                    
                    st.success(f"✓ 片段 {current_idx + 1} 生成完成！")
                    
                    # Show generated video
                    st.video(str(video_path))
                    
                    # Auto continue button
                    if current_idx + 1 < len(segments):
                        if st.button("➡️ 继续下一个片段", type="primary", use_container_width=True):
                            st.rerun()
                    else:
                        st.balloons()
                        if st.button("🎉 查看最终结果", type="primary", use_container_width=True):
                            st.rerun()
                
                except Exception as e:
                    st.error(f"生成失败: {str(e)}")
                    st.stop()
    
    # ==================== DISPLAY RESULTS ====================
    video_result = st.session_state.get("video_result")
    output_dir_result = st.session_state.get("video_output_dir")
    generated_results = st.session_state.get("generated_results", [])
    
    # For batch mode
    if video_result and output_dir_result:
        output_path = Path(output_dir_result)
        
        st.markdown("---")
        st.markdown("## 📺 生成结果")
        
        # Display final video
        final_video = output_path / "final_video.mp4"
        compatible_video = output_path / "final_video_compatible.mp4"
        
        video_to_show = compatible_video if compatible_video.exists() else final_video
        
        if video_to_show.exists():
            st.video(str(video_to_show))
            
            # Download button
            with open(video_to_show, 'rb') as f:
                video_bytes = f.read()
            
            st.download_button(
                label="📥 下载最终视频",
                data=video_bytes,
                file_name=video_to_show.name,
                mime="video/mp4",
                use_container_width=True
            )
        
        # Display individual clips
        clips = sorted(output_path.glob("S*.mp4"))
        
        if clips:
            with st.expander(f"🎞️ 查看所有片段 ({len(clips)} 个)", expanded=False):
                cols = st.columns(min(3, len(clips)))
                
                for idx, clip in enumerate(clips):
                    with cols[idx % 3]:
                        st.video(str(clip))
                        st.caption(clip.name)
    
    # For step mode (when all segments are done)
    elif st.session_state.get("generation_mode") == "step" and generated_results:
        output_dir_step = config.get_path("outputs") / "videos" / folder_name
        
        final_video = output_dir_step / "final_video.mp4"
        compatible_video = output_dir_step / "final_video_compatible.mp4"
        
        video_to_show = compatible_video if compatible_video.exists() else final_video
        
        if video_to_show.exists():
            st.markdown("---")
            st.markdown("## 📺 最终视频")
            st.video(str(video_to_show))
            
            with open(video_to_show, 'rb') as f:
                video_bytes = f.read()
            
            st.download_button(
                label="📥 下载最终视频",
                data=video_bytes,
                file_name=video_to_show.name,
                mime="video/mp4",
                use_container_width=True
            )


if __name__ == "__main__":
    main()

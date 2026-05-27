"""
Product Keyframe Generation Page
Generate product-focused keyframes from script JSON
"""

import sys
import os
from pathlib import Path
import base64
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import streamlit as st
from PIL import Image

from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase
from streamlit_app.components.file_manager import FileManager
from openai import OpenAI


DEFAULT_KEYFRAME_PROMPT = """
Create a professional product photography keyframe.

CRITICAL REQUIREMENTS:
- NO HUMANS, NO FACES, NO PEOPLE, NO HANDS in the image
- PRODUCT IS THE HERO: The product must be the main focus of the image
- PRODUCT LOGO MUST BE VISIBLE: Keep the product's logo/brand mark clearly visible and readable
- Show the product COMPLETELY: Display the full product with all its details, logos, and branding intact
- Do NOT hide, blur, or obscure any logos or product branding

{image_composition_info}

PHYSICAL REALISM & COMMON SENSE:
- Respect laws of physics: gravity, lighting, reflections, shadows must be realistic
- Product must rest naturally on surfaces - no floating or impossible positions
- Shadows must be consistent with light source direction
- Reflections on product surface must match the environment logically
- Cable connections (if any) must follow natural paths - no impossible knots or floating wires
- TV screen content should be appropriate and clearly visible from the viewing angle
- Scale and proportion must be realistic - product size relative to furniture/environment
- Lighting must have a logical source - window, ceiling light, or lamp
- No impossible geometries or Escher-like impossible spaces
- Materials should behave realistically - matte surfaces don't reflect, glossy surfaces do

Scene Setup:
- Place the product in a modern, clean Chinese living room environment
{environment_context}
- TV screen visible in background (displaying appropriate interface)
- Warm commercial lighting, professional product photography style
- Sharp focus on product, clean composition
- Furniture and props should be arranged in a natural, believable way

Product Focus:
- {product_focus}
- Highlight key selling points: {selling_points}
- Show practical usage scenario if applicable
- Product logo and branding should be prominently displayed
- Product should be positioned in a way that makes sense for its use

Technical Style:
- Vertical format 9:16 for short video
- Photorealistic, commercial quality
- Clean, professional, no clutter
- No text overlay that could obscure the product

Ignore any human/person references in the script - only show product and environment.
Make sure the product's original branding and logos remain visible and authentic.
Every element in the scene should look physically possible and naturally placed.
"""

DEFAULT_ENVIRONMENT_PROMPT = """
ENVIRONMENT REFERENCE INSTRUCTIONS:
The RIGHT side of the input image shows the EXACT environment/background to use.

STRICT ADHERENCE TO REFERENCE:
- Use the environment EXACTLY as shown in the reference image
- DO NOT add filters, special effects, or artistic enhancements
- DO NOT change the lighting style, color grading, or atmosphere
- DO NOT add dramatic shadows, lens flares, or cinematic effects
- Keep the SAME room layout, furniture positions, and props
- Maintain the ORIGINAL lighting direction and intensity
- Preserve the ORIGINAL color temperature (warm/cool/neutral as in reference)
- Copy the environment textures, materials, and details accurately

WHAT TO AVOID:
- No added "cinematic" or "commercial" lighting enhancements
- No changed wall colors, furniture styles, or room layout
- No extra decorative elements not present in the reference
- No stylized rendering - keep it photorealistic and natural
- No HDR-like effects or oversaturation

The goal is to place the product into the EXACT same environment, not to create a stylized version of it.
"""

IMAGE_COMPOSITION_WITH_ENV = """
IMAGE COMPOSITION INSTRUCTION:
The input image is a HORIZONTAL COMBINATION of TWO IMAGES:
- LEFT SIDE: Product image (the main product you need to showcase)
- RIGHT SIDE: Environment reference image (the EXACT scene/background to use)

These two parts are separated by a VERTICAL WHITE BAND.

Your task:
1. Identify the product from the LEFT side - this is the product to showcase
2. The RIGHT side shows the EXACT environment - use it as-is, without modifications
3. Generate a NEW image that:
   - Shows the SAME PRODUCT (from left side) as the main focus
   - Uses the EXACT SAME ENVIRONMENT (from right side) - no effects, no enhancements
   - Places the product naturally within this unchanged environment
   - Matches the original lighting, colors, and atmosphere perfectly
   - Creates a clean, natural product photograph without added effects

CRITICAL: Do NOT enhance or stylize the environment. Use it exactly as shown.
"""

IMAGE_COMPOSITION_NO_ENV = """
IMAGE COMPOSITION INSTRUCTION:
The input image shows the PRODUCT you need to showcase.
Generate a professional product photography that integrates this product into a scene.
"""


def concatenate_product_environment(
    product_path: Path,
    environment_path: Optional[Path],
    output_path: Path,
    white_band_width: int = 50
) -> Path:
    """
    Concatenate product image and environment image horizontally.
    Product on LEFT, Environment on RIGHT, separated by white band.
    
    Args:
        product_path: Path to product image
        environment_path: Path to environment image (optional)
        output_path: Path to save concatenated image
        white_band_width: Width of white separator band
    
    Returns:
        Path to concatenated image
    """
    product_img = Image.open(product_path).convert("RGB")
    
    if environment_path and environment_path.exists():
        env_img = Image.open(environment_path).convert("RGB")
        
        target_height = max(product_img.height, env_img.height)
        
        product_img = product_img.resize(
            (int(product_img.width * target_height / product_img.height), target_height),
            Image.Resampling.LANCZOS
        )
        env_img = env_img.resize(
            (int(env_img.width * target_height / env_img.height), target_height),
            Image.Resampling.LANCZOS
        )
        
        total_width = product_img.width + white_band_width + env_img.width
        
        combined = Image.new("RGB", (total_width, target_height), (255, 255, 255))
        
        combined.paste(product_img, (0, 0))
        
        combined.paste(env_img, (product_img.width + white_band_width, 0))
    else:
        combined = product_img
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(output_path, "PNG")
    
    return output_path


def get_image_files(directory: Path) -> List[Path]:
    """Get all image files from a directory"""
    if not directory.exists():
        return []
    
    images = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        images.extend(sorted(directory.glob(ext)))
    
    return images


def get_product_files(config: ConfigManager) -> List[Path]:
    """Get all product images from assets/products and its subdirectories"""
    products_dir = config.get_path("assets") / "products"
    if not products_dir.exists():
        products_dir.mkdir(parents=True, exist_ok=True)
        return []
    
    images = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        images.extend(sorted(products_dir.rglob(ext)))
    
    return images


def generate_single_keyframe(
    product_path: Path,
    prompt: str,
    output_path: Path,
    api_key: str,
    base_url: str = "https://ai.ktokenhub.app",
    image_model: str = "gpt-image-2",
    size: str = "1024x1792",
    quality: str = "auto",
    environment_path: Optional[Path] = None,
    debug_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate a single keyframe using images.edit() API.
    If environment image is provided, concatenate product and environment first.
    
    Args:
        product_path: Path to product image
        prompt: Generation prompt
        output_path: Path to save output
        api_key: API key
        base_url: API base URL
        image_model: Image model name
        size: Output size
        quality: Output quality
        environment_path: Optional path to environment reference image
        debug_dir: Directory to save concatenated input images for debugging
    
    Returns:
        Result dictionary with success status and paths
    """
    
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    
    try:
        input_image_path = product_path
        
        if environment_path and environment_path.exists():
            if debug_dir:
                concat_output = debug_dir / f"{output_path.stem}_input_concat.png"
            else:
                concat_output = output_path.parent / "debug" / f"{output_path.stem}_input_concat.png"
            
            input_image_path = concatenate_product_environment(
                product_path=product_path,
                environment_path=environment_path,
                output_path=concat_output,
                white_band_width=50
            )
        
        with open(input_image_path, 'rb') as img_file:
            response = client.images.edit(
                model=image_model,
                image=img_file,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
        
        image_b64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_b64)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return {
            "success": True,
            "image_path": str(output_path),
            "product_used": str(product_path),
            "environment_used": str(environment_path) if environment_path else None,
            "concatenated_input": str(input_image_path) if environment_path else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "product_used": str(product_path),
            "environment_used": str(environment_path) if environment_path else None
        }


def parse_script_segments(script_data: Dict) -> List[Dict]:
    """Parse script data to extract segments with key info"""
    script = script_data.get("script", script_data)
    planning = script_data.get("planning", {})
    
    segments = script.get("segments", [])
    parsed = []
    
    for seg in segments:
        parsed.append({
            "stage": seg.get("stage", "Unknown"),
            "time": seg.get("time", ""),
            "purpose": seg.get("purpose", ""),
            "visual": seg.get("visual", ""),
            "voiceover": seg.get("voiceover", ""),
            "selling_points": planning.get("core_selling_point", ""),
            "target_user": planning.get("target_user", "")
        })
    
    return parsed


def render_keyframe_table(
    segments: List[Dict],
    product_files: List[Path],
    session_key: str,
    uploaded_products: List[Path]
) -> List[Dict]:
    """Render keyframe configuration table"""
    
    all_products = product_files + uploaded_products
    product_options = ["不选择"] + [str(p.name) for p in all_products]
    product_path_map = {p.name: p for p in all_products}
    
    keyframe_configs = []
    keyframe_idx = 0
    
    for seg_idx, seg in enumerate(segments):
        stage = seg.get("stage", "Unknown")
        
        st.markdown(f"### 📍 {stage} ({seg.get('time', '')})")
        st.caption(f"目的: {seg.get('purpose', '')}")
        
        if seg.get("visual"):
            with st.expander("查看脚本详情", expanded=False):
                st.write(f"**画面**: {seg.get('visual', '')}")
                st.write(f"**口播**: {seg.get('voiceover', '')}")
        
        num_keyframes = st.number_input(
            "关键帧数量",
            min_value=0,
            max_value=5,
            value=1,
            key=f"{session_key}_num_{seg_idx}",
            help=f"该段落生成几张关键帧"
        )
        
        for kf_in_seg in range(num_keyframes):
            keyframe_idx += 1
            shot_id = f"S{keyframe_idx:02d}"
            
            st.markdown(f"**关键帧 {shot_id}**")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                selected_product = st.selectbox(
                    "产品图片",
                    options=product_options,
                    key=f"{session_key}_product_{seg_idx}_{kf_in_seg}",
                    label_visibility="collapsed"
                )
            
            with col2:
                custom_prompt_addon = st.text_input(
                    "补充描述（可选）",
                    placeholder="如: 特写产品接口、展示电视界面等",
                    key=f"{session_key}_addon_{seg_idx}_{kf_in_seg}",
                    label_visibility="collapsed"
                )
            
            with col3:
                preview = st.checkbox("预览", key=f"{session_key}_preview_{seg_idx}_{kf_in_seg}")
            
            if selected_product != "不选择":
                product_path = product_path_map.get(selected_product)
                
                if preview and product_path:
                    st.image(str(product_path), width=150)
                
                keyframe_configs.append({
                    "shot_id": shot_id,
                    "stage": stage,
                    "segment_idx": seg_idx,
                    "product_path": product_path,
                    "product_name": selected_product,
                    "custom_addon": custom_prompt_addon,
                    "segment_info": seg
                })
        
        st.divider()
    
    return keyframe_configs


def main():
    st.set_page_config(
        page_title="产品关键帧生成 - KINYO AI",
        page_icon="🖼️",
        layout="wide"
    )
    
    SessionStateManager.init_session_state()
    config = ConfigManager()
    
    st.title("🖼️ 产品关键帧生成")
    st.markdown("生成专注于产品展示的关键帧，**不会出现任何人像**")
    
    project_root = Path(__file__).resolve().parents[2]
    
    with st.sidebar:
        st.markdown("### 📄 脚本来源")
        
        script_path, uploaded_file = FileManager.select_or_upload_file(
            label="脚本文件",
            file_types=[".json"],
            key="keyframe_script_file",
            default_dir=config.get_path("outputs") / "final_script"
        )
        
        st.divider()
        
        st.markdown("### 📦 产品图片")
        
        product_files = get_product_files(config)
        
        st.markdown(f"**已有产品图**: {len(product_files)} 张")
        
        if product_files:
            with st.expander("预览产品图", expanded=False):
                cols = st.columns(min(4, len(product_files)))
                for idx, prod_path in enumerate(product_files[:8]):
                    with cols[idx % 4]:
                        st.image(str(prod_path), caption=prod_path.name[:15], use_container_width=True)
        
        uploaded_files = st.file_uploader(
            "上传新产品图",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="upload_products"
        )
        
        uploaded_product_paths = []
        if uploaded_files:
            temp_dir = config.get_path("assets") / "products" / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            for uf in uploaded_files:
                temp_path = temp_dir / uf.name
                temp_path.write_bytes(uf.getvalue())
                uploaded_product_paths.append(temp_path)
            
            st.success(f"已上传 {len(uploaded_files)} 张图片")
        
        st.divider()
        
        st.markdown("### 🏠 环境图片（可选）")
        st.caption("上传环境参照图以保持关键帧场景一致")
        
        environment_files = st.file_uploader(
            "上传环境参考图",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="upload_environments"
        )
        
        environment_paths = []
        if environment_files:
            env_dir = config.get_path("assets") / "environments" / "temp"
            env_dir.mkdir(parents=True, exist_ok=True)
            
            for ef in environment_files:
                env_path = env_dir / ef.name
                env_path.write_bytes(ef.getvalue())
                environment_paths.append(env_path)
            
            st.success(f"已上传 {len(environment_files)} 张环境图")
            
            with st.expander("预览环境图", expanded=False):
                cols = st.columns(min(4, len(environment_paths)))
                for idx, env_path in enumerate(environment_paths):
                    with cols[idx % 4]:
                        st.image(str(env_path), caption=env_path.name[:15], use_container_width=True)
        
        st.divider()
        
        st.markdown("### ⚙️ 生成设置")
        
        image_model = st.text_input(
            "图片模型",
            value=config.get_model("image_generation") or "gpt-image-2"
        )
        
        size = st.selectbox(
            "图片尺寸",
            options=["1024x1792", "1024x1024", "1792x1024", "auto"],
            index=0,
            help="推荐使用1024x1792 (9:16竖屏)"
        )
        
        quality = st.selectbox(
            "图片质量",
            options=["auto", "low", "medium", "high"],
            index=0
        )
        
        st.divider()
        
        st.markdown("### 💡 提示")
        st.info("""
        - 生成的关键帧**不会包含任何人像**
        - **产品logo会完整展示**，不会被隐藏或模糊
        - 专注于产品展示，产品是画面的主角
        - 可为每个segment设置多张关键帧
        - 可选：上传环境图来保持关键帧场景一致
        """)
    
    script_data = None
    
    if uploaded_file:
        script_data = FileManager.load_json_file(uploaded_file=uploaded_file)
    elif script_path:
        script_data = FileManager.load_json_file(file_path=script_path)
    else:
        script_data = SessionStateManager.get_script_result()
    
    if not script_data:
        st.warning("请先选择或生成脚本文件")
        return
    
    segments = parse_script_segments(script_data)
    
    if not segments:
        st.error("脚本中没有找到segments")
        return
    
    st.markdown("## 🎬 关键帧配置")
    st.markdown("为每个脚本段落设置关键帧数量和产品图片")
    
    all_products = product_files + uploaded_product_paths
    
    keyframe_configs = render_keyframe_table(
        segments=segments,
        product_files=product_files,
        session_key="kf_config",
        uploaded_products=uploaded_product_paths
    )
    
    st.markdown("---")
    
    total_keyframes = len(keyframe_configs)
    
    if total_keyframes == 0:
        st.warning("请至少为一张关键帧选择产品图片")
        return
    
    st.markdown(f"**共配置 {total_keyframes} 张关键帧**")
    
    st.markdown("### 📁 输出设置")
    
    col_name1, col_name2 = st.columns([3, 1])
    
    with col_name1:
        folder_name = st.text_input(
            "输出文件夹名称",
            placeholder="留空则使用时间戳命名",
            help="自定义输出文件夹名称"
        )
    
    with col_name2:
        st.markdown("&nbsp;")
        if st.button("使用时间戳", use_container_width=True):
            folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    
    if not folder_name.strip():
        folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    st.caption(f"输出路径: `outputs/keyframes/{folder_name}/`")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        generate_all = st.button("🚀 批量生成全部", type="primary", use_container_width=True)
    
    with col2:
        generate_selected = st.button("批量生成选中", use_container_width=True)
    
    if generate_all and keyframe_configs:
        api_key = config.get_api_key("k_token") or os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            st.error("请先在设置页面配置 API Key")
            return
        
        output_dir = config.get_path("outputs") / "keyframes" / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        environment_context = ""
        image_composition_info = ""
        
        if environment_paths:
            environment_context = DEFAULT_ENVIRONMENT_PROMPT.strip()
            image_composition_info = IMAGE_COMPOSITION_WITH_ENV.strip()
            st.info(f"🏠 已启用环境参照，产品图与环境图将拼接后输入AI")
        else:
            image_composition_info = IMAGE_COMPOSITION_NO_ENV.strip()
        
        for idx, kf_config in enumerate(keyframe_configs):
            shot_id = kf_config["shot_id"]
            product_path = kf_config["product_path"]
            segment_info = kf_config["segment_info"]
            custom_addon = kf_config.get("custom_addon", "")
            
            progress_bar.progress(int((idx + 1) / total_keyframes * 100))
            status_text.text(f"正在生成 {shot_id} ({idx + 1}/{total_keyframes})...")
            
            selling_points = segment_info.get("selling_points", "")
            product_focus = segment_info.get("visual", "")
            
            if custom_addon:
                product_focus = f"{product_focus}\n{custom_addon}"
            
            prompt = DEFAULT_KEYFRAME_PROMPT.format(
                product_focus=product_focus,
                selling_points=selling_points,
                environment_context=environment_context,
                image_composition_info=image_composition_info
            )
            
            output_path = output_dir / f"{shot_id}.png"
            
            env_path = environment_paths[0] if environment_paths else None
            
            result = generate_single_keyframe(
                product_path=product_path,
                prompt=prompt,
                output_path=output_path,
                api_key=api_key,
                base_url=os.getenv("K_TOKEN_BASE_URL", "https://ai.ktokenhub.app"),
                image_model=image_model,
                size=size if size != "auto" else "1024x1792",
                quality=quality,
                environment_path=env_path,
                debug_dir=debug_dir
            )
            
            result["shot_id"] = shot_id
            result["stage"] = kf_config["stage"]
            results.append(result)
            
            if result["success"]:
                st.success(f"✓ {shot_id} 生成成功")
            else:
                st.error(f"✗ {shot_id} 生成失败: {result.get('error', '')}")
            
            time.sleep(0.5)
        
        progress_bar.progress(100)
        status_text.text("完成！")
        
        st.session_state["keyframe_results"] = results
        st.session_state["keyframe_output_dir"] = str(output_dir)
    
    results = st.session_state.get("keyframe_results", [])
    output_dir = st.session_state.get("keyframe_output_dir")
    
    if results and output_dir:
        st.markdown("---")
        st.markdown("## 🖼️ 生成的关键帧")
        
        output_path = Path(output_dir)
        
        successful = [r for r in results if r.get("success")]
        
        if successful:
            cols = st.columns(min(4, len(successful)))
            
            for idx, result in enumerate(successful):
                shot_id = result["shot_id"]
                img_path = output_path / f"{shot_id}.png"
                
                if img_path.exists():
                    with cols[idx % 4]:
                        st.image(str(img_path), caption=f"{shot_id} - {result['stage']}", use_container_width=True)
            
            st.markdown("### 📥 导出")
            
            if st.button("打包下载全部关键帧"):
                import zipfile
                import io
                
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for result in successful:
                        shot_id = result["shot_id"]
                        img_path = output_path / f"{shot_id}.png"
                        if img_path.exists():
                            zf.write(img_path, f"{shot_id}.png")
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="📥 下载 ZIP",
                    data=zip_buffer,
                    file_name="product_keyframes.zip",
                    mime="application/zip"
                )
            
            st.markdown("### ➡️ 下一步")
            
            if st.button("发送到视频生成", type="primary"):
                SessionStateManager.set("keyframe_output_dir", output_dir)
                st.switch_page("pages/5_🎬_视频生成.py")


if __name__ == "__main__":
    main()

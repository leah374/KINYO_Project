"""
Video Segment Generator
Generate video segments using Seedance API with character and last frame support
"""

import base64
import json
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from openai import OpenAI


DEFAULT_SEEDANCE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_SEEDANCE_MODEL = "doubao-seedance-2-0-260128"

K_TOKEN_API_KEY = os.getenv("K_TOKEN_API_KEY") or os.getenv("OPENAI_API_KEY")
K_TOKEN_BASE_URL = os.getenv("K_TOKEN_BASE_URL", "https://ai.ktokenhub.app/v1")
GENERATION_MODEL = os.getenv("SCRIPT_MODEL", "gpt-5.4")


@dataclass
class SegmentConfig:
    """Configuration for a single video segment"""
    segment_idx: int
    stage: str
    time: str
    keyframe_path: Path
    character_paths: List[Path]
    prompt: str
    duration: int
    product_image_path: Optional[Path] = None


def load_characters(characters_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all character information from assets/characters/
    
    Returns:
        List of character dictionaries with description and paths
    """
    characters = []
    
    if not characters_dir.exists():
        return characters
    
    for char_dir in sorted(characters_dir.iterdir()):
        if not char_dir.is_dir():
            continue
        
        desc_file = char_dir / f"{char_dir.name}_desc.json"
        if not desc_file.exists():
            # Try to find any _desc.json file
            desc_files = list(char_dir.glob("*_desc.json"))
            if desc_files:
                desc_file = desc_files[0]
            else:
                continue
        
        try:
            desc = json.loads(desc_file.read_text(encoding="utf-8"))
            desc["path"] = str(char_dir)
            
            # Add full image paths
            images = desc.get("images", {})
            desc["image_paths"] = {}
            for view, filename in images.items():
                img_path = char_dir / filename
                if img_path.exists():
                    desc["image_paths"][view] = str(img_path)
            
            characters.append(desc)
        except Exception as e:
            print(f"Warning: Failed to load character {char_dir.name}: {e}")
    
    return characters


def image_to_base64(image_path: Path) -> str:
    """
    Convert local image to base64 data URL
    
    Args:
        image_path: Path to image file
    
    Returns:
        Base64 data URL string
    """
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def download_file(url: str, output_path: Path, timeout: int = 300) -> Path:
    """
    Download file from URL to local path
    
    Args:
        url: File URL
        output_path: Local path to save file
        timeout: Download timeout in seconds
    
    Returns:
        Path to downloaded file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    
    output_path.write_bytes(response.content)
    return output_path


def build_image_index_map(
    has_keyframe: bool = True,
    has_product: bool = False,
    character_infos: List[Dict[str, Any]] = None
) -> Dict[str, int]:
    """
    Build mapping of image types to their index numbers
    
    According to Seedance API, images are passed in order:
    1. Keyframe (always first if exists)
    2. Product image (second if exists)
    3. Character images (remaining)
    
    Args:
        has_keyframe: Whether keyframe exists
        has_product: Whether product image exists
        character_infos: List of character info dictionaries
    
    Returns:
        Dictionary mapping image identifiers to their 1-based index
    """
    index_map = {}
    current_idx = 1
    
    if has_keyframe:
        index_map["keyframe"] = current_idx
        current_idx += 1
    
    if has_product:
        index_map["product"] = current_idx
        current_idx += 1
    
    if character_infos:
        for char in character_infos:
            char_id = char.get("id", "")
            selected_images = char.get("selected_images", ["front_full"])
            for img_type in selected_images:
                key = f"{char_id}_{img_type}"
                index_map[key] = current_idx
                current_idx += 1
    
    return index_map


def build_initial_prompt(
    segment: Dict[str, Any],
    character_infos: List[Dict[str, Any]],
    product_name: str = "K7家庭K歌主机",
    image_index_map: Dict[str, int] = None
) -> str:
    """
    Build initial prompt for a segment
    
    Args:
        segment: Script segment data
        character_infos: List of character information dictionaries
        product_name: Product name for the prompt
        image_index_map: Mapping of image identifiers to index numbers
    
    Returns:
        Initial prompt string
    """
    stage = segment.get("stage", "")
    visual = segment.get("visual", "")
    voiceover = segment.get("voiceover", "")
    camera = segment.get("camera", "中景")
    motion = segment.get("motion", "")
    
    if image_index_map is None:
        image_index_map = {}
    
    keyframe_idx = image_index_map.get("keyframe", 1)
    product_idx = image_index_map.get("product", 2)
    
    if character_infos:
        char_descs = []
        char_image_refs = []
        
        for char in character_infos:
            char_id = char.get("id", "")
            char_desc = char.get("description", "")
            selected_images = char.get("selected_images", ["front_full"])
            
            char_descs.append(f"{char_id}的特征：{char_desc}")
            
            img_refs = []
            for img_type in selected_images:
                key = f"{char_id}_{img_type}"
                idx = image_index_map.get(key)
                if idx:
                    img_refs.append(f"图片{idx}")
            
            if img_refs:
                char_image_refs.append(f"将{'和'.join(img_refs)}中的人物定义为{char_id}")
        
        char_prompt = "\n".join(char_descs)
        char_ref_prompt = "\n".join(char_image_refs) if char_image_refs else ""
        char_names = "、".join([c.get("id", "") for c in character_infos])
        
        voice_parts = []
        if voiceover:
            for char in character_infos:
                char_id = char.get("id", "")
                voice_parts.append(f"{char_id}说道：{{{voiceover}}}")
        
        voice_prompt = "\n".join(voice_parts) if voice_parts else ""
        
        keyframe_ref = f"参考图片{keyframe_idx}作为场景参考" if keyframe_idx else ""
        product_ref = f"参考图片{product_idx}中的产品（{product_name}）" if product_idx in image_index_map else ""
        
        prompt = f"""
{char_ref_prompt}
{keyframe_ref}
{product_ref}

{char_prompt}

镜头1：{camera}，{char_names} {visual}。
{motion}
{voice_prompt}

全程画面高清电影纪实风，色调温暖，光影柔和；
人物面部稳定不变形，动作自然流畅，无卡顿无闪烁；
保持无字幕，不要生成Logo，不要生成水印。
产品{product_name}的外观保持不变，产品logo清晰可见。
"""
    else:
        keyframe_ref = f"参考图片{keyframe_idx}作为场景参考" if keyframe_idx else ""
        product_ref = f"参考图片{product_idx}中的产品（{product_name}）" if product_idx in image_index_map else ""
        
        prompt = f"""
{keyframe_ref}
{product_ref}

镜头1：{camera}，产品 {visual}。
{motion}

全程画面高清电影纪实风，色调温暖，光影柔和；
保持无字幕，不要生成Logo，不要生成水印。
产品{product_name}的外观保持不变，产品logo清晰可见。
"""
    
    return prompt.strip()


SEEDANCE_GUIDE_PATH = Path(__file__).resolve().parents[2] / "docs" / "seedance_prompt_guide.md"


def load_seedance_guide() -> str:
    """Load Seedance prompt guide content"""
    if SEEDANCE_GUIDE_PATH.exists():
        return SEEDANCE_GUIDE_PATH.read_text(encoding="utf-8")
    return ""


def optimize_prompt_with_gpt(
    segment: Dict[str, Any],
    character_infos: List[Dict[str, Any]],
    initial_prompt: str,
    duration: int = 5,
    product_image_name: Optional[str] = None,
    image_index_map: Dict[str, int] = None
) -> str:
    """
    Optimize prompt using GPT model with Seedance guide reference
    
    Args:
        segment: Script segment data
        character_infos: List of character information
        initial_prompt: Initial prompt to optimize
        duration: Video duration in seconds
        product_image_name: Optional product image filename
        image_index_map: Mapping of image identifiers to index numbers
    
    Returns:
        Optimized prompt string
    """
    if image_index_map is None:
        image_index_map = {}
    
    seedance_guide = load_seedance_guide()
    
    system_prompt = f"""你是视频生成提示词专家，专门优化 Doubao Seedance 2.0 的提示词。

## Seedance 提示词指南参考

{seedance_guide[:5000]}

## 核心优化要求

### 1. 图片引用格式（关键！）
- 必须使用"图片1、图片2..."指代素材，禁止用模糊表述
- 图片编号规则：图片1=关键帧，图片2=产品图（如有），图片3开始=人物图
- 定义主体时必须标明对应图片：将图片N中的[特征]定义为[人物名]
- 引用主体时保持名称一致

### 2. 结构要求
- 必须使用"镜头1、镜头2"分镜时序描述
- 每个镜头包含：运镜 + 动作 + 位置 + 音频
- 时长较短（<=5秒）时动作要简洁，不宜过多镜头切换

### 3. 动作描述
- 具体到肢体部位（手、腿、头、肩）
- 优先低缓连续小动作
- 情绪外化为具体动作细节（如"嘴角上扬"代替"开心"）

### 4. 音频约束
- 人物说话使用自然、清晰的音色
- 避免机械感、AI口音
- 语速适中，声音有情感起伏
- 台词用 {{中文}} 格式

### 5. 画质约束
- 保持无字幕、无Logo、无水印
- 人物面部稳定不变形
- 动作流畅无卡顿

### 6. 多人物场景（重要！）
- 明确标注每个人物对应哪张图片
- 人物名称前后一致
- 避免人物混淆或重复

### 7. 严格人物数量约束（最重要！）
- 只能使用提供的人物图片中已定义的人物，严禁生成额外人物
- 视频中出现的人物数量必须严格等于提供的人物图片数量
- 禁止生成任何未在图片中定义的路人、背景人物、群演等额外人物
- 如果提供0个人物图片，则视频中不能出现任何人物
- 如果提供1个人物图片，则视频中只能出现这1个人物
- 如果提供2个人物图片，则视频中只能出现这2个人物，不能多也不能少
- 必须在提示词末尾添加约束："视频全程禁止出现外形、着装完全一致的重复人物（双胞胎效果），禁止生成超出图片定义范围外的额外人物"

### 8. 视频连贯性约束（关键！）
- 每个片段的开头动作要与前一片段的结尾动作自然衔接
- 人物位置、姿态要保持合理的连续性
- 场景转换要有明确的过渡描述（如"转身走向"、"缓步移动到"）
- 产品位置要保持一致，不能突然位移
- 光影色调保持统一，避免片段间风格跳跃
- 人物服装、发型在所有片段中必须保持一致
- 如果是连续场景，动作要有惯性过渡，不能生硬切换

请直接输出优化后的提示词，不要解释。"""

    # Build detailed image index info
    keyframe_idx = image_index_map.get("keyframe", 1)
    product_idx = image_index_map.get("product", 2)
    
    image_info_lines = [f"- 图片{keyframe_idx}：关键帧/场景参考"]
    
    if product_idx in image_index_map.values():
        image_info_lines.append(f"- 图片{product_idx}：产品图（{product_image_name or '产品'}）")
    
    # Build character info with image mapping
    character_desc_lines = []
    if character_infos:
        for idx, c in enumerate(character_infos):
            char_id = c.get("id", f"人物{idx + 1}")
            char_desc = c.get("description", "无描述")
            selected_images = c.get("selected_images", ["front_full"])
            
            img_refs = []
            for img_type in selected_images:
                key = f"{char_id}_{img_type}"
                img_idx = image_index_map.get(key)
                if img_idx:
                    img_refs.append(f"图片{img_idx}")
            
            img_ref_str = "、".join(img_refs) if img_refs else "未分配图片"
            character_desc_lines.append(f"- {char_id}：{char_desc}（对应{img_ref_str}）")
            image_info_lines.append(f"- {img_ref_str}：人物【{char_id}】的{'+'.join(selected_images)}图")
    
    character_desc = "\n".join(character_desc_lines) if character_desc_lines else "无人物"
    image_index_info = "\n".join(image_info_lines)
    
    user_prompt = f"""## 图片编号映射（必读！）
{image_index_info}

## 任务信息
- 时长：{duration}秒
- 人物数量：{len(character_infos) if character_infos else 0}
- 片段阶段：{segment.get('stage', '未知')}
- 人物详情：
{character_desc}

## 原始提示词
{initial_prompt}

## 脚本信息
{json.dumps(segment, ensure_ascii=False, indent=2)}

## 关键约束（必须遵守！）
1. 人物数量约束：视频中只能出现 {len(character_infos) if character_infos else 0} 个人物，严禁生成额外人物
2. 人物必须从提供的图片中选择，使用正确的图片编号引用
3. 人物名称前后一致，避免混淆
4. 必须在提示词末尾添加约束："视频全程禁止出现重复人物（双胞胎效果），禁止生成额外人物"
5. {"如果脚本中提到其他人，只能用已定义的人物来替代，不能创建新人物" if character_infos else "此片段无人物，视频中不能出现任何人物"}
6. **视频连贯性**：注意与前后片段的动作衔接，人物位置、姿态、服装保持一致，产品位置稳定

请优化这个提示词，确保内容连贯、动作自然流畅。"""

    try:
        client = OpenAI(api_key=K_TOKEN_API_KEY, base_url=K_TOKEN_BASE_URL)
        
        print(f"[DEBUG] Calling GPT API: model={GENERATION_MODEL}, base_url={K_TOKEN_BASE_URL}")
        print(f"[DEBUG] API Key set: {bool(K_TOKEN_API_KEY)}")
        
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        # Handle both standard OpenAI response and KToken string response
        if isinstance(response, str):
            result = response.strip()
            print(f"[DEBUG] KToken API returned string directly, length: {len(result)} chars")
        elif hasattr(response, 'choices') and response.choices:
            result = response.choices[0].message.content.strip() if response.choices[0].message.content else initial_prompt
            print(f"[DEBUG] Standard OpenAI response, length: {len(result)} chars")
        else:
            print(f"[DEBUG] Unexpected response type: {type(response)}")
            result = str(response).strip() if response else initial_prompt
        
        return result if result else initial_prompt
    except Exception as e:
        print(f"[ERROR] GPT optimization failed: {e}")
        print(f"[ERROR] Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise


def generate_segment_video(
    keyframe_path: Path,
    character_paths: List[Path],
    prompt: str,
    duration: int,
    api_key: str,
    base_url: str = DEFAULT_SEEDANCE_BASE_URL,
    model: str = DEFAULT_SEEDANCE_MODEL,
    product_image_path: Optional[Path] = None,
    generate_audio: bool = True
) -> str:
    """
    Generate a single video segment using Seedance API
    
    Args:
        keyframe_path: Path to keyframe image
        character_paths: List of paths to character images
        prompt: Generation prompt
        duration: Video duration in seconds
        api_key: Seedance API key
        base_url: API base URL
        model: Model ID
        product_image_path: Optional path to product close-up image
        generate_audio: Whether to generate audio
    
    Returns:
        Video URL
    
    Raises:
        Exception: If video generation fails
    """
    import requests
    
    # Build content list with reference_image role
    content = [{"type": "text", "text": prompt}]
    
    # Add keyframe image
    if keyframe_path and keyframe_path.exists():
        content.append({
            "type": "image_url",
            "image_url": {"url": image_to_base64(keyframe_path)},
            "role": "reference_image"
        })
        print(f"[DEBUG] Added keyframe: {keyframe_path}")
        
        # Add product image if provided
        if product_image_path and product_image_path.exists():
            content.append({
                "type": "image_url",
                "image_url": {"url": image_to_base64(product_image_path)},
                "role": "reference_image"
            })
        
        # Add character images
        for char_path in character_paths:
            if char_path and char_path.exists():
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_to_base64(char_path)},
                    "role": "reference_image"
                })
    
    # Build payload
    payload = {
        "model": model,
        "content": content,
        "generate_audio": generate_audio,
        "ratio": "adaptive",
        "duration": duration,
    }
    
    # Create task using HTTP request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    create_url = f"{base_url.rstrip('/')}/contents/generations/tasks"
    response = requests.post(create_url, headers=headers, json=payload, timeout=120)
    
    if response.status_code >= 400:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
    
    create_result = response.json()
    task_id = create_result.get("id") or create_result.get("task_id")
    
    if not task_id:
        raise Exception(f"No task ID in response: {create_result}")
    
    # Poll for task completion
    query_url = f"{base_url.rstrip('/')}/contents/generations/tasks/{task_id}"
    max_poll_time = 600  # 10 minutes max wait time
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_poll_time:
            raise Exception(f"Polling timeout after {max_poll_time}s")
        
        time.sleep(10)
        
        poll_response = requests.get(query_url, headers=headers, timeout=120)
        
        if poll_response.status_code >= 400:
            raise Exception(f"Poll request failed with status {poll_response.status_code}: {poll_response.text}")
        
        result = poll_response.json()
        status = result.get("status", "").lower()
        
        if status in ("succeeded", "completed", "success", "done"):
            video_url = (
                result.get("video_url") or 
                result.get("data", {}).get("video_url") or
                result.get("content", {}).get("video_url")
            )
            
            print(f"[DEBUG] Video URL: {video_url[:80] if video_url else 'None'}...")
            
            if not video_url:
                raise Exception(f"No video URL in response: {result}")
            
            return video_url
        
        elif status in ("failed", "error", "cancelled"):
            error_msg = result.get("error") or result.get("message") or "Unknown error"
            raise Exception(f"Video generation failed: {error_msg}")
        
        # Continue polling for other statuses
        print(f"Status: {status}, waiting...")


def generate_all_segments(
    segments_config: List[SegmentConfig],
    output_dir: Path,
    api_key: str,
    base_url: str = DEFAULT_SEEDANCE_BASE_URL,
    model: str = DEFAULT_SEEDANCE_MODEL,
    generate_audio: bool = True,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Generate all video segments sequentially
    
    Official Seedance approach: Use previous video's last frame as next video's first frame
    for smooth transitions.
    
    Args:
        segments_config: List of segment configurations
        output_dir: Output directory
        api_key: Seedance API key
        base_url: API base URL
        model: Model ID
        generate_audio: Whether to generate audio
        progress_callback: Optional callback(progress_percent, status_message)
    
    Returns:
        Dictionary with generation results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    total = len(segments_config)
    
    for idx, seg_config in enumerate(segments_config):
        progress_percent = int((idx + 1) / total * 100)
        status_msg = f"正在生成 Segment {idx + 1}/{total}: {seg_config.stage}..."
        
        if progress_callback:
            progress_callback(progress_percent, status_msg)
        
        try:
            # Generate video
            video_url = generate_segment_video(
                keyframe_path=seg_config.keyframe_path,
                character_paths=seg_config.character_paths,
                prompt=seg_config.prompt,
                duration=seg_config.duration,
                api_key=api_key,
                base_url=base_url,
                model=model,
                product_image_path=seg_config.product_image_path,
                generate_audio=generate_audio
            )
            
            # Download video
            video_path = output_dir / f"S{seg_config.segment_idx + 1:02d}.mp4"
            download_file(video_url, video_path)
            print(f"[DEBUG] Video saved to: {video_path}")
            
            results.append({
                "segment_idx": seg_config.segment_idx,
                "stage": seg_config.stage,
                "video_path": str(video_path),
                "success": True
            })
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Segment {idx + 1} generation failed: {str(e)}",
                "results": results
            }
    
    return {
        "success": True,
        "results": results
    }


def concatenate_videos_ffmpeg(video_paths: List[Path], output_path: Path) -> Path:
    """
    Concatenate videos using ffmpeg
    
    Args:
        video_paths: List of video paths in order
        output_path: Output path for concatenated video
    
    Returns:
        Path to concatenated video
    """
    import shutil
    import subprocess
    
    # Find ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = shutil.which("ffmpeg")
        if not ffmpeg_exe:
            raise RuntimeError("ffmpeg is required. Install imageio-ffmpeg or system ffmpeg.")
    
    # Create concat list
    concat_list = output_path.parent / "concat_list.txt"
    lines = []
    for vp in video_paths:
        if vp.exists():
            escaped = str(vp.resolve()).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
    
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    # Run ffmpeg concat
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


def make_compatible_video(input_path: Path, output_path: Path) -> Path:
    """
    Re-encode video for broader compatibility
    
    Args:
        input_path: Input video path
        output_path: Output video path
    
    Returns:
        Path to compatible video
    """
    import shutil
    import subprocess
    
    # Find ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = shutil.which("ffmpeg")
        if not ffmpeg_exe:
            raise RuntimeError("ffmpeg is required.")
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_path),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.1",
        "-r", "24",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path

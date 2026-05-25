import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORYBOARD = BASE_DIR / "outputs" / "keyframes" / "storyboard.json"
DEFAULT_KEYFRAME_DIR = BASE_DIR / "outputs" / "keyframes" / "images"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "videos"

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedance-2-0-260128"
DEFAULT_RATIO = "9:16"
DEFAULT_RESOLUTION = ""
DEFAULT_DURATION = 5

SUCCEEDED_STATUSES = {"succeeded", "completed", "success", "done"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}
PENDING_STATUSES = {"submitted", "queued", "running", "processing", "in_progress", "created"}


@dataclass
class VideoJob:
    shot_id: str
    image_path: Path
    prompt: str
    duration: int
    output_path: Path
    next_image_path: Optional[Path] = None


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def http_json(
    method: str,
    url: str,
    api_key: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 180,
) -> Dict[str, Any]:
    body = b""
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    cmd = [
        "curl",
        "-sS",
        "-X",
        method,
        url,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "--max-time",
        str(timeout),
        "-w",
        "\n%{http_code}",
    ]
    if payload is not None:
        cmd.extend(["--data-binary", "@-"])

    completed = subprocess.run(cmd, input=body, capture_output=True, check=False)
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise RuntimeError(f"{method} {url} failed: {stderr}")

    raw, _, code_text = stdout.rpartition("\n")
    status_code = int(code_text.strip() or "0")
    if status_code >= 400:
        raise RuntimeError(f"{method} {url} failed with HTTP {status_code}: {raw}")

    if not raw.strip():
        return {}
    return json.loads(raw)


def download_file(url: str, path: Path, timeout: int = 300) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "-sSL", "--max-time", str(timeout), "-o", str(path), url]
    completed = subprocess.run(cmd, capture_output=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Download failed: {stderr}")


def image_to_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def image_ref(path: Path, mode: str) -> str:
    if mode == "base64":
        return image_to_data_url(path)
    if mode == "path":
        return str(path)
    raise ValueError(f"Unsupported image ref mode: {mode}")


def compact(text: Any, max_chars: int = 500) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."


def seconds_to_duration(value: Any, fallback: int) -> int:
    try:
        duration = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback
    return max(5, min(15, duration))


def build_seedance_prompt(
    storyboard: Dict[str, Any],
    shot: Dict[str, Any],
    camera_fixed: bool,
) -> str:
    style = storyboard.get("style_guide", {})
    camera_fixed_flag = "true" if camera_fixed else "false"
    parts = [
        f"生成一段竖屏短视频广告镜头，镜头编号 {shot.get('shot_id', '')}。",
        f"画面内容：{compact(shot.get('visual_beat'), 260)}",
        f"镜头运动：{compact(shot.get('motion'), 180)}",
        f"机位：{compact(shot.get('camera'), 180)}",
        f"广告目的：{compact(shot.get('purpose'), 120)}",
        f"口播语境：{compact(shot.get('voiceover'), 260)}",
        "音频要求：使用轻快、温暖、原创免版权的家庭氛围背景音乐；用自然清晰的普通话女声念出口播语境，语速适中，声音像短视频带货广告旁白；不要引用真实歌曲、影视剧、歌手、品牌或版权内容。",
        "字幕要求：视频画面中不要出现字幕、口播文字、促销大字、角标文案或任何可读文字，只保留音频念白。",
        "界面要求：电视和点歌页只使用虚构分类、抽象图标和占位歌单，不出现真实歌名、影视名、平台名、商标或版权素材。",
        "产品要求：保持首帧里的 K7 木纹箱体、黑色前面板、无线麦克风外观，不要替换成其他款式。",
        "保持首帧中的客厅、电视、产品主机、麦克风和空间风格一致；让动作自然连贯，产品和电视界面清晰可见。",
        "首帧不包含人脸。视频生成阶段可以让虚构的 AI 广告演员家庭成员从画面边缘自然入镜，人物不对应任何真实身份；优先使用侧脸、背影、中远景和手部互动，避免清晰正脸特写和真实人物肖像感。",
        "真实商业广告质感，干净明亮，避免水印、乱码字幕、夸张变形、错误手指和品牌侵权标识。",
    ]
    if style:
        parts.append(f"整体风格参考：{compact(style.get('visual_style'), 180)}")
        parts.append(f"连续性要求：{compact(style.get('continuity'), 180)}")
    if camera_fixed:
        parts.append(f"保持镜头稳定，camera_fixed={camera_fixed_flag}。")
    return "\n".join(part for part in parts if part.strip())


def find_keyframe(shot_id: str, keyframe_dir: Path) -> Optional[Path]:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = keyframe_dir / f"{shot_id}{ext}"
        if path.exists():
            return path
    return None


def build_jobs(
    storyboard: Dict[str, Any],
    keyframe_dir: Path,
    output_dir: Path,
    duration: int,
    ratio: str,
    resolution: str,
    camera_fixed: bool,
    use_last_frame: bool,
    include_shots: Optional[List[str]],
    skip_shots: Optional[List[str]],
) -> Tuple[List[VideoJob], List[Dict[str, Any]]]:
    shots = storyboard.get("storyboard") or []
    include_set = {item.upper() for item in include_shots or []}
    skip_set = {item.upper() for item in skip_shots or []}
    jobs: List[VideoJob] = []
    skipped: List[Dict[str, Any]] = []

    for idx, shot in enumerate(shots):
        shot_id = str(shot.get("shot_id") or f"S{idx + 1:02d}").upper()
        if include_set and shot_id not in include_set:
            continue
        if shot_id in skip_set:
            skipped.append({"shot_id": shot_id, "status": "skipped_by_user"})
            continue

        image_path = find_keyframe(shot_id, keyframe_dir)
        if not image_path:
            skipped.append({"shot_id": shot_id, "status": "missing_keyframe"})
            continue

        next_image_path = None
        if use_last_frame and idx + 1 < len(shots):
            next_id = str(shots[idx + 1].get("shot_id") or f"S{idx + 2:02d}").upper()
            next_image_path = find_keyframe(next_id, keyframe_dir)

        job_duration = seconds_to_duration(shot.get("duration_sec"), duration)
        prompt = build_seedance_prompt(
            storyboard=storyboard,
            shot=shot,
            camera_fixed=camera_fixed,
        )
        jobs.append(
            VideoJob(
                shot_id=shot_id,
                image_path=image_path,
                next_image_path=next_image_path,
                prompt=prompt,
                duration=job_duration,
                output_path=output_dir / "clips" / f"{shot_id}.mp4",
            )
        )

    return jobs, skipped


def build_payload(
    job: VideoJob,
    model: str,
    image_mode: str,
    generate_audio: bool,
    ratio: str,
    resolution: str,
    watermark: Optional[bool],
    callback_url: Optional[str],
) -> Dict[str, Any]:
    content: List[Dict[str, Any]] = [
        {"type": "text", "text": job.prompt},
        {
            "type": "image_url",
            "image_url": {"url": image_ref(job.image_path, image_mode)},
            "role": "reference_image",
        },
    ]
    if job.next_image_path:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_ref(job.next_image_path, image_mode)},
                "role": "reference_image",
            }
        )

    payload: Dict[str, Any] = {
        "model": model,
        "content": content,
        "generate_audio": generate_audio,
        "ratio": ratio,
        "duration": job.duration,
    }
    if resolution:
        payload["resolution"] = resolution
    if watermark is not None:
        payload["watermark"] = watermark
    if callback_url:
        payload["callback_url"] = callback_url
    return payload


def endpoint(base_url: str, suffix: str) -> str:
    return f"{base_url.rstrip('/')}/{suffix.lstrip('/')}"


def extract_task_id(response: Dict[str, Any]) -> str:
    task_id = response.get("id") or response.get("task_id") or response.get("taskId")
    data = response.get("data")
    if not task_id and isinstance(data, dict):
        task_id = data.get("id") or data.get("task_id") or data.get("taskId")
    if not task_id:
        raise RuntimeError(f"Create-task response does not include task id: {response}")
    return str(task_id)


def extract_status(response: Dict[str, Any]) -> str:
    status = response.get("status") or response.get("state") or response.get("task_status")
    data = response.get("data")
    if not status and isinstance(data, dict):
        status = data.get("status") or data.get("state") or data.get("task_status")
    return str(status or "").lower()


def find_first_url(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            found = find_first_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in ("video_url", "file_url", "url", "download_url"):
            found = value.get(key)
            if isinstance(found, str) and found.startswith(("http://", "https://")):
                return found
        for item in value.values():
            found = find_first_url(item)
            if found:
                return found
    return None


def extract_video_url(response: Dict[str, Any]) -> Optional[str]:
    return find_first_url(response)


def submit_and_wait(
    job: VideoJob,
    base_url: str,
    api_key: str,
    payload: Dict[str, Any],
    poll_interval: int,
    timeout_sec: int,
) -> Dict[str, Any]:
    create_url = endpoint(base_url, "contents/generations/tasks")
    created = http_json("POST", create_url, api_key=api_key, payload=payload)
    task_id = extract_task_id(created)

    deadline = time.time() + timeout_sec
    query_url = endpoint(base_url, f"contents/generations/tasks/{task_id}")
    last_response: Dict[str, Any] = created
    while time.time() < deadline:
        time.sleep(poll_interval)
        last_response = http_json("GET", query_url, api_key=api_key)
        status = extract_status(last_response)
        if status in SUCCEEDED_STATUSES:
            video_url = extract_video_url(last_response)
            if not video_url:
                raise RuntimeError(f"Task {task_id} succeeded but no video URL was returned: {last_response}")
            download_file(video_url, job.output_path)
            return {
                "shot_id": job.shot_id,
                "task_id": task_id,
                "status": status,
                "video_url": video_url,
                "output_path": display_path(job.output_path),
                "raw_response": last_response,
            }
        if status in FAILED_STATUSES:
            return {
                "shot_id": job.shot_id,
                "task_id": task_id,
                "status": status,
                "output_path": "",
                "raw_response": last_response,
            }
        if status and status not in PENDING_STATUSES:
            print(f"[{job.shot_id}] Unknown status {status}; keep polling.")

    raise TimeoutError(f"Task {task_id} for {job.shot_id} did not finish within {timeout_sec}s.")


def write_concat_file(clips: Iterable[Path], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for clip in clips:
        escaped = str(clip.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        found = shutil.which("ffmpeg")
        if found:
            return found
    raise RuntimeError("ffmpeg is required for --concat. Install imageio-ffmpeg or system ffmpeg.")


def concat_clips(clips: List[Path], output_path: Path) -> None:
    if not clips:
        raise RuntimeError("No clips available for concat.")
    concat_list = output_path.parent / "concat_list.txt"
    write_concat_file(clips, concat_list)
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def make_compatible_video(input_path: Path, output_path: Path) -> None:
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "baseline",
        "-level",
        "3.1",
        "-r",
        "24",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def parse_list(value: str) -> List[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def run(args: argparse.Namespace) -> Dict[str, Any]:
    storyboard_path = Path(args.storyboard)
    keyframe_dir = Path(args.keyframe_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    storyboard = read_json(storyboard_path)
    jobs, skipped = build_jobs(
        storyboard=storyboard,
        keyframe_dir=keyframe_dir,
        output_dir=output_dir,
        duration=args.duration,
        ratio=args.ratio,
        resolution=args.resolution,
        camera_fixed=args.camera_fixed,
        use_last_frame=args.use_last_frame,
        include_shots=parse_list(args.only_shots),
        skip_shots=parse_list(args.skip_shots),
    )

    payloads = []
    for job in jobs:
        payload = build_payload(
            job=job,
            model=args.model,
            image_mode=args.image_mode,
            generate_audio=args.generate_audio,
            ratio=args.ratio,
            resolution=args.resolution,
            watermark=args.watermark,
            callback_url=args.callback_url,
        )
        preview_payload = json.loads(json.dumps(payload, ensure_ascii=False))
        for item in preview_payload.get("content", []):
            if item.get("type") == "image_url" and args.image_mode == "base64":
                url = item.get("image_url", {}).get("url", "")
                item["image_url"]["url"] = f"{url[:48]}...<base64 omitted>"
        payloads.append(
            {
                "shot_id": job.shot_id,
                "duration": job.duration,
                "image_path": display_path(job.image_path),
                "next_image_path": display_path(job.next_image_path) if job.next_image_path else "",
                "output_path": display_path(job.output_path),
                "payload": preview_payload,
            }
        )

    plan_path = output_dir / "seedance_request_plan.json"
    write_json(
        plan_path,
        {
            "storyboard": display_path(storyboard_path),
            "base_url": args.base_url,
            "model": args.model,
            "submit": args.submit,
            "jobs": payloads,
            "skipped": skipped,
        },
    )

    results: List[Dict[str, Any]] = []
    if args.submit:
        api_key = os.getenv("SEEDANCE_API_KEY") or os.getenv("LAS_API_KEY") or os.getenv("ARK_API_KEY")
        if not api_key:
            raise RuntimeError("Set SEEDANCE_API_KEY, LAS_API_KEY, or ARK_API_KEY before using --submit.")
        for index, job in enumerate(jobs, start=1):
            if job.output_path.exists() and not args.overwrite:
                results.append(
                    {
                        "shot_id": job.shot_id,
                        "status": "skipped_existing",
                        "output_path": display_path(job.output_path),
                    }
                )
                continue
            payload = build_payload(
                job=job,
                model=args.model,
                image_mode=args.image_mode,
                generate_audio=args.generate_audio,
                ratio=args.ratio,
                resolution=args.resolution,
                watermark=args.watermark,
                callback_url=args.callback_url,
            )
            print(f"[{index}/{len(jobs)}] submit {job.shot_id}")
            results.append(
                submit_and_wait(
                    job=job,
                    base_url=args.base_url,
                    api_key=api_key,
                    payload=payload,
                    poll_interval=args.poll_interval,
                    timeout_sec=args.timeout,
                )
            )

    results_path = output_dir / "seedance_results.json"
    write_json(results_path, {"results": results, "skipped": skipped})

    final_video_path = output_dir / "final_seedance_video.mp4"
    compatible_video_path = output_dir / "final_seedance_video_compatible.mp4"
    if args.concat:
        clip_paths = [
            output_dir / "clips" / f"{job.shot_id}.mp4"
            for job in jobs
            if (output_dir / "clips" / f"{job.shot_id}.mp4").exists()
        ]
        concat_clips(clip_paths, final_video_path)
        if args.compatible_output:
            make_compatible_video(final_video_path, compatible_video_path)

    return {
        "plan_path": str(plan_path),
        "results_path": str(results_path),
        "final_video_path": str(final_video_path) if final_video_path.exists() else "",
        "compatible_video_path": str(compatible_video_path) if compatible_video_path.exists() else "",
        "job_count": len(jobs),
        "skipped_count": len(skipped),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Seedance image-to-video clips from keyframes.")
    parser.add_argument("--storyboard", default=str(DEFAULT_STORYBOARD), help="Path to outputs/keyframes/storyboard.json.")
    parser.add_argument("--keyframe-dir", default=str(DEFAULT_KEYFRAME_DIR), help="Directory containing S01.png style keyframes.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for video task plan, clips, and results.")
    parser.add_argument("--base-url", default=os.getenv("SEEDANCE_BASE_URL", DEFAULT_BASE_URL), help="Seedance API base URL.")
    parser.add_argument("--model", default=os.getenv("SEEDANCE_MODEL", DEFAULT_MODEL), help="Seedance model ID.")
    parser.add_argument("--ratio", default=DEFAULT_RATIO, help="Video aspect ratio, e.g. 9:16.")
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION, help="Video resolution, e.g. 720p or 1080p.")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Fallback clip duration in seconds.")
    parser.add_argument("--image-mode", choices=["base64", "path"], default="base64", help="How to pass local keyframes to API.")
    parser.add_argument("--generate-audio", action="store_true", help="Ask Seedance to generate native audio if the model supports it.")
    parser.add_argument("--watermark", action=argparse.BooleanOptionalAction, default=None, help="Pass watermark true/false when the gateway supports it.")
    parser.add_argument("--camera-fixed", action="store_true", help="Use --cf true in the Seedance prompt.")
    parser.add_argument("--use-last-frame", action="store_true", help="Use the next shot keyframe as last_frame for smoother transitions.")
    parser.add_argument("--only-shots", default="", help="Comma-separated shot IDs to include, e.g. S01,S02.")
    parser.add_argument("--skip-shots", default="", help="Comma-separated shot IDs to skip, e.g. S03,S07.")
    parser.add_argument("--callback-url", default="", help="Optional callback URL for async Seedance task status changes.")
    parser.add_argument("--submit", action="store_true", help="Actually call Seedance API. Without this, only writes request plan.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate clips even if local mp4 already exists.")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between task status polls.")
    parser.add_argument("--timeout", type=int, default=900, help="Max seconds to wait per Seedance task.")
    parser.add_argument("--concat", action="store_true", help="Concatenate generated clips with ffmpeg after generation.")
    parser.add_argument("--compatible-output", action="store_true", help="After --concat, also re-encode a conservative H.264/AAC compatible MP4.")
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

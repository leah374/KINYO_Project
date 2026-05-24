import argparse
import base64
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openai import OpenAI
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE_DIR / "outputs" / "final_script" / "final_script.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "keyframes"

DEFAULT_OPENAI_BASE_URL = "https://ai.ktokenhub.app"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "auto"
DEFAULT_ASPECT_RATIO = "9:16"


@dataclass
class TimeRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)

    def label(self) -> str:
        return f"{_fmt_sec(self.start)}-{_fmt_sec(self.end)}s"


def _fmt_sec(value: float) -> str:
    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_time_range(value: Any, fallback_start: float, fallback_duration: float) -> TimeRange:
    text = str(value or "")
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if len(numbers) >= 2 and numbers[1] > numbers[0]:
        return TimeRange(numbers[0], numbers[1])
    if len(numbers) == 1:
        return TimeRange(numbers[0], numbers[0] + fallback_duration)
    return TimeRange(fallback_start, fallback_start + fallback_duration)


def split_visual_beats(segment: Dict[str, Any], max_beats: int) -> List[str]:
    visual = str(segment.get("visual") or "").strip()
    shot_hint = str(segment.get("shot_hint") or "").strip()
    source = visual
    if shot_hint:
        source = f"{visual}。镜头提示：{shot_hint}"

    parts = [
        item.strip(" ，,；;。.")
        for item in re.split(r"[。；;]\s*", source)
        if item.strip(" ，,；;。.")
    ]
    if not parts:
        parts = [str(segment.get("purpose") or segment.get("stage") or "关键画面")]

    merged: List[str] = []
    for part in parts:
        if len(part) < 12 and merged:
            merged[-1] = f"{merged[-1]}，{part}"
        else:
            merged.append(part)

    return merged[:max_beats]


def allocate_ranges(parent: TimeRange, count: int) -> List[TimeRange]:
    count = max(1, count)
    step = parent.duration / count
    return [
        TimeRange(parent.start + step * idx, parent.start + step * (idx + 1))
        for idx in range(count)
    ]


def stage_shot_budget(stage: str, remaining: int) -> int:
    stage_key = stage.lower()
    if stage_key == "twist":
        return min(5, remaining)
    if stage_key in {"hook", "setup"}:
        return min(2, remaining)
    return min(1, remaining)


def compact_text(text: Any, max_chars: int = 420) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."


def build_storyboard(final_script: Dict[str, Any], max_shots: int) -> Dict[str, Any]:
    planning = final_script.get("planning", {})
    script = final_script.get("script", final_script)
    segments = script.get("segments") or []
    if not segments:
        raise ValueError("Input JSON does not contain script.segments.")

    storyboard: List[Dict[str, Any]] = []
    cursor = 0.0
    remaining = max(1, max_shots)

    for segment in segments:
        parent_range = parse_time_range(segment.get("time"), cursor, 5.0)
        cursor = parent_range.end
        stage = str(segment.get("stage") or "Shot")
        budget = stage_shot_budget(stage, remaining)
        beats = split_visual_beats(segment, budget)
        ranges = allocate_ranges(parent_range, len(beats))

        for idx, (beat, time_range) in enumerate(zip(beats, ranges), start=1):
            shot_no = len(storyboard) + 1
            shot_id = f"S{shot_no:02d}"
            image_prompt = build_image_prompt(
                title=str(script.get("title") or "家庭影音广告"),
                planning=planning,
                segment=segment,
                beat=beat,
                shot_id=shot_id,
            )
            storyboard.append(
                {
                    "shot_id": shot_id,
                    "stage": stage,
                    "time": time_range.label(),
                    "duration_sec": round(time_range.duration, 2),
                    "purpose": segment.get("purpose", ""),
                    "visual_beat": beat,
                    "voiceover": segment.get("voiceover", ""),
                    "subtitle": segment.get("subtitle", ""),
                    "camera": infer_camera(beat, segment),
                    "motion": infer_motion(stage, beat),
                    "keyframe_prompt": image_prompt,
                    "negative_prompt": negative_prompt(),
                }
            )
            remaining -= 1
            if remaining <= 0:
                break
        if remaining <= 0:
            break

    return {
        "source_title": script.get("title", ""),
        "objective": script.get("objective", ""),
        "aspect_ratio": DEFAULT_ASPECT_RATIO,
        "style_guide": style_guide(),
        "storyboard": storyboard,
    }


def style_guide() -> Dict[str, str]:
    return {
        "format": "vertical short video, 9:16, realistic commercial keyframe",
        "visual_style": "clean Chinese ecommerce short-video ad, warm family living room, practical product demo, natural light, high clarity",
        "characters": "Chinese family, presenter, grandparents, parents, child when needed",
        "product": "compact home karaoke and cinema set-top box, HDMI cable, TV screen, wireless microphones, remote control",
        "continuity": "use the same cozy living room, same TV wall, same product kit, consistent wardrobe and warm lighting across keyframes",
    }


def build_image_prompt(
    title: str,
    planning: Dict[str, Any],
    segment: Dict[str, Any],
    beat: str,
    shot_id: str,
) -> str:
    core_selling_point = compact_text(planning.get("core_selling_point"), 260)
    target_user = compact_text(planning.get("target_user"), 180)
    subtitle = compact_text(segment.get("subtitle"), 160)
    voiceover = compact_text(segment.get("voiceover"), 260)
    purpose = compact_text(segment.get("purpose"), 120)

    return (
        f"Create keyframe {shot_id} for a vertical 9:16 Chinese short-video advertisement. "
        f"Campaign title: {title}. "
        f"Scene: {beat}. "
        f"Ad purpose: {purpose}. "
        f"Target audience: {target_user}. "
        f"Core product promise: {core_selling_point}. "
        "Show a realistic home karaoke and cinema product demo in a cozy modern Chinese living room: "
        "a TV, compact set-top box, HDMI cable, wireless microphones, remote control, and family members interacting naturally. "
        "Make the product and TV interface clearly visible, with believable hands-on operation and warm family energy. "
        f"Voiceover context: {voiceover}. "
        f"Optional large overlay caption concept for later editing: {subtitle}. "
        "Photorealistic, commercial lighting, sharp focus, stable composition, no brand logos, no watermark, no tiny unreadable UI text."
    )


def negative_prompt() -> str:
    return (
        "Avoid distorted hands, extra fingers, fake logos, messy cables unless requested, unreadable dense text, "
        "foreign-language captions, low-resolution screen UI, over-stylized illustration, dark blurry image, watermark."
    )


def infer_camera(beat: str, segment: Dict[str, Any]) -> str:
    text = f"{beat} {segment.get('shot_hint', '')}"
    if any(key in text for key in ["接口", "特写", "麦克风", "主机", "遥控器"]):
        return "close-up product demo shot, hands and device in frame"
    if any(key in text for key in ["全家", "家庭", "客厅", "沙发", "欢唱"]):
        return "medium-wide living-room shot, family and TV both visible"
    if any(key in text for key in ["屏幕", "界面", "点歌", "电影", "电视剧"]):
        return "over-the-shoulder TV interface shot, screen content dominant"
    return "medium shot with presenter, product, and TV visible"


def infer_motion(stage: str, beat: str) -> str:
    text = f"{stage} {beat}"
    if "快切" in text or stage.lower() == "hook":
        return "fast cut, strong contrast, energetic opening beat"
    if any(key in text for key in ["插", "连接", "切换", "语音"]):
        return "hands-on demonstration, clear before-and-after action"
    if stage.lower() == "cta":
        return "final offer frame, product and family benefit held clearly"
    return "smooth explanatory product shot"


def iter_prompt_rows(storyboard_payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for shot in storyboard_payload.get("storyboard", []):
        yield {
            "shot_id": shot["shot_id"],
            "time": shot["time"],
            "stage": shot["stage"],
            "prompt": shot["keyframe_prompt"],
            "negative_prompt": shot["negative_prompt"],
        }


def write_prompts_jsonl(path: Path, storyboard_payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in iter_prompt_rows(storyboard_payload)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def storyboard_to_markdown(storyboard_payload: Dict[str, Any]) -> str:
    lines = [
        f"# {storyboard_payload.get('source_title', '分镜与关键帧')}",
        "",
        f"- objective: {storyboard_payload.get('objective', '')}",
        f"- aspect_ratio: {storyboard_payload.get('aspect_ratio', DEFAULT_ASPECT_RATIO)}",
        "",
        "## Style Guide",
        "",
    ]
    for key, value in storyboard_payload.get("style_guide", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Storyboard", ""])
    for shot in storyboard_payload.get("storyboard", []):
        lines.extend(
            [
                f"### {shot['shot_id']} {shot['stage']} {shot['time']}",
                f"- duration_sec: {shot['duration_sec']}",
                f"- purpose: {shot.get('purpose', '')}",
                f"- visual_beat: {shot.get('visual_beat', '')}",
                f"- camera: {shot.get('camera', '')}",
                f"- motion: {shot.get('motion', '')}",
                f"- subtitle: {shot.get('subtitle', '')}",
                f"- prompt: {shot.get('keyframe_prompt', '')}",
                f"- negative_prompt: {shot.get('negative_prompt', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def extract_image_b64(response: Any) -> Optional[str]:
    data = getattr(response, "data", None)
    if data:
        first = data[0]
        return getattr(first, "b64_json", None) or getattr(first, "b64", None)

    output = getattr(response, "output", None)
    if output:
        for item in output:
            result = getattr(item, "result", None)
            if result:
                return result
    return None


def generate_keyframes(
    storyboard_payload: Dict[str, Any],
    output_dir: Path,
    base_url: Optional[str],
    image_model: str,
    size: str,
    quality: str,
    sleep_sec: float,
    retries: int,
    overwrite: bool,
    skip_shots: List[str],
) -> List[Dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when --generate-images is set.")

    client_kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url.rstrip("/")
    client = OpenAI(**client_kwargs)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Dict[str, Any]] = []
    skip_set = {item.strip().upper() for item in skip_shots if item.strip()}

    for row in iter_prompt_rows(storyboard_payload):
        shot_id = row["shot_id"]
        image_path = images_dir / f"{shot_id}.png"
        if shot_id.upper() in skip_set:
            generated.append(
                {
                    "shot_id": shot_id,
                    "image_path": "",
                    "model": image_model,
                    "base_url": base_url or "openai_default",
                    "size": size,
                    "quality": quality,
                    "status": "skipped_by_user",
                }
            )
            continue
        if image_path.exists() and not overwrite:
            generated.append(
                {
                    "shot_id": shot_id,
                    "image_path": str(image_path.relative_to(BASE_DIR)),
                    "model": image_model,
                    "base_url": base_url or "openai_default",
                    "size": size,
                    "quality": quality,
                    "status": "skipped_existing",
                }
            )
            continue

        prompt = f"{row['prompt']}\n\nNegative prompt: {row['negative_prompt']}"
        response = None
        for attempt in range(1, retries + 2):
            try:
                response = client.images.generate(
                    model=image_model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1,
                )
                break
            except (APIConnectionError, APITimeoutError, RateLimitError, APIError):
                if attempt > retries:
                    raise
                time.sleep(min(6 * attempt, 30))

        image_b64 = extract_image_b64(response)
        if not image_b64:
            raise RuntimeError(f"Image response for {shot_id} did not include base64 image data.")
        image_path.write_bytes(base64.b64decode(image_b64))
        generated.append(
            {
                "shot_id": shot_id,
                "image_path": str(image_path.relative_to(BASE_DIR)),
                "model": image_model,
                "base_url": base_url or "openai_default",
                "size": size,
                "quality": quality,
                "status": "generated",
            }
        )
        time.sleep(sleep_sec)

    return generated


def run(
    input_path: Path,
    output_dir: Path,
    max_shots: int,
    generate_images: bool,
    base_url: Optional[str],
    image_model: str,
    size: str,
    quality: str,
    sleep_sec: float,
    retries: int,
    overwrite: bool,
    skip_shots: List[str],
) -> Dict[str, Path]:
    payload = read_json(input_path)
    storyboard_payload = build_storyboard(payload, max_shots=max_shots)

    output_dir.mkdir(parents=True, exist_ok=True)
    storyboard_json = output_dir / "storyboard.json"
    storyboard_md = output_dir / "storyboard.md"
    prompts_jsonl = output_dir / "image_prompts.jsonl"

    write_json(storyboard_json, storyboard_payload)
    storyboard_md.write_text(storyboard_to_markdown(storyboard_payload), encoding="utf-8")
    write_prompts_jsonl(prompts_jsonl, storyboard_payload)

    generated_json = output_dir / "generated_images.json"
    if generate_images:
        generated = generate_keyframes(
            storyboard_payload=storyboard_payload,
            output_dir=output_dir,
            base_url=base_url,
            image_model=image_model,
            size=size,
            quality=quality,
            sleep_sec=sleep_sec,
            retries=retries,
            overwrite=overwrite,
            skip_shots=skip_shots,
        )
        write_json(generated_json, generated)

    return {
        "storyboard_json": storyboard_json,
        "storyboard_md": storyboard_md,
        "prompts_jsonl": prompts_jsonl,
        "generated_images_json": generated_json,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate storyboard and OpenAI image prompts from final_script.json.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to outputs/final_script/final_script.json.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for storyboard and keyframes.")
    parser.add_argument("--max-shots", type=int, default=10, help="Maximum storyboard shots/keyframes.")
    parser.add_argument("--generate-images", action="store_true", help="Call OpenAI image generation and save PNG keyframes.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
        help="OpenAI-compatible API base URL. Defaults to OPENAI_BASE_URL or the project token factory.",
    )
    parser.add_argument("--image-model", default=DEFAULT_IMAGE_MODEL, help="OpenAI image model, e.g. gpt-image-2.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size. Use auto unless a fixed size is required.")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="Image quality. Use auto unless a fixed quality is required.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between image generation calls.")
    parser.add_argument("--retries", type=int, default=2, help="Retries for transient image API failures.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate images even if output PNG files already exist.")
    parser.add_argument(
        "--skip-shots",
        default="",
        help="Comma-separated shot IDs to skip during image generation, e.g. S03,S07.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        max_shots=args.max_shots,
        generate_images=args.generate_images,
        base_url=args.base_url,
        image_model=args.image_model,
        size=args.size,
        quality=args.quality,
        sleep_sec=args.sleep,
        retries=args.retries,
        overwrite=args.overwrite,
        skip_shots=[item.strip() for item in args.skip_shots.split(",") if item.strip()],
    )
    print(json.dumps({key: str(value) for key, value in paths.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

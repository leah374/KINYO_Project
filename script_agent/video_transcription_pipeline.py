import csv
import base64
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4v", ".wmv"}
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "raw_videos"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "transcription_result"
ASR_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ASR_TRANSCRIBE_MODEL = "qwen3-asr-flash-2026-02-10"
ASR_API_KEY = os.getenv("ASR_API_KEY", "")
MAX_AUDIO_MB = 7


def now_iso():
    """返回当前本地时间的 ISO 格式字符串，精确到秒，用于记录任务开始、结束和结果创建时间。"""
    return datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path, chunk_size=1024 * 1024):
    """按块读取文件并计算 SHA-256 哈希值，用于判断视频文件是否已经处理过，避免重复转写。"""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def get_ffmpeg_path():
    """查找可用的 ffmpeg 可执行文件路径。优先使用环境变量 FFMPEG_PATH，其次尝试 imageio_ffmpeg，最后回退到系统命令 ffmpeg。"""
    explicit = os.getenv("FFMPEG_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    try:
        import imageio_ffmpeg

        ffmpeg_path = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if ffmpeg_path.exists():
            return str(ffmpeg_path)
    except Exception:
        pass
    known_paths = [
        Path(r"C:\Users\10476\anaconda3\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"),
    ]
    for path in known_paths:
        if path.exists():
            return str(path)
    return "ffmpeg"


def run_ffprobe(ffmpeg_path: str, video_path: Path):
    """调用 ffprobe 读取视频的基础媒体信息，包括时长和音视频流编码信息；读取失败时返回空字典，不中断主流程。"""
    ffprobe = Path(ffmpeg_path).with_name("ffprobe.exe")
    if not ffprobe.exists():
        return {}
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def extract_audio(ffmpeg_path: str, video_path: Path, work_dir: Path):
    """使用 ffmpeg 从视频文件中提取单声道、16kHz、低码率的 MP3 音频，供后续语音识别模型转写。"""
    audio_path = work_dir / f"{video_path.stem}.mp3"
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "32k",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError(result.stderr[-2000:] or "ffmpeg audio extraction failed")
    return audio_path


def split_audio_if_needed(ffmpeg_path: str, audio_path: Path, work_dir: Path):
    """检查音频文件大小，若超过 TRANSCRIBE_MAX_AUDIO_MB 限制，则按固定时长切分为多个 MP3 片段，避免单次接口请求过大。"""
    max_bytes = MAX_AUDIO_MB * 1024 * 1024
    if audio_path.stat().st_size <= max_bytes:
        return [audio_path]

    parts_dir = work_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    pattern = parts_dir / "part_%03d.mp3"
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        "1200",
        "-c",
        "copy",
        str(pattern),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "ffmpeg audio split failed")
    parts = sorted(parts_dir.glob("part_*.mp3"))
    if not parts:
        raise RuntimeError("audio split produced no parts")
    return parts


def transcribe_audio(client: OpenAI, audio_paths):
    """逐个读取音频片段并转为 base64 data URL，调用 DashScope/OpenAI 兼容接口进行中文语音转写，最后合并完整文本并返回分段结果。"""
    segments = []
    full_text = []
    for idx, audio_path in enumerate(audio_paths):
        audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("utf-8")
        audio_format = audio_path.suffix.lower().lstrip(".") or "mp3"
        mime_type = "audio/mpeg" if audio_format == "mp3" else f"audio/{audio_format}"
        audio_data_url = f"data:{mime_type};base64,{audio_b64}"
        result = client.chat.completions.create(
            model=ASR_TRANSCRIBE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "请将音频完整转写为中文文本。只输出转写内容，不要解释。",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_data_url,
                            },
                        },
                    ],
                }
            ],
        )
        text = (result.choices[0].message.content or "").strip()
        lower_text = text.lstrip().lower()
        if lower_text.startswith("<!doctype html") or lower_text.startswith("<html"):
            raise RuntimeError(
                "transcription endpoint returned an HTML page instead of text. "
                "Check DASHSCOPE_BASE_URL; it should be the DashScope compatible-mode /v1 endpoint."
            )
        full_text.append(text)
        segments.append({"chunk_index": idx, "start_sec": None, "end_sec": None, "text": text})
    return "\n".join(t for t in full_text if t).strip(), segments


def load_existing(jsonl_path: Path):
    """从历史 transcripts.jsonl 文件中读取已成功处理的视频记录，并按文件 SHA-256 建立索引，用于断点续跑和跳过重复文件。"""
    done = {}
    if not jsonl_path.exists():
        return done
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") == "success" and row.get("file_sha256"):
                done[row["file_sha256"]] = row
    return done


def append_jsonl(path: Path, row):
    """将单条转写结果以 JSON Lines 格式追加写入文件，便于任务中途失败后仍保留已完成结果。"""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def preview_text(text: str, max_chars=220):
    """压缩文本中的多余空白并截取指定长度，生成控制台预览内容，避免打印过长的转写全文。"""
    compact = " ".join((text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def write_csv(csv_path: Path, rows):
    """将当前批次的视频处理结果写入 CSV 汇总表，只保留适合表格查看的核心字段。"""
    fields = [
        "video_id",
        "file_name",
        "source_path",
        "file_sha256",
        "file_size",
        "duration_sec",
        "status",
        "transcript_text",
        "error",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def iter_videos(source_dir: Path):
    """递归扫描源目录，筛选出支持的视频格式文件，并按路径排序后返回。"""
    return sorted(
        p for p in source_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )


def process_video(client: OpenAI, ffmpeg_path: str, video_path: Path, output_dir: Path, index: int):
    """处理单个视频文件：计算哈希、读取元信息、提取/切分音频、调用 ASR 转写，并保存 txt 与 json 明细结果。"""
    file_hash = sha256_file(video_path)
    video_id = video_path.stem
    meta = run_ffprobe(ffmpeg_path, video_path)
    duration = None
    try:
        duration = float((meta.get("format") or {}).get("duration"))
    except Exception:
        duration = None

    with tempfile.TemporaryDirectory(prefix="video_transcribe_") as tmp:
        work_dir = Path(tmp)
        audio_path = extract_audio(ffmpeg_path, video_path, work_dir)
        audio_parts = split_audio_if_needed(ffmpeg_path, audio_path, work_dir)
        transcript_text, segments = transcribe_audio(client, audio_parts)

    row = {
        "video_id": video_id,
        "index": index,
        "source_path": str(video_path),
        "file_name": video_path.name,
        "file_sha256": file_hash,
        "file_size": video_path.stat().st_size,
        "duration_sec": duration,
        "transcribe_model": ASR_TRANSCRIBE_MODEL,
        "base_url": ASR_BASE_URL,
        "language": "zh",
        "transcript_text": transcript_text,
        "segments": segments,
        "status": "success",
        "error": None,
        "created_at": now_iso(),
    }
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in video_id)[:180]
    (output_dir / "texts").mkdir(parents=True, exist_ok=True)
    (output_dir / "items").mkdir(parents=True, exist_ok=True)
    (output_dir / "texts" / f"{safe_name}.txt").write_text(transcript_text, encoding="utf-8")
    (output_dir / "items" / f"{safe_name}.json").write_text(
        json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return row


def main():
    """视频批量转写流程入口：读取配置、初始化输出目录和 ASR 客户端，遍历视频文件，跳过已完成项，保存 JSONL、CSV 和 manifest 汇总文件。"""
    source_dir = Path(os.getenv("VIDEO_SOURCE_DIR", str(DEFAULT_SOURCE_DIR)))
    output_dir = Path(os.getenv("TRANSCRIPT_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    limit = int(os.getenv("TRANSCRIBE_LIMIT", "0"))
    api_key = ASR_API_KEY
    if not api_key:
        raise RuntimeError("请设置环境变量 ASR_API_KEY。")

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "transcripts.jsonl"
    csv_path = output_dir / "transcripts.csv"
    manifest_path = output_dir / "manifest.json"

    videos = iter_videos(source_dir)
    if limit > 0:
        videos = videos[:limit]
    existing = load_existing(jsonl_path)
    ffmpeg_path = get_ffmpeg_path()
    client = OpenAI(api_key=api_key, base_url=ASR_BASE_URL)

    rows = []
    started = now_iso()
    for idx, video_path in enumerate(videos, 1):
        file_hash = sha256_file(video_path)
        if file_hash in existing:
            row = dict(existing[file_hash])
            row["status"] = "skipped_existing"
            rows.append(row)
            print(f"[{idx}/{len(videos)}] skipped {video_path.name}", flush=True)
            continue
        print(f"[{idx}/{len(videos)}] transcribing {video_path.name}", flush=True)
        try:
            row = process_video(client, ffmpeg_path, video_path, output_dir, idx)
            print(
                f"[preview] {video_path.name}\n"
                f"{preview_text(row.get('transcript_text', ''))}\n",
                flush=True,
            )
        except Exception as exc:
            row = {
                "video_id": video_path.stem,
                "index": idx,
                "source_path": str(video_path),
                "file_name": video_path.name,
                "file_sha256": file_hash,
                "file_size": video_path.stat().st_size,
                "duration_sec": None,
                "transcribe_model": ASR_TRANSCRIBE_MODEL,
                "base_url": ASR_BASE_URL,
                "language": "zh",
                "transcript_text": "",
                "segments": [],
                "status": "error",
                "error": str(exc),
                "created_at": now_iso(),
            }
        rows.append(row)
        append_jsonl(jsonl_path, row)
        write_csv(csv_path, rows)
        print(
            f"[saved] status={row.get('status')} "
            f"csv={csv_path} jsonl={jsonl_path}",
            flush=True,
        )
        time.sleep(float(os.getenv("TRANSCRIBE_SLEEP_SEC", "0.2")))

    manifest = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "started_at": started,
        "finished_at": now_iso(),
        "video_count": len(videos),
        "success_count": sum(1 for r in rows if r.get("status") in {"success", "skipped_existing"}),
        "error_count": sum(1 for r in rows if r.get("status") == "error"),
        "asr_base_url": ASR_BASE_URL,
        "transcribe_model": ASR_TRANSCRIBE_MODEL,
        "ffmpeg_path": ffmpeg_path,
        "max_audio_mb": MAX_AUDIO_MB,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Batch transcription for KINYO Project audio using OpenAI Whisper.

Default behavior:
- Input:   Processed_Data/K7VideoProcessed/audio_full
- Output:  Processed_Data/K7VideoProcessed/transcripts
- Model:   medium
- Writes one UTF-8 text file per audio.

Run (PowerShell):
  python transcribe_whisper_batch.py --model medium --language zh

Notes:
- Requires: openai-whisper, torch, and ffmpeg available on PATH.
"""

from __future__ import annotations
import argparse
import csv
import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm"}

def _check_ffmpeg() -> None:
    try:
        completed = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "未找到 ffmpeg：Whisper 解码音频需要 ffmpeg。\n"
            "请先安装 ffmpeg 并把 ffmpeg 加入 PATH，然后重试。"
        ) from exc

    if completed.returncode != 0:
        raise RuntimeError(
            "ffmpeg 无法正常运行（返回码非 0）。\n"
            f"stdout: {completed.stdout[:300]}\n"
            f"stderr: {completed.stderr[:300]}"
        )


def _iter_audio_files(input_dir: Path) -> Iterable[Path]:
    for path in sorted(input_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
            yield path


def _safe_stem(path: Path) -> str:
    # Keep original stem; just guard against accidental trailing dots/spaces
    stem = path.stem.strip().rstrip(".")
    return stem if stem else "audio"


def _transcribe_one(
    *,
    model,
    audio_path: Path,
    language: str | None,
    task: str,
    fp16: bool,
) -> dict:
    return model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        fp16=fp16,
        verbose=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch transcribe audio with Whisper")
    parser.add_argument(
        "--input", # 音频输入目录
        type=Path,
        default=Path("Processed_Data") / "K7VideoProcessed" / "audio_full",
        help="Input directory containing audio files",
    )
    parser.add_argument(
        "--output", # 转录文本输出目录
        type=Path,
        default=Path("Processed_Data") / "K7VideoProcessed" / "transcripts",
        help="Output directory to write transcripts",
    )
    parser.add_argument("--model", type=str, default="medium", help="Whisper model name")
    parser.add_argument(
        "--language", # Whisper 语言代码，或 "auto" 以禁用强制语言（默认 zh）。如果音频包含多种语言，建议使用 "auto"。
        type=str,
        default="zh",
        help="Language code (e.g., zh, en). Use 'auto' to disable forcing language.",
    )
    parser.add_argument(
        "--task", # Whisper 任务类型：transcribe（保持原语言）或 translate（翻译成英文）
        type=str,
        default="transcribe",
        choices=["transcribe", "translate"],
        help="transcribe: keep language; translate: translate to English",
    )
    parser.add_argument(
        "--overwrite", # 是否覆盖已存在的转录文本文件
        action="store_true",
        help="Overwrite existing transcript files",
    )
    parser.add_argument(
        "--also-json", # 是否同时写出包含分段信息的 JSON 文件，供后续分析使用
        action="store_true",
        help="Also write a JSON file with segments per audio",
    )

    args = parser.parse_args()

    input_dir: Path = args.input # 音频输入目录
    output_dir: Path = args.output # 转录文本输出目录
    model_name: str = args.model # Whisper 模型名称
    language_arg: str = args.language # 语言代码，或 "auto" 以禁用强制语言
    task: str = args.task # 任务类型：transcribe（保持原语言）或 translate（翻译成英文）

    language: str | None
    if language_arg.lower() == "auto":
        language = None
    else:
        language = language_arg

    if not input_dir.exists():
        print(f"ERROR: input dir not found: {input_dir}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    _check_ffmpeg()

    try:
        import torch  # type: ignore
    except Exception as exc:
        raise RuntimeError("未安装 torch(Whisper 依赖）。请先安装后重试。") from exc

    try:
        import whisper  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "导入 whisper 失败：请确认已安装 openai-whisper,且当前 python 环境一致。\n"
            "建议: pip show openai-whisper"
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # fp16 only works on CUDA
    fp16 = device == "cuda"

    print(f"Whisper model: {model_name}")
    print(f"Device: {device}")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")

    model = whisper.load_model(model_name, device=device)

    audio_files = list(_iter_audio_files(input_dir))
    if not audio_files:
        print("No audio files found.")
        return 0

    manifest_path = output_dir / "whisper_manifest.csv"
    started_at = _dt.datetime.now().isoformat(timespec="seconds")

    # Append-safe manifest: write header if new file
    write_header = not manifest_path.exists()

    processed = 0
    skipped = 0
    failed = 0

    with open(manifest_path, "a", newline="", encoding="utf-8-sig") as mf:
        writer = csv.DictWriter(
            mf,
            fieldnames=[
                "started_at",
                "model",
                "device",
                "audio_path",
                "transcript_txt",
                "transcript_json",
                "language",
                "task",
                "status",
                "error",
                "text_len",
            ],
        )
        if write_header:
            writer.writeheader()

        for audio_path in audio_files:
            stem = _safe_stem(audio_path)
            out_txt = output_dir / f"{stem}.txt"
            out_json = output_dir / f"{stem}.json"

            if out_txt.exists() and not args.overwrite:
                skipped += 1
                writer.writerow(
                    {
                        "started_at": started_at,
                        "model": model_name,
                        "device": device,
                        "audio_path": str(audio_path),
                        "transcript_txt": str(out_txt),
                        "transcript_json": str(out_json) if args.also_json else "",
                        "language": language or "auto",
                        "task": task,
                        "status": "skipped",
                        "error": "",
                        "text_len": "",
                    }
                )
                continue

            try:
                result = _transcribe_one(
                    model=model,
                    audio_path=audio_path,
                    language=language,
                    task=task,
                    fp16=fp16,
                )

                text = (result.get("text") or "").strip()
                out_txt.write_text(text + "\n", encoding="utf-8-sig")

                if args.also_json:
                    # Keep full result for later alignment/segment analysis
                    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8-sig")

                processed += 1
                writer.writerow(
                    {
                        "started_at": started_at,
                        "model": model_name,
                        "device": device,
                        "audio_path": str(audio_path),
                        "transcript_txt": str(out_txt),
                        "transcript_json": str(out_json) if args.also_json else "",
                        "language": language or "auto",
                        "task": task,
                        "status": "ok",
                        "error": "",
                        "text_len": len(text),
                    }
                )
                mf.flush()

            except Exception as exc:
                failed += 1
                writer.writerow(
                    {
                        "started_at": started_at,
                        "model": model_name,
                        "device": device,
                        "audio_path": str(audio_path),
                        "transcript_txt": str(out_txt),
                        "transcript_json": str(out_json) if args.also_json else "",
                        "language": language or "auto",
                        "task": task,
                        "status": "failed",
                        "error": repr(exc),
                        "text_len": "",
                    }
                )
                mf.flush()

                print(f"FAILED: {audio_path}\n  {exc}", file=sys.stderr)

    print(f"Done. ok={processed}, skipped={skipped}, failed={failed}")
    print(f"Manifest: {manifest_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

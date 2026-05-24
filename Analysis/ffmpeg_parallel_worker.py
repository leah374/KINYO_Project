from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    # NaN check (works for float('nan') and numpy.nan)
    try:
        return value != value  # noqa: PLR0124
    except Exception:
        return False


def _sanitize_filename(name: str, max_len: int = 180) -> str:
    name = str(name)
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:max_len] if len(name) > max_len else name


def _pick_first_existing(row_dict: dict, cols: list[str]) -> str | None:
    for col in cols:
        if col in row_dict and not _is_missing(row_dict[col]):
            value = str(row_dict[col]).strip()
            if value:
                return value
    return None


def _build_base_name(row_dict: dict, idx: int) -> str:
    material_id = _pick_first_existing(row_dict, ["素材ID", "material_id", "id"])
    material_name = _pick_first_existing(
        row_dict,
        ["素材名称", "material_name", "name", "video_file", "视频文件"],
    )
    base = "_".join([x for x in [material_id, material_name] if x]) or f"row_{idx:04d}"
    return _sanitize_filename(base)


def ffmpeg_process_one(idx: int, row_dict: dict, video_col: str, cfg: dict) -> list[dict]:
    """Process one row.

    Returns a list of result dicts (video_full, clip15s, audio_full).
    This function must live in an importable .py module for Windows multiprocessing.
    """

    raw_path = row_dict.get(video_col)
    if _is_missing(raw_path):
        return [{"idx": int(idx), "status": "missing_path"}]

    in_path = Path(str(raw_path))
    if not in_path.is_absolute():
        in_path = (Path(cfg.get("CWD", Path.cwd())) / in_path).resolve()

    if not in_path.exists():
        return [{"idx": int(idx), "input": str(raw_path), "status": "missing_file"}]

    base = _build_base_name(row_dict, int(idx))

    video_full_dir = Path(cfg["VIDEO_FULL_DIR"])
    video_15s_dir = Path(cfg["VIDEO_15S_DIR"])
    audio_full_dir = Path(cfg["AUDIO_FULL_DIR"])

    full_out = video_full_dir / f"{base}_full.mp4"
    clip_out = video_15s_dir / f"{base}_15s.mp4"
    audio_out = audio_full_dir / f"{base}.m4a"

    def _run(cmd: list[str]) -> None:
        if cfg.get("DRY_RUN", False):
            return
        subprocess.run(cmd, check=True)

    results: list[dict] = []

    # --- full video ---
    if cfg.get("COMPRESS_FULL_VIDEO", True):
        full_cmd = [
            cfg["FFMPEG"],
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(in_path),
        ]
        full_scale = cfg.get("FULL_SCALE")
        if full_scale:
            full_cmd += ["-vf", f"scale={full_scale}"]
        full_cmd += [
            "-c:v",
            "libx264",
            "-preset",
            cfg["FULL_PRESET"],
            "-crf",
            str(cfg["FULL_CRF"]),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            cfg["FULL_AUDIO_BITRATE"],
            "-movflags",
            "+faststart",
            str(full_out),
        ]

        try:
            _run(full_cmd)
            results.append(
                {
                    "idx": int(idx),
                    "input": str(in_path),
                    "output": str(full_out),
                    "kind": "video_full",
                    "status": "ok",
                    "method": "transcode",
                }
            )
        except Exception as e:
            results.append(
                {
                    "idx": int(idx),
                    "input": str(in_path),
                    "output": str(full_out),
                    "kind": "video_full",
                    "status": "error",
                    "method": "transcode",
                    "error": repr(e),
                }
            )
    else:
        try:
            if not cfg.get("DRY_RUN", False):
                shutil.copy2(str(in_path), str(full_out))
            results.append(
                {
                    "idx": int(idx),
                    "input": str(in_path),
                    "output": str(full_out),
                    "kind": "video_full",
                    "status": "ok",
                    "method": "copy",
                }
            )
        except Exception as e:
            results.append(
                {
                    "idx": int(idx),
                    "input": str(in_path),
                    "output": str(full_out),
                    "kind": "video_full",
                    "status": "error",
                    "method": "copy",
                    "error": repr(e),
                }
            )

    # --- 15s clip ---
    clip_cmd = [
        cfg["FFMPEG"],
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "0",
        "-i",
        str(in_path),
        "-t",
        str(cfg["CLIP_SECONDS"]),
    ]
    scale = cfg.get("SCALE")
    if scale:
        clip_cmd += ["-vf", f"scale={scale}"]
    clip_cmd += [
        "-c:v",
        "libx264",
        "-preset",
        cfg["PRESET"],
        "-crf",
        str(cfg["CRF"]),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        cfg["AUDIO_BITRATE"],
        "-movflags",
        "+faststart",
        str(clip_out),
    ]

    try:
        _run(clip_cmd)
        results.append(
            {
                "idx": int(idx),
                "input": str(in_path),
                "output": str(clip_out),
                "kind": "clip15s",
                "status": "ok",
            }
        )
    except Exception as e:
        results.append(
            {
                "idx": int(idx),
                "input": str(in_path),
                "output": str(clip_out),
                "kind": "clip15s",
                "status": "error",
                "error": repr(e),
            }
        )

    # --- full audio ---
    audio_cmd = [
        cfg["FFMPEG"],
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(in_path),
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        cfg["AUDIO_FULL_BITRATE"],
        str(audio_out),
    ]

    try:
        _run(audio_cmd)
        results.append(
            {
                "idx": int(idx),
                "input": str(in_path),
                "output": str(audio_out),
                "kind": "audio_full",
                "status": "ok",
            }
        )
    except Exception as e:
        results.append(
            {
                "idx": int(idx),
                "input": str(in_path),
                "output": str(audio_out),
                "kind": "audio_full",
                "status": "error",
                "error": repr(e),
            }
        )

    return results

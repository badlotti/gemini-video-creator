"""Combine generated scene videos, narration, and BGM into a final video using ffmpeg."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _get_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _write_concat_list(paths: list[Path], list_file: Path) -> None:
    with open(list_file, "w") as f:
        for p in paths:
            # ffmpeg concat demuxer requires forward slashes on all platforms
            f.write(f"file '{p.resolve().as_posix()}'\n")


def concat_videos(video_paths: list[Path], out_path: Path) -> bool:
    """Concatenate scene videos (re-encoded for consistent codec/params)."""
    if not video_paths:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "videos.txt"
        _write_concat_list(video_paths, list_file)
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    return True


def concat_audios(audio_paths: list[Path], out_path: Path) -> bool:
    """Concatenate narration WAV clips in order into a single track."""
    valid = [p for p in audio_paths if p and p.exists()]
    if not valid:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "audios.txt"
        _write_concat_list(valid, list_file)
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:a", "pcm_s16le", str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    return True


def mix_with_bgm(narration_path: Path | None, bgm_path: Path | None, duration: float, out_path: Path) -> Path | None:
    """Loop/trim BGM to `duration` and mix it with narration (if any) into out_path."""
    if not bgm_path and not narration_path:
        return None

    if bgm_path and narration_path:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-i", str(narration_path),
            "-filter_complex",
            f"[0:a]atrim=0:{duration},volume=0.25[bgm];"
            f"[1:a]apad[narr];"
            "[narr][bgm]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map", "[aout]", "-t", str(duration), str(out_path),
        ]
    elif bgm_path:
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(bgm_path),
            "-t", str(duration), str(out_path),
        ]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(narration_path), "-t", str(duration), str(out_path)]

    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def mux_video_audio(video_path: Path, audio_path: Path | None, out_path: Path) -> Path:
    if audio_path and audio_path.exists():
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_path),
        ]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(video_path), "-c", "copy", str(out_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def build_final_video(
    scene_videos: list[Path],
    narration_clips: list[Path],
    bgm_path: Path | None,
    work_dir: Path,
    out_path: Path,
) -> Path | None:
    """High-level helper that combines everything into a final mp4 at out_path."""
    if not _ffmpeg_available():
        print("  [警告] ffmpeg/ffprobe が見つからないため、結合をスキップします")
        return None

    scene_videos = [p for p in scene_videos if p and p.exists()]
    if not scene_videos:
        print("  [警告] 結合可能な動画がありません")
        return None

    video_combined = work_dir / "_video_combined.mp4"
    concat_videos(scene_videos, video_combined)
    duration = _get_duration(video_combined)

    narration_combined = work_dir / "_narration_combined.wav"
    has_narration = concat_audios(narration_clips, narration_combined)

    audio_mix = work_dir / "_audio_mix.wav"
    mixed = mix_with_bgm(
        narration_combined if has_narration else None,
        bgm_path if bgm_path and bgm_path.exists() else None,
        duration,
        audio_mix,
    )

    return mux_video_audio(video_combined, mixed, out_path)

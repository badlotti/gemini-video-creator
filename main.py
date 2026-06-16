#!/usr/bin/env python3
"""Gemini Video Creator
====================

1つのプロンプトから、構成・キャラクター・動画(Veo)・音楽(Lyria)・音声(Gemini TTS)を
一括生成し、ffmpegで結合して1本の動画ファイルを作成するCLIツール。

事前準備:
  - Google Cloud プロジェクトでVertex AI APIを有効化
  - `gcloud auth application-default login` で認証
  - 必要モデル(Veo, Lyria, Imagen)へのアクセス権
  - ffmpeg のインストール (結合をスキップしない場合)

使い方:
  python main.py "猫の探偵が街の事件を解決するショートアニメ" \\
      --project YOUR_GCP_PROJECT --location us-central1
"""

import argparse
import json
import re
import sys
from pathlib import Path

from google import genai

from src.combine import build_final_video
from src.image_gen import generate_character_image
from src.music_gen import generate_bgm
from src.plan_generator import generate_plan
from src.schema import VideoPlan
from src.video_gen import generate_scene_video
from src.voice_gen import generate_voice_line


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_")
    return text[:40] or "video"


def write_plan_summary(plan: VideoPlan, out_dir: Path) -> None:
    (out_dir / "plan.json").write_text(plan.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

    lines = [f"# {plan.title}", "", f"## あらすじ", plan.synopsis, "", "## キャラクター"]
    for c in plan.characters:
        lines += [
            f"### {c.name}",
            f"- 性格: {c.personality}",
            f"- 声: {c.voice_name} ({c.voice_style})",
            f"- Imagen用プロンプト: `{c.appearance_prompt}`",
            "",
        ]

    lines += ["## BGM", f"- 雰囲気: {plan.music.mood}", f"- Lyria用プロンプト: `{plan.music.bgm_prompt}`", ""]

    lines += ["## シーン"]
    for s in plan.scenes:
        lines += [
            f"### シーン{s.index}: {s.title} ({s.duration_seconds}秒)",
            s.description,
            "",
            f"Veo用プロンプト: `{s.veo_prompt}`",
            "",
        ]
        if s.dialogue:
            lines.append("セリフ:")
            for d in s.dialogue:
                lines.append(f"- **{d.character}**: {d.text}")
        lines.append("")

    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", help="動画の構成案を生成するための元になるプロンプト")
    parser.add_argument("--project", help="GCPプロジェクトID (Vertex AI用)", required=True)
    parser.add_argument("--location", default="us-central1", help="Vertex AIのリージョン")
    parser.add_argument("--output", default="./output", help="出力先ディレクトリ")
    parser.add_argument("--gcs-bucket", help="Veoの出力に使うGCSバケット (gs://bucket/path)")

    parser.add_argument("--plan-model", default="gemini-2.5-pro")
    parser.add_argument("--image-model", default="imagen-4.0-generate-001")
    parser.add_argument("--video-model", default="veo-2.0-generate-001")
    parser.add_argument("--music-model", default="lyria-002")
    parser.add_argument("--tts-model", default="gemini-2.5-flash-preview-tts")
    parser.add_argument("--aspect-ratio", default="9:16", help="Veo動画のアスペクト比")

    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--skip-music", action="store_true")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-combine", action="store_true")
    parser.add_argument("--plan-only", action="store_true", help="構成案の生成のみ行う")
    parser.add_argument("--scenes", type=str, default=None,
                        help="生成するシーン番号をカンマ区切りで指定 例: --scenes 1,2")

    args = parser.parse_args()

    client = genai.Client(vertexai=True, project=args.project, location=args.location)

    print("== 1/6 構成案を生成中 ==")
    plan = generate_plan(client, args.prompt, model=args.plan_model)

    out_dir = Path(args.output) / slugify(plan.title)
    (out_dir / "characters").mkdir(parents=True, exist_ok=True)
    (out_dir / "scenes").mkdir(parents=True, exist_ok=True)
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)
    (out_dir / "music").mkdir(parents=True, exist_ok=True)

    write_plan_summary(plan, out_dir)
    print(f"  -> {out_dir}/plan.json, README.md を出力しました")

    if args.plan_only:
        return 0

    # --- 2. キャラクター画像 (Imagen) ---
    if not args.skip_images:
        print("== 2/6 キャラクター画像を生成中 (Imagen) ==")
        for c in plan.characters:
            out_path = out_dir / "characters" / f"{slugify(c.name)}.png"
            print(f"  - {c.name}")
            generate_character_image(client, c.appearance_prompt, out_path, model=args.image_model)
    else:
        print("== 2/6 キャラクター画像生成をスキップ ==")

    # --- 3. シーン動画 (Veo) ---
    target_scenes = None
    if args.scenes:
        target_scenes = {int(n.strip()) for n in args.scenes.split(",")}

    scene_video_paths: list[Path] = []
    if not args.skip_video:
        print("== 3/6 シーン動画を生成中 (Veo) ==")
        for s in plan.scenes:
            if target_scenes and s.index not in target_scenes:
                existing = out_dir / "scenes" / f"scene_{s.index:02d}.mp4"
                if existing.exists():
                    scene_video_paths.append(existing)
                continue
            out_path = out_dir / "scenes" / f"scene_{s.index:02d}.mp4"
            print(f"  - シーン{s.index}: {s.title}")
            result = generate_scene_video(
                client,
                s.veo_prompt,
                s.duration_seconds,
                out_path,
                model=args.video_model,
                output_gcs_uri=args.gcs_bucket,
                aspect_ratio=args.aspect_ratio,
            )
            if result:
                scene_video_paths.append(result)
    else:
        print("== 3/6 動画生成をスキップ ==")

    # --- 4. BGM (Lyria) ---
    bgm_path = out_dir / "music" / "bgm.wav"
    if not args.skip_music:
        print("== 4/6 BGMを生成中 (Lyria) ==")
        result = generate_bgm(args.project, args.location, plan.music.bgm_prompt, bgm_path, model=args.music_model)
        if not result:
            bgm_path = None
    else:
        print("== 4/6 BGM生成をスキップ ==")
        bgm_path = None

    # --- 5. セリフ/ナレーション (Gemini TTS) ---
    narration_clips: list[Path] = []
    if not args.skip_voice:
        print("== 5/6 セリフ音声を生成中 (Gemini TTS) ==")
        voice_map = {c.name: c for c in plan.characters}
        clip_index = 0
        for s in plan.scenes:
            for d in s.dialogue:
                clip_index += 1
                char = voice_map.get(d.character)
                voice_name = char.voice_name if char else "Kore"
                voice_style = char.voice_style if char else ""
                out_path = out_dir / "audio" / f"line_{clip_index:03d}_{slugify(d.character)}.wav"
                print(f"  - シーン{s.index} {d.character}: {d.text[:30]}")
                result = generate_voice_line(client, d.text, voice_name, voice_style, out_path, model=args.tts_model)
                if result:
                    narration_clips.append(result)
    else:
        print("== 5/6 音声生成をスキップ ==")

    # --- 6. 結合 ---
    if not args.skip_combine:
        print("== 6/6 動画・音楽・音声を結合中 (ffmpeg) ==")
        final_path = out_dir / "final.mp4"
        result = build_final_video(scene_video_paths, narration_clips, bgm_path, out_dir, final_path)
        if result:
            print(f"  -> 完成: {result}")
    else:
        print("== 6/6 結合をスキップ ==")

    print(f"\n全ての出力は {out_dir} に保存されました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

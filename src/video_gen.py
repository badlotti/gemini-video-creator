"""Generate scene videos using Veo on Vertex AI."""

import time
from pathlib import Path

from google import genai
from google.genai import types


def _download_gcs_uri(uri: str, out_path: Path) -> None:
    from google.cloud import storage

    assert uri.startswith("gs://")
    bucket_name, blob_path = uri[len("gs://") :].split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(str(out_path))


def generate_scene_video(
    client: genai.Client,
    prompt: str,
    duration_seconds: int,
    out_path: Path,
    model: str = "veo-2.0-generate-001",
    output_gcs_uri: str | None = None,
    poll_interval: int = 10,
    timeout: int = 600,
    aspect_ratio: str = "9:16",
) -> Path | None:
    """Generate a single scene video and save it to out_path (mp4).

    Returns the path on success, or None if generation failed (error is printed).
    """
    duration_seconds = 8 if duration_seconds >= 7 else 5

    config_kwargs = dict(
        aspect_ratio=aspect_ratio,
        duration_seconds=duration_seconds,
        number_of_videos=1,
    )
    if output_gcs_uri:
        config_kwargs["output_gcs_uri"] = output_gcs_uri

    try:
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_kwargs),
        )

        start = time.time()
        while not operation.done:
            if time.time() - start > timeout:
                print("  [警告] 動画生成がタイムアウトしました")
                return None
            time.sleep(poll_interval)
            operation = client.operations.get(operation)

        if operation.error:
            print(f"  [警告] 動画生成エラー: {operation.error}")
            return None

        videos = operation.response.generated_videos
        if not videos:
            print("  [警告] 動画が生成されませんでした")
            return None

        video = videos[0].video
        if getattr(video, "video_bytes", None):
            out_path.write_bytes(video.video_bytes)
        elif getattr(video, "uri", None):
            _download_gcs_uri(video.uri, out_path)
        else:
            print("  [警告] 生成された動画の取得方法が不明です")
            return None

        return out_path
    except Exception as exc:  # noqa: BLE001
        print(f"  [警告] 動画生成に失敗しました ({model}): {exc}")
        return None

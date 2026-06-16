"""Generate background music using Lyria on Vertex AI (REST predict endpoint).

The google-genai SDK does not yet wrap Lyria, so this calls the Vertex AI
predict endpoint directly using Application Default Credentials.
"""

import base64
from pathlib import Path

import google.auth
import google.auth.transport.requests
import requests

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def generate_bgm(
    project: str,
    location: str,
    prompt: str,
    out_path: Path,
    model: str = "lyria-002",
    negative_prompt: str | None = None,
    seed: int | None = None,
) -> Path | None:
    """Generate background music and save it as a WAV file at out_path.

    Returns the path on success, or None if generation failed (error is printed).
    """
    try:
        credentials, _ = google.auth.default(scopes=SCOPES)
        credentials.refresh(google.auth.transport.requests.Request())

        url = (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/"
            f"{project}/locations/{location}/publishers/google/models/{model}:predict"
        )

        instance: dict = {"prompt": prompt}
        if negative_prompt:
            instance["negative_prompt"] = negative_prompt
        if seed is not None:
            instance["seed"] = seed

        body = {"instances": [instance], "parameters": {"sample_count": 1}}

        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()

        predictions = data.get("predictions", [])
        if not predictions:
            print(f"  [警告] BGMが生成されませんでした: {data}")
            return None

        audio_b64 = predictions[0].get("bytesBase64Encoded")
        if not audio_b64:
            print(f"  [警告] BGMの音声データが見つかりません: {predictions[0]}")
            return None

        out_path.write_bytes(base64.b64decode(audio_b64))
        return out_path
    except Exception as exc:  # noqa: BLE001
        print(f"  [警告] BGM生成に失敗しました ({model}): {exc}")
        return None

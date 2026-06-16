"""Generate character reference images using Imagen on Vertex AI."""

from pathlib import Path

from google import genai
from google.genai import types


def generate_character_image(
    client: genai.Client,
    prompt: str,
    out_path: Path,
    model: str = "imagen-4.0-generate-001",
) -> Path | None:
    """Generate a single reference image for a character and save it to out_path.

    Returns the path on success, or None if generation failed (error is printed).
    """
    try:
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
            ),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  [警告] 画像生成に失敗しました ({model}): {exc}")
        return None

    if not response.generated_images:
        print("  [警告] 画像が生成されませんでした")
        return None

    image_bytes = response.generated_images[0].image.image_bytes
    out_path.write_bytes(image_bytes)
    return out_path

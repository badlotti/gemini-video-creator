"""Generate voice/narration audio using Gemini's native TTS."""

import wave
from pathlib import Path

from google import genai
from google.genai import types


def _save_pcm_as_wav(pcm_data: bytes, out_path: Path, channels=1, rate=24000, sample_width=2) -> None:
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def generate_voice_line(
    client: genai.Client,
    text: str,
    voice_name: str,
    voice_style: str,
    out_path: Path,
    model: str = "gemini-2.5-flash-preview-tts",
) -> Path | None:
    """Generate a single line of speech and save it as a WAV file at out_path.

    Returns the path on success, or None if generation failed (error is printed).
    """
    try:
        styled_text = f"{voice_style}\n\n{text}" if voice_style else text

        response = client.models.generate_content(
            model=model,
            contents=styled_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )

        part = response.candidates[0].content.parts[0]
        pcm_data = part.inline_data.data
        _save_pcm_as_wav(pcm_data, out_path)
        return out_path
    except Exception as exc:  # noqa: BLE001
        print(f"  [警告] 音声生成に失敗しました ({model}): {exc}")
        return None

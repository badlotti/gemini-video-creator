"""Generate a structured video plan (story, characters, scenes, music) using Gemini."""

from google import genai
from google.genai import types

from .schema import VideoPlan

SYSTEM_INSTRUCTION = """\
あなたは動画制作のプロデューサーです。
ユーザーから渡された1つのテーマ・要望(プロンプト)をもとに、
ショート動画(合計30秒〜90秒程度)の企画を作成してください。

出力には以下を必ず含めてください:
- title, synopsis
- characters: 登場キャラクターの設定。appearance_promptは英語でImagen用の画像生成プロンプトとして
  そのまま使えるレベルまで具体的に書くこと(同一人物として描けるよう、容姿の特徴を一貫させること)。
- music: 動画全体のBGMについて、Lyria(音楽生成AI)向けの英語プロンプトをbgm_promptに書くこと。
- scenes: 3〜6個程度のシーンに分割すること。各シーンのveo_promptは英語で、
  Veo(動画生成AI)向けにそのまま使えるレベルまで具体的に書くこと
  (主体・動き・カメラワーク・画風・ライティング・雰囲気を含める)。
  キャラクターが登場するシーンでは、appearance_promptと一致する見た目になるよう
  veo_promptにも容姿の特徴を簡潔に含めること。
  各シーンのduration_secondsは5または8とすること。
  dialogueには、そのシーンで話すキャラクターのセリフ・ナレーションを順番に入れること
  (発話者がいないシーンは空配列でよい)。

すべて日本語で説明できる部分は日本語、AI生成モデル向けのプロンプト
(appearance_prompt, veo_prompt, bgm_prompt)は英語で記述してください。
"""


def generate_plan(
    client: genai.Client,
    user_prompt: str,
    model: str = "gemini-2.5-pro",
) -> VideoPlan:
    """Call Gemini with a structured response schema to build a VideoPlan."""

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=VideoPlan,
            temperature=1.0,
        ),
    )

    plan = response.parsed
    if plan is None:
        raise RuntimeError(f"Gemini が構造化出力の生成に失敗しました: {response.text}")
    return plan

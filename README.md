# Gemini Video Creator

1つのプロンプトから、Gemini / Vertex AI を使って動画の企画〜素材〜完成動画までを
自動生成するPython CLIです。

## 生成される内容

1. **構成案** (Gemini): タイトル・あらすじ・キャラクター設定・シーン分割・台本
2. **キャラクター画像** (Imagen): 各キャラクターの見た目の参考画像
3. **シーン動画** (Veo): 各シーンの動画クリップ
4. **BGM** (Lyria): 動画全体のBGM
5. **セリフ・ナレーション音声** (Gemini TTS): キャラごとの声で読み上げ
6. **最終動画** (ffmpeg): 上記をすべて結合した `final.mp4`

## セットアップ

```bash
cd gemini-video-creator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud / Vertex AI の準備

```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT
gcloud services enable aiplatform.googleapis.com
```

以下のモデルへのアクセスが必要です(モデルによってはアロウリスト/プレビュー申請が必要です):

- `gemini-2.5-pro` (構成案生成)
- `imagen-4.0-generate-001` (キャラクター画像)
- `veo-2.0-generate-001` (動画生成)
- `lyria-002` (音楽生成)
- `gemini-2.5-flash-preview-tts` (音声生成)

### ffmpeg

最終結合には ffmpeg / ffprobe が必要です。

```bash
brew install ffmpeg
```

## 使い方

```bash
python main.py "猫の探偵が街の事件を解決するショートアニメ" \
  --project YOUR_GCP_PROJECT \
  --location us-central1
```

実行すると `./output/<タイトル>/` 以下に以下が生成されます:

```
output/<タイトル>/
├── plan.json          # 構成案(全プロンプトを含む)
├── README.md          # 構成案を見やすく整理したもの
├── characters/         # キャラクター画像 (Imagen)
├── scenes/             # シーン動画 (Veo)
├── audio/              # セリフ・ナレーション音声 (TTS)
├── music/              # BGM (Lyria)
└── final.mp4           # 結合済みの完成動画
```

## オプション

| オプション | 説明 |
|---|---|
| `--plan-only` | 構成案(plan.json/README.md)のみ生成し、メディア生成は行わない |
| `--skip-images` | キャラクター画像の生成をスキップ |
| `--skip-video` | シーン動画の生成をスキップ |
| `--skip-music` | BGMの生成をスキップ |
| `--skip-voice` | セリフ音声の生成をスキップ |
| `--skip-combine` | 最終結合(ffmpeg)をスキップ |
| `--gcs-bucket gs://BUCKET/PATH` | Veoの出力先GCSバケットを指定(プロジェクトによって必須) |
| `--aspect-ratio` | Veo動画のアスペクト比 (デフォルト `9:16`) |
| `--plan-model` / `--image-model` / `--video-model` / `--music-model` / `--tts-model` | 各ステップで使うモデル名を変更 |

## まずは構成案だけ試す

API課金が発生するメディア生成の前に、構成案のみを確認できます:

```bash
python main.py "猫の探偵が街の事件を解決するショートアニメ" \
  --project YOUR_GCP_PROJECT --plan-only
```

`output/<タイトル>/README.md` にVeo/Imagen/Lyria/TTS用の全プロンプトが
そのままコピーできる形で出力されます。

## 注意事項

- Veo/Lyria/Imagen は利用できるリージョンやアロウリストが限られている場合があります。
  各ステップは個別にエラーハンドリングされており、失敗した素材はスキップされ、
  他の素材生成と最終結合は続行されます。
- 生成コンテンツの利用については各モデルの利用規約・ガイドラインに従ってください。

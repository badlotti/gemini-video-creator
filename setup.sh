#!/usr/bin/env bash
# Gemini Video Creator - Mac/Linux セットアップスクリプト
# 実行方法: bash setup.sh

set -e

TOOLS_DIR="$HOME/.gemini-video-tools"
GCLOUD_DIR="$HOME/google-cloud-sdk"
LOCAL_BIN="$HOME/.local/bin"
ARCH=$(uname -m)
OS=$(uname -s)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo ""
echo -e "${CYAN}========================================"
echo -e "  Gemini Video Creator セットアップ"
echo -e "========================================${NC}"
echo ""

mkdir -p "$TOOLS_DIR" "$LOCAL_BIN"

# ── 1. Python 3.10+ ────────────────────────────────────────
echo -e "${YELLOW}[1/5] Python 3.10+ の確認...${NC}"

PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oE '3\.[0-9]+')
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "${minor:-0}" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            echo -e "  ${GREEN}OK: $("$cmd" --version)${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  Python 3.10以上が見つかりません。pyenvでインストールします..."
    if ! command -v pyenv &>/dev/null; then
        curl -fsSL https://pyenv.run | bash
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    fi
    pyenv install -s 3.13.5
    export PATH="$HOME/.pyenv/versions/3.13.5/bin:$PATH"
    PYTHON_CMD="python3.13"
    echo -e "  ${GREEN}Python 3.13 インストール完了${NC}"
fi

# ── 2. gcloud CLI ──────────────────────────────────────────
echo -e "${YELLOW}[2/5] gcloud CLI の確認...${NC}"

if command -v gcloud &>/dev/null; then
    echo -e "  ${GREEN}OK: $(gcloud --version 2>&1 | head -1)${NC}"
else
    if [ "$OS" = "Darwin" ]; then
        [ "$ARCH" = "arm64" ] && GCLOUD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz" \
                               || GCLOUD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz"
    else
        GCLOUD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz"
    fi
    echo "  ダウンロード中..."
    curl -fsSL "$GCLOUD_URL" -o /tmp/gcloud.tar.gz
    tar -xzf /tmp/gcloud.tar.gz -C "$HOME"
    rm /tmp/gcloud.tar.gz
    export PATH="$GCLOUD_DIR/bin:$PATH"
    export CLOUDSDK_PYTHON="$("$PYTHON_CMD" -c 'import sys; print(sys.executable)')"
    CLOUDSDK_CORE_DISABLE_PROMPTS=1 "$GCLOUD_DIR/install.sh" --quiet --usage-reporting=false --path-update=false 2>/dev/null || true
    echo -e "  ${GREEN}gcloud インストール完了${NC}"
fi

export CLOUDSDK_PYTHON="$("$PYTHON_CMD" -c 'import sys; print(sys.executable)')"

# ── 3. ffmpeg ──────────────────────────────────────────────
echo -e "${YELLOW}[3/5] ffmpeg の確認...${NC}"

if command -v ffmpeg &>/dev/null; then
    echo -e "  ${GREEN}OK: $(ffmpeg -version 2>&1 | head -1)${NC}"
else
    echo "  ダウンロード中..."
    if [ "$OS" = "Darwin" ]; then
        curl -fsSL "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip" -o /tmp/ffmpeg.zip
        curl -fsSL "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip" -o /tmp/ffprobe.zip
        unzip -o /tmp/ffmpeg.zip -d "$LOCAL_BIN" && unzip -o /tmp/ffprobe.zip -d "$LOCAL_BIN"
        rm /tmp/ffmpeg.zip /tmp/ffprobe.zip
    else
        curl -fsSL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" -o /tmp/ffmpeg.tar.xz
        tar -xJf /tmp/ffmpeg.tar.xz -C /tmp
        cp /tmp/ffmpeg-*-static/ffmpeg /tmp/ffmpeg-*-static/ffprobe "$LOCAL_BIN/"
        rm -rf /tmp/ffmpeg.tar.xz /tmp/ffmpeg-*-static
    fi
    chmod +x "$LOCAL_BIN/ffmpeg" "$LOCAL_BIN/ffprobe"
    export PATH="$LOCAL_BIN:$PATH"
    echo -e "  ${GREEN}ffmpeg インストール完了${NC}"
fi

# ── 4. Python 仮想環境 + パッケージ ───────────────────────
echo -e "${YELLOW}[4/5] Python 仮想環境を作成中...${NC}"

rm -rf .venv
"$PYTHON_CMD" -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo -e "  ${GREEN}仮想環境作成・パッケージインストール完了${NC}"

# ── 5. シェル設定の永続化 ─────────────────────────────────
echo -e "${YELLOW}[5/5] PATH を永続設定中...${NC}"

SHELL_RC="$HOME/.zprofile"
[ "${SHELL##*/}" = "bash" ] && SHELL_RC="$HOME/.bashrc"

PYENV_ROOT_DIR="$HOME/.pyenv"

{
    echo ""
    echo "# === Gemini Video Creator ==="
    echo "export PATH=\"$LOCAL_BIN:\$PATH\""
    echo "export PATH=\"$GCLOUD_DIR/bin:\$PATH\""
    echo "export CLOUDSDK_PYTHON=\"$CLOUDSDK_PYTHON\""
    if [ -d "$PYENV_ROOT_DIR" ]; then
        echo "export PYENV_ROOT=\"$PYENV_ROOT_DIR\""
        echo "export PATH=\"\$PYENV_ROOT/bin:\$PATH\""
        echo 'eval "$(pyenv init -)"'
    fi
} >> "$SHELL_RC"

echo -e "  ${GREEN}$SHELL_RC に設定を追加しました${NC}"

# ── 完了 ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}========================================"
echo -e "  セットアップ完了！"
echo -e "========================================${NC}"
echo ""
echo -e "${CYAN}次のステップ:${NC}"
echo ""
echo "1. Google Cloud 認証:"
echo "   gcloud auth application-default login"
echo ""
echo "2. 動作確認 (構成案のみ・課金なし):"
echo "   source .venv/bin/activate"
echo "   python main.py \"テーマ\" --project YOUR_PROJECT_ID --plan-only"
echo ""
echo "3. 本番実行:"
echo "   python main.py \"テーマ\" --project YOUR_PROJECT_ID"
echo ""

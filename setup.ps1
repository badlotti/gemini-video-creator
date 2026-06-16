# Gemini Video Creator - Windows セットアップスクリプト
# PowerShell 5.1以上で実行してください
# 実行方法: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$TOOLS_DIR = "$HOME\.gemini-video-tools"
$GCLOUD_DIR = "$TOOLS_DIR\google-cloud-sdk"
$FFMPEG_DIR = "$TOOLS_DIR\ffmpeg"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Gemini Video Creator セットアップ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

New-Item -ItemType Directory -Force -Path $TOOLS_DIR | Out-Null

# ── 1. Python 3.13 ──────────────────────────────────────────
Write-Host "[1/5] Python 3.13 の確認..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python3.13", "python3", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "3\.(1[0-9]|[2-9]\d)") {
            $pythonCmd = $cmd
            Write-Host "  OK: $ver ($cmd)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "  Python 3.10以上が見つかりません。インストールします..." -ForegroundColor Yellow
    $pyInstaller = "$TOOLS_DIR\python-installer.exe"
    Write-Host "  ダウンロード中..."
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.5/python-3.13.5-amd64.exe" `
        -OutFile $pyInstaller -UseBasicParsing
    Write-Host "  インストール中 (ユーザーフォルダへ、管理者権限不要)..."
    Start-Process -FilePath $pyInstaller -ArgumentList `
        "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait
    Remove-Item $pyInstaller -Force

    # PATH を再読み込み
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + $env:Path
    $pythonCmd = "python"
    Write-Host "  Python 3.13 インストール完了" -ForegroundColor Green
}

# ── 2. gcloud CLI ────────────────────────────────────────────
Write-Host "[2/5] gcloud CLI の確認..." -ForegroundColor Yellow

$gcloudCmd = "$GCLOUD_DIR\bin\gcloud.cmd"
if (Test-Path $gcloudCmd) {
    Write-Host "  OK: gcloud すでにインストール済み" -ForegroundColor Green
} else {
    Write-Host "  ダウンロード中 (約100MB)..."
    $gcloudZip = "$TOOLS_DIR\gcloud.zip"
    Invoke-WebRequest -Uri "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-windows-x86_64.zip" `
        -OutFile $gcloudZip -UseBasicParsing
    Write-Host "  展開中..."
    Expand-Archive -Path $gcloudZip -DestinationPath $TOOLS_DIR -Force
    Remove-Item $gcloudZip -Force
    Write-Host "  gcloud インストール完了" -ForegroundColor Green
}

$env:Path = "$GCLOUD_DIR\bin;" + $env:Path
$env:CLOUDSDK_PYTHON = & $pythonCmd -c "import sys; print(sys.executable)"

# ── 3. ffmpeg ────────────────────────────────────────────────
Write-Host "[3/5] ffmpeg の確認..." -ForegroundColor Yellow

$ffmpegExe = "$FFMPEG_DIR\ffmpeg.exe"
if (Test-Path $ffmpegExe) {
    Write-Host "  OK: ffmpeg すでにインストール済み" -ForegroundColor Green
} else {
    Write-Host "  ダウンロード中 (約90MB)..."
    $ffmpegZip = "$TOOLS_DIR\ffmpeg.zip"
    Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" `
        -OutFile $ffmpegZip -UseBasicParsing
    Write-Host "  展開中..."
    Expand-Archive -Path $ffmpegZip -DestinationPath "$TOOLS_DIR\_ffmpeg_tmp" -Force
    $extractedBin = Get-ChildItem "$TOOLS_DIR\_ffmpeg_tmp" -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    New-Item -ItemType Directory -Force -Path $FFMPEG_DIR | Out-Null
    Move-Item $extractedBin.FullName "$FFMPEG_DIR\ffmpeg.exe" -Force
    $extractedProbe = Get-ChildItem "$TOOLS_DIR\_ffmpeg_tmp" -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
    Move-Item $extractedProbe.FullName "$FFMPEG_DIR\ffprobe.exe" -Force
    Remove-Item "$TOOLS_DIR\_ffmpeg_tmp" -Recurse -Force
    Remove-Item $ffmpegZip -Force
    Write-Host "  ffmpeg インストール完了" -ForegroundColor Green
}

$env:Path = "$FFMPEG_DIR;" + $env:Path

# ── 4. Python 仮想環境 + パッケージ ─────────────────────────
Write-Host "[4/5] Python 仮想環境を作成中..." -ForegroundColor Yellow

if (Test-Path ".venv") {
    Remove-Item ".venv" -Recurse -Force
}
& $pythonCmd -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip -q
.\.venv\Scripts\pip.exe install -r requirements.txt -q
Write-Host "  仮想環境作成・パッケージインストール完了" -ForegroundColor Green

# ── 5. PATH をユーザー環境変数に永続化 ──────────────────────
Write-Host "[5/5] PATH を永続設定中..." -ForegroundColor Yellow

$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$newPaths = @("$GCLOUD_DIR\bin", $FFMPEG_DIR)
foreach ($p in $newPaths) {
    if ($userPath -notlike "*$p*") {
        $userPath = "$p;$userPath"
    }
}
[System.Environment]::SetEnvironmentVariable("Path", $userPath, "User")
[System.Environment]::SetEnvironmentVariable("CLOUDSDK_PYTHON", $env:CLOUDSDK_PYTHON, "User")

Write-Host "  PATH 設定完了" -ForegroundColor Green

# ── 完了メッセージ ────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  セットアップ完了！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Google Cloud 認証 (ブラウザが開きます):"
Write-Host "   gcloud auth application-default login" -ForegroundColor White
Write-Host ""
Write-Host "2. 動作確認 (構成案のみ、課金なし):"
Write-Host "   .venv\Scripts\python.exe main.py `"テーマ`" --project YOUR_PROJECT_ID --plan-only" -ForegroundColor White
Write-Host ""
Write-Host "3. 本番実行 (動画・音楽・音声すべて生成):"
Write-Host "   .venv\Scripts\python.exe main.py `"テーマ`" --project YOUR_PROJECT_ID" -ForegroundColor White
Write-Host ""

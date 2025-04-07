# 一般的な FastAPI の構成順は：
# 1. インポート
# 2. 設定系（APIの定義、CORSなど）
# 3. ユーティリティ関数（画像変換など）
# 4. エンドポイント一覧（ルート、履歴、画像処理など）

# === 1. 必要なモジュール ===
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
# 日時取得
from datetime import datetime
# HEICをJPEGに変換用
import pyheif
from PIL import Image
import io
from fastapi import UploadFile
import base64
import requests
# .envのAPIキーを読み込む用
from dotenv import load_dotenv
import os
load_dotenv()  # .env を読み込む

# === 2. FastAPIインスタンスとCORS設定 ===
app = FastAPI()

# CORSの設定（Reactからのリクエストを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # セキュリティ強化するならReactのURLだけにする
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 3. ユーティリティ関数 ===
# HEICをJPEGに変換する関数
def convert_heic_to_jpeg(file: bytes) -> bytes:
    heif_file = pyheif.read_heif(file)
    image = Image.frombytes(
        heif_file.mode, 
        heif_file.size, 
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


# === 4. エンドポイント一覧 ===
#トップページ
@app.get("/") 
def read_root():
    return {"message": "FastAPI へようこそ！"}

#履歴一覧をReactに送信
@app.get("/history") 
def read_history():
    try:
        with open("history.json", "r", encoding="utf-8") as f:
            lines = f.readlines()
            data = [json.loads(line) for line in lines]
            return data
    except FileNotFoundError:
        return []

#履歴を追加
@app.post("/history") 
async def save_history(request: Request):
    data = await request.json()  # JSON形式で受け取る
    print("📥 受け取ったデータ:", data)

    # 日時を追加
    data["timestamp"] = datetime.now().isoformat()

    # 保存するファイル
    with open("history.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

    return {"message": "履歴を保存しました！"}

## 画像アップロード（HEIC変換対応）
# 画像をアップロードして、文字を読み取るまでを全部やってくれる魔法の関数
@app.post("/upload-image")
async def upload_image(file: UploadFile):
    content = await file.read()

    # HEICならJPEGに変換
    if file.filename.lower().endswith(".heic"):
        content = convert_heic_to_jpeg(content)

    # バイナリ → base64へ変換
    base64_image = base64.b64encode(content).decode("utf-8")

    # GCVに送信
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    payload = {
        "requests": [
            {
                "image": {"content": base64_image},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    return result  # Reactに返す！

# 削除API
@app.delete("/history")
def clear_history():
    with open("history.json", "w", encoding="utf-8") as f:
        f.write("")  # 内容を空にする
    return {"message": "履歴を削除しました"}






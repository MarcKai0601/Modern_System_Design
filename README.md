# Modern System Design

透過實作學習系統設計概念的學習專案。每個題目都有獨立的 Python Package，包含完整的架構說明與可執行的 API 服務。

A hands-on learning project where each system design topic is implemented as a standalone Python package with a runnable API service.

---

## 目錄結構 / Directory Structure

```
Modern_System_Design/
├── main.py              # 啟動入口 / Project launcher
├── requirements.txt     # 依賴套件 / Dependencies
├── docs/
│   └── python-for-java-devs.md  # Python 語法對照文件（給 Java 開發者）
├── qr_code/             # 題目一：QR Code 產生器 / Topic 1: QR Code Generator
│   ├── __init__.py
│   ├── models.py        # 資料模型、常數、例外 / Data models, constants, exceptions
│   ├── storage.py       # 儲存層（模擬 Redis + PostgreSQL）/ Storage layer
│   ├── service.py       # 業務邏輯層 / Business logic layer
│   └── app.py           # FastAPI 路由 / FastAPI routes
└── openspec/            # 規格文件 / Spec-driven design artifacts
    └── changes/
        └── qr-code-generator/
            ├── proposal.md
            ├── design.md
            └── specs/
```

---

## 環境設定 / Setup

```bash
# 建立虛擬環境（已存在可略過）/ Create virtual environment (skip if exists)
python -m venv .venv

# 啟動虛擬環境 / Activate virtual environment
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

# 安裝依賴 / Install dependencies
pip install -r requirements.txt
```

---

## 執行方式 / Running

```bash
python main.py
```

啟動後開啟瀏覽器 / Then open your browser:

- **互動式 API 文件 / Interactive API docs** → http://localhost:8000/docs
- **自動產生的 OpenAPI schema** → http://localhost:8000/openapi.json

---

## API 說明 / API Reference

### QR Code Generator

| Method   | Path                                          | Status | 說明 / Description                        |
|----------|-----------------------------------------------|--------|-------------------------------------------|
| `POST`   | `/api/users/{user_id}/qr-codes?url=...`       | 201    | 產生 QR Code / Create QR code             |
| `GET`    | `/api/users/{user_id}/qr-codes`               | 200    | 列出所有 QR Code / List QR codes          |
| `GET`    | `/api/users/{user_id}/qr-codes/{qr_id}/view`  | 200    | **瀏覽器掃描頁面 / Scan page** (HTML)    |
| `GET`    | `/api/users/{user_id}/qr-codes/{qr_id}/image` | 200    | QR Code 圖片 / QR Code image (PNG)        |
| `DELETE` | `/api/users/{user_id}/qr-codes/{qr_id}`       | 204    | 刪除 QR Code / Delete QR code             |
| `GET`    | `/{qr_id}`                                    | 307    | 掃描後跳轉（熱路徑）/ Redirect on scan   |

**URL 規則 / URL rules：** ASCII 字元，最多 20 字元。

**快速測試 / Quick test：**

```bash
# 1. 產生 QR Code / Create QR code
curl -X POST "http://localhost:8000/api/users/alice/qr-codes?url=http://example.com"

# 2. 在瀏覽器開啟掃描頁面 / Open scan page in browser（將 {qr_id} 換成回傳的 ID）
open "http://localhost:8000/api/users/alice/qr-codes/{qr_id}/view"

# 3. 列出所有 QR Codes / List QR codes
curl http://localhost:8000/api/users/alice/qr-codes
```

---

## 系統設計概念 / System Design Concepts

### QR Code Generator

**規模目標 / Scale targets**

| 指標 | 目標 |
|------|------|
| 使用者數 / Users | 1 億 / 100 million |
| QR Code 總數 / QR codes | 10 億 / 1 billion |
| 跳轉延遲 / Redirect latency | < 100 ms |
| 可用性 / Availability | 24/7 |

**生產架構 / Production architecture**

```
Client
  │
  ▼
Load Balancer
  │
  ▼
API Servers（無狀態，水平擴展 / stateless, horizontally scalable）
  │
  ├──► Redis       ← 跳轉快取：qr_id → original_url（< 1 ms）
  │                   Redirect cache: qr_id → original_url
  │
  └──► PostgreSQL  ← 完整記錄的來源 / Source of truth for all records
```

**關鍵設計決策 / Key design decisions**

| 決策 | 原因 |
|------|------|
| Base62 ID（6 字元）| URL 安全、QR 友善；62⁶ = 568 億 >> 10 億目標 |
| 分離跳轉快取（Redis）與完整記錄（PostgreSQL）| 熱路徑只需 qr_id → url，Redis GET < 1 ms |
| 根路徑跳轉 URL `/{id}` | URL 越短 → QR 矩陣越小 → 越易掃描 |
| HTTP 307（非 301）| 瀏覽器每次都詢問伺服器，支援未來更改目標網址與流量統計 |
| 重複 URL → HTTP 409 | 強迫客戶端明確處理，避免靜默地回傳舊記錄 |

---

## 新增題目 / Adding New Topics

每個系統設計題目都是一個獨立的 Python Package。

Each system design topic is an independent Python package.

**建議結構 / Suggested structure：**

```
<topic_name>/
├── __init__.py
├── models.py    # 資料模型 / Data models
├── storage.py   # 儲存層 / Storage layer
├── service.py   # 業務邏輯 / Business logic
└── app.py       # FastAPI 路由 / FastAPI routes
```

新增後在 `main.py` 掛載新的 FastAPI app：

After adding, mount the new app in `main.py`:

```python
from fastapi import FastAPI
from qr_code.app import app as qr_app
from url_shortener.app import app as url_app  # 下一個題目 / next topic

root = FastAPI()
root.mount("/qr", qr_app)
root.mount("/url", url_app)
```

---

## 開發工作流程 / Development Workflow

本專案使用 [OpenSpec](https://openspec.dev) 進行規格驅動開發。

This project uses [OpenSpec](https://openspec.dev) for spec-driven development.

```
/opsx:propose   →   撰寫提案與設計文件 / Write proposal & design
/opsx:apply     →   實作待辦任務 / Implement pending tasks
/opsx:archive   →   封存已完成的變更 / Archive completed changes
```

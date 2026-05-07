## 為什麼（Why）

這是「Modern System Design」學習專案的第一個主題。我們透過實作一個 QR Code 產生服務，同時學習系統設計的核心概念（容量估算、高可用性、低延遲架構）以及 Python 語言的實作技巧。

## 目標（Goals）

- 實作一個可實際運行的 QR Code 產生 API，支援建立、查詢、刪除 QR Code 及掃描後重新導向。
- 透過程式碼中的設計說明，理解如何將系統設計概念（Redis cache、PostgreSQL 持久層、Base62 ID）對應到真實實作。
- 學習 Python 的 dataclass、型別提示、自訂例外階層、FastAPI 路由設計等慣用模式。

## 非目標（Non-Goals）

- 不實作真實的使用者驗證或 OAuth 流程（以 `user_id` query parameter 簡化）。
- 不部署到雲端或建立 Docker 容器（本地開發即可）。
- 不實作 QR Code 的到期機制或進階統計儀表板。

## 異動內容（What Changes）

- 新增 `qr_code_generator.py`：單一檔案，包含所有系統設計說明與完整 Python 實作。
- 新增 `requirements.txt`：列出 FastAPI、uvicorn、qrcode[pil]、Pillow、python-multipart 等相依套件。

## 能力清單（Capabilities）

### 新增能力（New Capabilities）

- `qr-code-creation`：使用者提交 URL（ASCII，最長 20 字元），服務產生 QR Code PNG 圖像並回傳。
- `qr-code-management`：使用者可列出自己建立的所有 QR Code，並依需求刪除指定項目。
- `qr-code-redirect`：掃描 QR Code 後，服務將使用者重新導向（HTTP 307）至原始 URL，延遲需低於 100ms。

### 修改能力（Modified Capabilities）

（無）

## 影響範圍（Impact）

- **新增檔案**：`qr_code_generator.py`、`requirements.txt`
- **相依套件**：fastapi、uvicorn[standard]、qrcode[pil]、pillow、python-multipart
- **API 端點**：`POST /api/users/{user_id}/qr-codes`、`GET /api/users/{user_id}/qr-codes`、`DELETE /api/users/{user_id}/qr-codes/{qr_id}`、`GET /{qr_id}`（重新導向熱路徑）
- **無破壞性變更**：本專案為全新建立，不影響現有程式碼。

## Context

本專案是一個學習用的系統設計主題，目標是透過實作一個可運行的 QR Code 產生服務，理解高可用性、低延遲、大規模儲存等核心系統設計概念。所有邏輯集中在單一 Python 檔案 `qr_code_generator.py`，以最小複雜度呈現完整的分層架構（Data Model → Storage → Service → API）。

規模目標：1 億使用者、10 億 QR Codes、重新導向延遲 < 100ms。

## Goals / Non-Goals

**Goals:**
- 以 FastAPI 實作四個端點：建立、列出、刪除 QR Code，以及掃描重新導向。
- 以 In-Memory Storage 模擬 Redis（熱路徑 cache）＋ PostgreSQL（持久層）的雙層架構，並在程式碼中明確標註升級路徑。
- 以繁體中文撰寫所有說明文件，技術術語保留英文。

**Non-Goals:**
- 不實作真實的 Redis / PostgreSQL 連線。
- 不實作使用者驗證（身份以 `user_id` query parameter 代替）。
- 不建立 Docker 或 CI/CD 流程。

## Decisions

### 決策 1：單一檔案架構

**選擇**：所有程式碼放在 `qr_code_generator.py`，不拆分模組。

**理由**：這是學習主題，每個主題一個專用檔案，便於閱讀與對照系統設計說明。若拆分模組，跨檔案跳轉會增加學習摩擦。

**替代方案**：建立 `qr_code_generator/` 套件，分為 models.py、storage.py、service.py、api.py。適合生產環境，但對學習目標過於複雜。

---

### 決策 2：Base62 短 ID（6 字元）

**選擇**：使用 `[A-Z][a-z][0-9]` 組成的 6 字元 ID（62^6 ≈ 568 億個唯一值）。

**理由**：
- URL-safe：無需 percent-encoding。
- 容量充足：568 億 >> 10 億目標，即使達到 10 億也只有 1.8% 碰撞機率。
- QR-friendly：QR Code 的英數字模式（Alphanumeric mode）比 Byte mode 每字元佔用更少模組，短 ID 產生更小的 QR Code。

**替代方案**：Redis `INCR` 轉 Base62，徹底消除碰撞，但 ID 具可預測性。

---

### 決策 3：分離熱路徑 Cache 與完整記錄

**選擇**：`_redirect_cache`（對應 Redis）只存 `qr_id → original_url`；`_qr_codes`（對應 PostgreSQL）存完整 `QRCodeRecord`。

**理由**：重新導向端點（`GET /{qr_id}`）是唯一需要 < 100ms 的路徑。Redis GET 約 0.5ms，PostgreSQL SELECT 約 5–20ms。只有熱路徑才需要 Redis，避免過度快取。

---

### 決策 4：HTTP 307 而非 301

**選擇**：重新導向回應使用 `307 Temporary Redirect`。

**理由**：301 會被瀏覽器永久快取，若未來需要更新目標 URL 或追蹤掃描事件，快取的瀏覽器不會再次詢問伺服器。307 確保每次掃描都經過伺服器，保留分析數據與未來修改目標 URL 的彈性。

---

### 決策 5：重新導向端點掛載於根路徑

**選擇**：`GET /{qr_id}` 而非 `GET /api/redirect/{qr_id}`。

**理由**：QR Code 中編碼的 URL 越短，QR 矩陣越小、越容易掃描。根路徑 URL（如 `https://qr.example.com/aB3x9Z`）比巢狀路徑節省多個字元。

---

### 決策 6：建立時重複 URL 回傳 409

**選擇**：同一使用者對同一 URL 發出第二次建立請求時，回傳 `409 Conflict`。

**理由**：強制客戶端明確處理重複情況，避免靜默建立多個指向同一目標的 QR Code，造成管理混亂。

**替代方案**：冪等設計，回傳既有記錄（HTTP 200）。較友善但難以偵錯。

## Risks / Trade-offs

- **In-Memory 資料不持久** → 伺服器重啟後所有 QR Code 消失。學習環境可接受；生產環境需替換為 PostgreSQL + Redis。
- **scan_count 未即時更新** → 目前每次重新導向不更新計數器（保護 < 100ms SLA）。若需要準確計數，需加入非同步事件佇列（Kafka → counter service）。
- **無速率限制** → 任何人可無限建立 QR Code。生產環境需在 API Gateway 或 middleware 層加入 rate limiting。
- **user_id 無驗證** → 任何人可用任意 user_id 存取或刪除他人的 QR Code（已透過 404 遮蔽存在性）。生產環境需 JWT 或 session 驗證。

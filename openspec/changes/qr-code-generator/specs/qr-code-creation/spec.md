## ADDED Requirements

### Requirement: 使用者可提交 URL 以產生 QR Code

服務 SHALL 接受使用者提交的 URL（僅限 ASCII 字元，最長 20 字元），產生對應的 QR Code PNG 圖像並以 HTTP 201 回傳。

#### Scenario: 成功建立 QR Code
- **GIVEN** 使用者提交一個合法的 URL（ASCII，長度 ≤ 20）
- **WHEN** 呼叫 `POST /api/users/{user_id}/qr-codes?url=<url>`
- **THEN** 回應狀態碼為 201，Content-Type 為 `image/png`，Body 為 QR Code 圖像的 PNG binary

#### Scenario: URL 超過最大長度
- **GIVEN** 使用者提交的 URL 長度超過 20 字元
- **WHEN** 呼叫 `POST /api/users/{user_id}/qr-codes?url=<url>`
- **THEN** 回應狀態碼為 422，Body 包含錯誤說明訊息

#### Scenario: URL 包含非 ASCII 字元
- **GIVEN** 使用者提交的 URL 含有非 ASCII 字元（例如中文）
- **WHEN** 呼叫 `POST /api/users/{user_id}/qr-codes?url=<url>`
- **THEN** 回應狀態碼為 422，Body 包含錯誤說明訊息

#### Scenario: 同一使用者重複提交相同 URL
- **GIVEN** 使用者已建立過某 URL 的 QR Code
- **WHEN** 再次呼叫 `POST /api/users/{user_id}/qr-codes?url=<same_url>`
- **THEN** 回應狀態碼為 409，Body 包含重複衝突說明

### Requirement: QR Code 內嵌短網址而非原始 URL

服務 SHALL 在 QR Code 圖像中編碼重新導向短網址（例如 `http://localhost:8000/{qr_id}`），而非直接編碼使用者提交的原始 URL。

#### Scenario: QR Code 內容為重新導向 URL
- **GIVEN** 使用者成功建立 QR Code
- **WHEN** 解碼該 QR Code 圖像
- **THEN** 解碼內容為服務的短網址格式（`{BASE_REDIRECT_URL}/{qr_id}`），而非原始 URL

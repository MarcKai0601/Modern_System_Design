## ADDED Requirements

### Requirement: 掃描 QR Code 後重新導向至原始 URL

服務 SHALL 在使用者掃描 QR Code（或直接訪問短網址）時，以 HTTP 307 將其重新導向至原始 URL。整體延遲 SHALL 低於 100ms。

#### Scenario: 成功重新導向
- **GIVEN** 系統中存在一個有效的 QR Code（qr_id 對應的原始 URL 存在）
- **WHEN** 使用者訪問 `GET /{qr_id}`
- **THEN** 回應狀態碼為 307，`Location` header 指向原始 URL

#### Scenario: 掃描不存在的 QR Code
- **GIVEN** 指定的 `qr_id` 不存在於系統中（或已被刪除）
- **WHEN** 使用者訪問 `GET /{qr_id}`
- **THEN** 回應狀態碼為 404

### Requirement: 重新導向端點使用根路徑

服務 SHALL 將重新導向端點掛載於根路徑（`/{qr_id}`），而非巢狀路徑（如 `/api/redirect/{qr_id}`），以最小化 QR Code 編碼的 URL 長度。

#### Scenario: 短網址格式為根路徑
- **GIVEN** 使用者成功建立 QR Code
- **WHEN** 查看回傳的 QR Code metadata 中的 `redirect_url`
- **THEN** `redirect_url` 格式為 `{BASE_REDIRECT_URL}/{qr_id}`，無任何中間路徑段

### Requirement: 重新導向使用 307 而非 301

服務 SHALL 使用 HTTP 307（Temporary Redirect）而非 301（Permanent Redirect），以確保每次掃描皆經過伺服器處理，支援分析追蹤與未來的目標 URL 變更。

#### Scenario: 回應狀態碼為 307
- **GIVEN** 系統中存在一個有效的 QR Code
- **WHEN** 使用者訪問 `GET /{qr_id}`
- **THEN** 回應狀態碼 SHALL 為 307，而非 301 或 302

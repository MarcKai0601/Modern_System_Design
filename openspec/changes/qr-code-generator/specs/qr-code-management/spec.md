## ADDED Requirements

### Requirement: 使用者可列出自己的所有 QR Code

服務 SHALL 允許使用者查詢自己建立的所有 QR Code 清單，回傳 JSON 格式的 metadata（不含圖像）。

#### Scenario: 成功列出 QR Code 清單
- **GIVEN** 使用者已建立至少一個 QR Code
- **WHEN** 呼叫 `GET /api/users/{user_id}/qr-codes`
- **THEN** 回應狀態碼為 200，Body 為 JSON 陣列，每個項目包含 `qr_id`、`original_url`、`redirect_url`、`created_at`、`scan_count`

#### Scenario: 使用者尚未建立任何 QR Code
- **GIVEN** 使用者已存在但尚未建立任何 QR Code
- **WHEN** 呼叫 `GET /api/users/{user_id}/qr-codes`
- **THEN** 回應狀態碼為 200，Body 為空 JSON 陣列 `[]`

#### Scenario: 查詢不存在的使用者
- **GIVEN** 指定的 `user_id` 從未建立過任何 QR Code（使用者不存在）
- **WHEN** 呼叫 `GET /api/users/{user_id}/qr-codes`
- **THEN** 回應狀態碼為 404，Body 包含使用者不存在的說明

### Requirement: 使用者可刪除指定的 QR Code

服務 SHALL 允許使用者刪除自己建立的指定 QR Code。刪除後該 QR Code 的掃描端點 SHALL 回傳 404。

#### Scenario: 成功刪除 QR Code
- **GIVEN** 使用者已建立某個 QR Code（qr_id 存在且屬於該使用者）
- **WHEN** 呼叫 `DELETE /api/users/{user_id}/qr-codes/{qr_id}`
- **THEN** 回應狀態碼為 204，無回應 Body

#### Scenario: 刪除後掃描已刪除的 QR Code
- **GIVEN** 使用者已成功刪除某個 QR Code
- **WHEN** 呼叫 `GET /{qr_id}`
- **THEN** 回應狀態碼為 404

#### Scenario: 刪除不屬於自己的 QR Code
- **GIVEN** 指定的 `qr_id` 屬於其他使用者
- **WHEN** 呼叫 `DELETE /api/users/{user_id}/qr-codes/{qr_id}`
- **THEN** 回應狀態碼為 404（不揭露該 qr_id 是否存在）

#### Scenario: 刪除不存在的 QR Code
- **GIVEN** 指定的 `qr_id` 不存在於系統中
- **WHEN** 呼叫 `DELETE /api/users/{user_id}/qr-codes/{qr_id}`
- **THEN** 回應狀態碼為 404

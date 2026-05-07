# Python 概念對照：給 Java 開發者

這份文件說明本專案中用到的 Python 語法，以 Java 作為對照。

---

## 1. 常數（Constants）

Python 沒有 `public static final`，慣例是用全大寫命名。

```python
# Python
MAX_URL_LENGTH: int = 20
BASE62_ALPHABET: str = "ABC..."
```

```java
// Java 對應
public static final int MAX_URL_LENGTH = 20;
public static final String BASE62_ALPHABET = "ABC...";
```

---

## 2. 資料類別（Data Classes）

`@dataclass` 自動產生建構子、`__repr__`（toString）、`__eq__`（equals）。

```python
# Python — 等同 Java record 或 Lombok @Data
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class QRCodeRecord:
    qr_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
```

```java
// Java 16+ record 對應
public record QRCodeRecord(String qrId, String userId, LocalDateTime createdAt) {
    public QRCodeRecord(String qrId, String userId) {
        this(qrId, userId, LocalDateTime.now());
    }
}
```

> `field(default_factory=datetime.utcnow)` 的用意：  
> 直接寫 `= datetime.utcnow()` 只在「定義類別時」呼叫一次，所有實例會共用同一個時間。  
> `default_factory` 讓每次建立新實例時才呼叫，等同在 Java 建構子裡寫 `this.createdAt = LocalDateTime.now()`。

---

## 3. `self` vs `this`

Python 方法必須明確宣告 `self` 作為第一個參數，等同 Java 隱式的 `this`。

```python
# Python
class QRCodeService:
    def __init__(self, storage):
        self.storage = storage        # 等同 Java: this.storage = storage

    def list_qr_codes(self, user_id):
        return self.storage.get_user_qr_codes(user_id)
```

```java
// Java
class QRCodeService {
    private final InMemoryStorage storage;

    public QRCodeService(InMemoryStorage storage) {
        this.storage = storage;
    }

    public List<QRCodeRecord> listQrCodes(String userId) {
        return storage.getUserQrCodes(userId);
    }
}
```

---

## 4. 型別標注（Type Hints）

Python 的型別標注是選擇性的，執行時不強制檢查（不像 Java 編譯時強制）。  
IDE 和 `mypy` 等工具會用它做靜態分析。

```python
# Python
def get_qr_code(self, qr_id: str) -> Optional[QRCodeRecord]:
    ...
```

```java
// Java
public Optional<QRCodeRecord> getQrCode(String qrId) { ... }
```

---

## 5. 容器型別

| Python | Java |
|--------|------|
| `dict[str, User]` | `HashMap<String, User>` |
| `list[str]` | `List<String>` / `ArrayList<String>` |
| `Optional[str]` | `Optional<String>`（或直接回傳 `null`） |
| `tuple[A, B]` | 沒有直接對應，通常用自訂 class 或 `Pair<A, B>` |

---

## 6. `Optional` 與 `None`

Python 的 `None` 等同 Java 的 `null`。  
`Optional[str]` 代表「可能回傳 `None`」，是型別標注慣例，不是包裝物件。

```python
# Python：检查 None 用 is None（不要用 == None）
result = storage.get_qr_code(qr_id)
if result is None:
    raise QRCodeNotFoundError(...)
```

```java
// Java
QRCodeRecord result = storage.getQrCode(qrId);
if (result == null) {
    throw new QRCodeNotFoundException(...);
}
```

---

## 7. `dict` 操作

```python
# 取值，找不到回傳 None（不拋例外）
value = my_dict.get(key)

# 取值，找不到回傳預設值
value = my_dict.get(key, default)

# 移除，找不到不拋例外
my_dict.pop(key, None)

# 確認 key 是否存在
if key in my_dict: ...
if key not in my_dict: ...
```

```java
// Java 對應
map.getOrDefault(key, null);
map.getOrDefault(key, defaultValue);
map.remove(key);                        // 找不到回傳 null
map.containsKey(key);
!map.containsKey(key);
```

---

## 8. List Comprehension

```python
# Python
result = [record for record in records if record.user_id == user_id]
```

```java
// Java Stream 對應
List<QRCodeRecord> result = records.stream()
    .filter(r -> r.getUserId().equals(userId))
    .collect(Collectors.toList());
```

---

## 9. f-string（字串格式化）

```python
# Python
message = f"User '{user_id}' already has QR code for '{url}'."
elapsed = f"{elapsed_ms:.3f} ms"   # 小數點後 3 位
```

```java
// Java 對應
String message = String.format("User '%s' already has QR code for '%s'.", userId, url);
// 或 Java 15+
String message = "User '%s' already has QR code for '%s'.".formatted(userId, url);
```

---

## 10. 例外（Exceptions）

Python 例外全都是「非受檢（unchecked）」，不需要在方法簽名加 `throws`。  
繼承語法與 Java 相同：`class Child(Parent)`。

```python
# Python
class QRCodeError(Exception): ...
class URLValidationError(QRCodeError): ...

# 拋出
raise URLValidationError("URL too long.")

# 捕捉
try:
    ...
except URLValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

```java
// Java
class QRCodeException extends RuntimeException { ... }
class URLValidationException extends QRCodeException { ... }

throw new URLValidationException("URL too long.");

try { ... }
catch (URLValidationException e) {
    throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage());
}
```

---

## 11. 私有成員慣例

Python 沒有 `private` 關鍵字，用「底線前綴」表示「請勿從外部直接存取」。

```python
self._users = {}       # 慣例私有
self.__secret = "x"   # 雙底線會做名稱修飾（name mangling），更強的慣例
```

```java
private Map<String, User> users = new HashMap<>();
```

---

## 12. 相對匯入（Relative Import）

```python
from .models import QRCodeRecord     # . 代表同一個 package（qr_code/）
from ..utils import helper           # .. 代表上一層 package
```

```java
// Java 的同 package 下不需要 import
// 跨 package 才需要
import com.example.qrcode.models.QRCodeRecord;
```

---

## 13. FastAPI 路由 vs Spring MVC

```python
# Python FastAPI
@app.get("/api/users/{user_id}/qr-codes", status_code=200)
def list_qr_codes(user_id: str) -> JSONResponse:
    ...
```

```java
// Java Spring MVC
@GetMapping("/api/users/{userId}/qr-codes")
@ResponseStatus(HttpStatus.OK)
public ResponseEntity<List<QRCodeRecord>> listQrCodes(@PathVariable String userId) {
    ...
}
```

---

## 14. 多值回傳（Tuple）

Python 函式可直接回傳多個值，接收端用「解包（unpacking）」取出。

```python
# Python
def create_qr_code(...) -> tuple[QRCodeRecord, bytes]:
    return record, image_bytes

# 呼叫端解包
record, image_bytes = service.create_qr_code(user_id, url)
```

```java
// Java 沒有直接對應，通常定義 Result class
public record CreateResult(QRCodeRecord record, byte[] imageBytes) {}

CreateResult result = service.createQrCode(userId, url);
QRCodeRecord record = result.record();
byte[] imageBytes = result.imageBytes();
```

---

## 15. `io.BytesIO` vs `ByteArrayOutputStream`

```python
buffer = io.BytesIO()          # 記憶體內的二進位流
img.save(buffer, format="PNG")
buffer.seek(0)                 # 移回開頭，準備讀取
data = buffer.read()           # 取得全部 bytes
```

```java
ByteArrayOutputStream buffer = new ByteArrayOutputStream();
ImageIO.write(img, "PNG", buffer);
byte[] data = buffer.toByteArray();
```

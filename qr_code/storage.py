"""
Storage layer: in-memory implementation of the Redis + PostgreSQL backend.
"""

import random
# Optional 表示回傳值可能是 None（等同 Java 的 Optional<T> 或直接回傳 null）。
# Python 3.10+ 可改寫為 str | None，這裡用 Optional 可讀性較高。
from typing import Optional

# from .models 是「相對匯入」，. 代表同一個 package（qr_code/）。
# 等同 Java 的 import com.example.qrcode.models.*;
from .models import BASE62_ALPHABET, SHORT_ID_LENGTH, QRCodeRecord, User


class InMemoryStorage:
    """
    In-memory storage using Python dicts.

    This implementation is the functional equivalent of a Redis + PostgreSQL
    backend. The interface is identical — swapping the implementation is
    mechanical once you add an ORM and a Redis client.

    Production upgrade path:
    ┌─────────────────────────────┬──────────────────────────────────────────────────┐
    │ This dict                   │ Production equivalent                            │
    ├─────────────────────────────┼──────────────────────────────────────────────────┤
    │ _redirect_cache             │ Redis HSET/HGET qr_id → original_url            │
    │ _qr_codes                   │ PostgreSQL table `qr_codes`                      │
    │ _users                      │ PostgreSQL table `users`                         │
    │ _user_qr_index              │ PostgreSQL index on (user_id, qr_id)             │
    │                             │ OR Redis SET per user: SADD user:{id}:codes {id} │
    └─────────────────────────────┴──────────────────────────────────────────────────┘

    Why a separate _redirect_cache?
    The redirect hot path (GET /{qr_id}) only needs qr_id → original_url.
    Fetching the full QRCodeRecord from PostgreSQL every time adds latency.
    Redis holds only what the hot path needs — a single string per QR code.
    """

    def __init__(self) -> None:
        # __init__ 是 Python 的建構子，等同 Java 的 constructor。
        # self 是必須明確宣告的第一個參數，等同 Java 的 this（只是 Java 是隱式的）。

        # dict[str, User] 等同 Java 的 HashMap<String, User>。
        # 底線前綴（_users）是 Python 的「私有慣例」，
        # 沒有像 Java 的 private 關鍵字強制限制，但代表「不應從外部直接存取」。
        self._users: dict[str, User] = {}
        self._qr_codes: dict[str, QRCodeRecord] = {}        # keyed by qr_id
        self._user_qr_index: dict[str, list[str]] = {}      # user_id → [qr_id, ...]
        self._redirect_cache: dict[str, str] = {}            # qr_id → original_url

    def get_or_create_user(self, user_id: str) -> User:
        # `key not in dict` 等同 Java 的 !map.containsKey(key)
        if user_id not in self._users:
            # User(user_id=user_id) 使用「具名引數（keyword argument）」呼叫建構子，
            # 等同 Java 的 new User(userId)，但更明確不易出錯。
            self._users[user_id] = User(user_id=user_id)
            self._user_qr_index[user_id] = []   # [] 是空 list，等同 new ArrayList<>()
        return self._users[user_id]

    def save_qr_code(self, record: QRCodeRecord) -> None:
        # -> None 表示此方法沒有回傳值，等同 Java 的 void。
        self._qr_codes[record.qr_id] = record
        self._redirect_cache[record.qr_id] = record.original_url   # hot-path cache
        self._user_qr_index[record.user_id].append(record.qr_id)

    def get_qr_code(self, qr_id: str) -> Optional[QRCodeRecord]:
        # dict.get(key) 找不到 key 時回傳 None（不拋例外），
        # 等同 Java HashMap.getOrDefault(key, null)。
        return self._qr_codes.get(qr_id)

    def get_user_qr_codes(self, user_id: str) -> list[QRCodeRecord]:
        # dict.get(key, default) 找不到時回傳第二個參數，等同 Java 的 getOrDefault()。
        qr_ids = self._user_qr_index.get(user_id, [])

        # List Comprehension（串列生成式）：
        # [expression for item in iterable if condition]
        # 等同 Java Stream:
        # qr_ids.stream()
        #        .filter(qid -> _qr_codes.containsKey(qid))
        #        .map(qid -> _qr_codes.get(qid))
        #        .collect(Collectors.toList())
        return [self._qr_codes[qid] for qid in qr_ids if qid in self._qr_codes]

    def delete_qr_code(self, qr_id: str, user_id: str) -> None:
        # In production: PostgreSQL DELETE + Redis DEL, ideally in a transaction.

        # dict.pop(key, default) 移除並回傳值，找不到時回傳 default 而非拋例外。
        # 等同 Java HashMap.remove(key)，但 Java 版找不到 key 會回傳 null。
        self._qr_codes.pop(qr_id, None)
        self._redirect_cache.pop(qr_id, None)
        index = self._user_qr_index.get(user_id, [])
        if qr_id in index:
            index.remove(qr_id)

    def resolve_redirect(self, qr_id: str) -> Optional[str]:
        # Hot path: only touches _redirect_cache (Redis analog).
        # Does NOT touch _qr_codes (PostgreSQL analog).
        return self._redirect_cache.get(qr_id)

    def id_exists(self, qr_id: str) -> bool:
        # `key in dict` 等同 Java 的 map.containsKey(key)，時間複雜度 O(1)。
        return qr_id in self._qr_codes

    def user_has_url(self, user_id: str, url: str) -> bool:
        # In production: enforced by a UNIQUE constraint on (user_id, original_url).
        for qid in self._user_qr_index.get(user_id, []):
            record = self._qr_codes.get(qid)
            # `and` 是 Python 的邏輯運算子，等同 Java 的 &&
            if record and record.original_url == url:
                return True
        return False


def generate_short_id(storage: InMemoryStorage, length: int = SHORT_ID_LENGTH) -> str:
    """
    Generate a collision-free Base62 short ID using random sampling with retry.

    Collision probability at 1 billion codes (1.8% of 56B space):
      P(collision on single draw) ≈ 1.8%
      Expected retries to find a free ID: ~1.02  (negligible overhead)

    Production alternative — Redis INCR → Base62:
      INCR global:qr_counter  →  integer N  →  to_base62(N)
      Eliminates collisions entirely. Trade-off: IDs are sequential
      (predictable), which may be undesirable for security.
    """
    # length: int = SHORT_ID_LENGTH 是「帶預設值的參數」，
    # 等同 Java 的方法多載（overloading）：呼叫時可省略此參數。
    while True:
        # "".join(iterable) 把可迭代物件的元素串接成字串，
        # 等同 Java 的 String.join("", list) 或 StringBuilder。
        # random.choices(population, k=n) 有放回地隨機抽 n 個元素。
        candidate = "".join(random.choices(BASE62_ALPHABET, k=length))
        if not storage.id_exists(candidate):
            return candidate

"""
Storage layer: in-memory implementation of the Redis + PostgreSQL backend.
"""

import random
from typing import Optional

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
        self._users: dict[str, User] = {}
        self._qr_codes: dict[str, QRCodeRecord] = {}        # keyed by qr_id
        self._user_qr_index: dict[str, list[str]] = {}      # user_id → [qr_id, ...]
        self._redirect_cache: dict[str, str] = {}            # qr_id → original_url

    def get_or_create_user(self, user_id: str) -> User:
        if user_id not in self._users:
            self._users[user_id] = User(user_id=user_id)
            self._user_qr_index[user_id] = []
        return self._users[user_id]

    def save_qr_code(self, record: QRCodeRecord) -> None:
        self._qr_codes[record.qr_id] = record
        self._redirect_cache[record.qr_id] = record.original_url   # hot-path cache
        self._user_qr_index[record.user_id].append(record.qr_id)

    def get_qr_code(self, qr_id: str) -> Optional[QRCodeRecord]:
        return self._qr_codes.get(qr_id)

    def get_user_qr_codes(self, user_id: str) -> list[QRCodeRecord]:
        qr_ids = self._user_qr_index.get(user_id, [])
        return [self._qr_codes[qid] for qid in qr_ids if qid in self._qr_codes]

    def delete_qr_code(self, qr_id: str, user_id: str) -> None:
        # In production: PostgreSQL DELETE + Redis DEL, ideally in a transaction.
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
        return qr_id in self._qr_codes

    def user_has_url(self, user_id: str, url: str) -> bool:
        # In production: enforced by a UNIQUE constraint on (user_id, original_url).
        for qid in self._user_qr_index.get(user_id, []):
            record = self._qr_codes.get(qid)
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
    while True:
        candidate = "".join(random.choices(BASE62_ALPHABET, k=length))
        if not storage.id_exists(candidate):
            return candidate

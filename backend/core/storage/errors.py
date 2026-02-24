from __future__ import annotations


class StorageError(Exception):
    code = "storage_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StorageLimitExceeded(StorageError):
    code = "storage_limit_exceeded"


class StorageQueryNotAllowed(StorageError):
    code = "storage_query_not_allowed"


class StorageRateLimited(StorageError):
    code = "storage_rate_limited"


class StorageRpcTimeout(StorageError):
    code = "storage_rpc_timeout"


class StorageDdlNotAllowed(StorageError):
    code = "storage_ddl_not_allowed"


__all__ = [
    "StorageDdlNotAllowed",
    "StorageError",
    "StorageLimitExceeded",
    "StorageQueryNotAllowed",
    "StorageRateLimited",
    "StorageRpcTimeout",
]

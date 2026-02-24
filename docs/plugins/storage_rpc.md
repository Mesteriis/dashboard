# StorageRPC (`oko.storage.rpc.v1`)

`StorageRPC` — единый интерфейс доступа плагинов и фоновых задач к storage.

Поддерживаемые mode backend-реализаций:

- `core_universal` (Mode A)
- `core_physical_tables` (Mode B)

Плагины и collectors не получают DB session напрямую.

## Контракты

- `StorageRpcRequest(id, ts, plugin_id, op, table?, key?, where?, limit?, row?, secret?)`
- `StorageRpcResponse(id, ok, error?, result?)`

Операции:

- `kv.get`, `kv.set`, `kv.delete`
- `table.get`, `table.upsert`, `table.delete`, `table.query`

## Реализации

- `InProcStorageRPC`: прямой вызов core storage
- `BusStorageRPC`: RPC over queue `oko.storage.rpc.v1`

## Bus RPC pattern

1. Клиент публикует `StorageRpcEnvelope` в `oko.storage.rpc.v1`
   - `correlation_id` = `request.id`
   - `reply_to` = временная очередь
2. Consumer в core валидирует `plugin_id/op`, capabilities, limits
3. Consumer выбирает storage backend по mode plugin config (`core_universal`/`core_physical_tables`)
4. Выполняет операцию
5. Публикует `StorageRpcReply` в `reply_to`
6. Клиент ждёт ответ по `correlation_id`

## Timeout & errors

`BusStorageRPC` поддерживает timeout. При timeout:

- `StorageRpcResponse.ok=false`
- `error.code=storage_rpc_timeout`
- typed wrapper поднимает `StorageRpcTimeout`

## Пример request payload

```json
{
  "id": "8e7e0f52-ec1e-47a0-aef8-1d8cbf6f57aa",
  "ts": "2026-02-23T15:20:00Z",
  "plugin_id": "autodiscover",
  "op": "table.query",
  "table": "scan_runs",
  "where": {
    "status": "completed"
  },
  "limit": 50
}
```

## Пример response payload

```json
{
  "id": "8e7e0f52-ec1e-47a0-aef8-1d8cbf6f57aa",
  "ok": true,
  "result": {
    "rows": [
      {
        "scan_id": "scan-42",
        "status": "completed"
      }
    ]
  }
}
```

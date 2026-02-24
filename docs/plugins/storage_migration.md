# Plugin Storage Migration (A <-> B)

Миграция storage между режимами выполняется только через action gateway:

- action type: `core.plugin.storage.migrate`
- capability: `core.plugin.storage.migrate`

UI не получает прямой доступ к storage migration APIs.

## Payload v1

```json
{
  "plugin_id": "autodiscover",
  "from_mode": "core_universal",
  "to_mode": "core_physical_tables",
  "tables": ["scan_runs"],
  "dry_run": false,
  "strategy": "read_only_lock"
}
```

Поля:

- `plugin_id`
- `from_mode` / `to_mode`
- `tables`
- `dry_run`
- `strategy`: `read_only_lock | dual_write`

Сейчас поддержан только `read_only_lock`.

## Events

Runner публикует события в bus:

- `migrate.started`
- `migrate.progress`
- `migrate.completed`
- `migrate.failed`

`correlation_id` = `action_id`.

## Lock behavior

Во время миграции (`read_only_lock`):

- `table_upsert` и `table_delete` блокируются для целевых таблиц
- `table_get` и `table_query` разрешены

## A -> B

1. Validate payload/plugin/tables/modes
2. Ensure B tables exist via safe DDL engine
3. Read A rows batched (`plugin_rows`, keyset pagination)
4. Upsert in B physical tables
5. Switch routing table mode to B

## B -> A

1. Read B rows batched (physical table keyset pagination)
2. Upsert in A (`plugin_rows`) with index rebuild
3. Switch routing table mode to A

## Dry run

`dry_run=true` возвращает план:

- rows per table
- without writes
- without mode switching

## Audit

Action проходит через `ActionGateway`, поэтому фиксируется в audit log (validated/executed or failed).

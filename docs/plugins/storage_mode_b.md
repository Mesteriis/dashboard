# Oko Plugin Storage Mode B (`core_physical_tables`)

Mode B создаёт физические таблицы в core DB для каждого плагина на основе DDL-спеки.

## Контракты

- `PluginStorageConfig(mode="core_physical_tables", ddl, limits, tables)`
- `StorageDDLSpec(version, tables[])`
- `StorageTableSpec(name, primary_key, indexes[])`
- `StorageLimits(...)`

## DDL source

Файл спецификации: `contracts/storage/tables.yaml`.

Core загружает DDL per plugin и применяет `safe migrate-engine`.

## Physical table naming

Логические таблицы маппятся в физические по шаблону:

- `plg__{plugin_id_sanitized}__{logical_table}`

Санитизация:

- lower-case
- `.` и `-` -> `_`
- только `[a-z0-9_]`
- пустые/опасные идентификаторы блокируются

## Safe migrate-engine

Разрешены только whitelist-операции:

- create table
- add column
- add index

Запрещены destructive изменения:

- drop table / drop column / drop index
- изменение схемы, требующее удаления существующих данных

Если в новой DDL-спеке отсутствуют уже существующие колонки, миграция отклоняется `StorageDdlNotAllowed`.

## Query model

`table_query` поддерживает только строгий режим:

- `where` обязательно непустой
- только equality + AND
- поля только из `primary_key` или `indexes[]`
- `limit` зажимается `max_query_limit`

## Limits

Применяются лимиты Mode A:

- `max_tables`
- `max_rows_per_table`
- `max_row_bytes`
- `max_kv_bytes`
- `max_qps`
- `max_query_limit`

Ошибки:

- `StorageLimitExceeded`
- `StorageQueryNotAllowed`
- `StorageRateLimited`
- `StorageDdlNotAllowed`

## Security

- default-deny по `plugin_id`, table и op
- плагины не получают DB session / raw SQL
- доступ только через `StorageRPC`

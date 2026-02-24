# Oko Plugin Storage Mode A (`core_universal`)

Mode A даёт плагину изолированное хранилище в core через три таблицы:

- `plugin_kv` для key-value
- `plugin_rows` для табличных строк
- `plugin_indexes` для индексных выборок

Все операции всегда scoped по `plugin_id`.

## Контракты

- `PluginStorageConfig(mode="core_universal", limits, tables)`
- `StorageTableSpec(name, primary_key, indexes[])`
- `StorageLimits(max_tables, max_rows_per_table, max_row_bytes, max_kv_bytes, max_qps, max_query_limit)`

## Ограничения

- `max_tables`: максимум таблиц на плагин
- `max_rows_per_table`: максимум строк в одной таблице
- `max_row_bytes`: максимум размера JSON-строки
- `max_kv_bytes`: максимум размера KV значения
- `max_qps`: rate limit на `plugin_id+op` (token bucket)
- `max_query_limit`: верхняя граница `table_query.limit` (зажимается clamp)

Ошибки:

- `StorageLimitExceeded`
- `StorageQueryNotAllowed`
- `StorageRateLimited`

## Табличные операции

### `table_upsert`

1. Проверка `table` по конфигу плагина (default-deny)
2. Проверка PK и `row_bytes`
3. Проверка `rows_per_table`
4. Запись в `plugin_rows`
5. Полная пересборка индексов для PK: delete old + insert new

### `table_query`

Поддерживается только строгий режим:

- `where` обязательно непустой
- только equality + AND (ключи словаря `where`)
- разрешены только `primary_key` и `indexes[]`

Алгоритм:

1. Для каждого условия получить кандидаты PK (`plugin_indexes` или прямой PK)
2. Пересечь множества PK
3. Прочитать строки из `plugin_rows` по финальному набору PK
4. Применить `limit` с clamp до `max_query_limit`

## Security

- default-deny: plugin/table/operation должны быть явно разрешены
- изоляция `plugin_id` enforced на каждом SQL запросе

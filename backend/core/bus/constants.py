from __future__ import annotations

BUS_EXCHANGE = "oko.bus"
BUS_EXCHANGE_TYPE = "topic"

QUEUE_STORAGE = "oko.bus.storage"
QUEUE_ACTIONS = "oko.bus.actions"
QUEUE_EVENTS = "oko.bus.events"
QUEUE_RPC_REPLY = "oko.bus.rpc.reply"
QUEUE_HEALTH_CHECK_REQUEST = "oko.bus.health.check.request"
QUEUE_HEALTH_CHECK_RESULT = "oko.bus.health.check.result"

ROUTING_STORAGE_KV_PREFIX = "storage.kv."
ROUTING_STORAGE_TABLE_PREFIX = "storage.table."
ROUTING_ACTION_EXECUTE = "action.execute"
ROUTING_EVENT_PUBLISH = "event.publish"
ROUTING_HEALTH_CHECK_REQUEST = "health.check.request"
ROUTING_HEALTH_CHECK_RESULT = "health.check.result"

STORAGE_ROUTING_KEYS = (
    "storage.kv.get",
    "storage.kv.set",
    "storage.kv.delete",
    "storage.table.get",
    "storage.table.upsert",
    "storage.table.delete",
    "storage.table.query",
)

__all__ = [
    "BUS_EXCHANGE",
    "BUS_EXCHANGE_TYPE",
    "QUEUE_ACTIONS",
    "QUEUE_EVENTS",
    "QUEUE_HEALTH_CHECK_REQUEST",
    "QUEUE_HEALTH_CHECK_RESULT",
    "QUEUE_RPC_REPLY",
    "QUEUE_STORAGE",
    "ROUTING_ACTION_EXECUTE",
    "ROUTING_EVENT_PUBLISH",
    "ROUTING_HEALTH_CHECK_REQUEST",
    "ROUTING_HEALTH_CHECK_RESULT",
    "ROUTING_STORAGE_KV_PREFIX",
    "ROUTING_STORAGE_TABLE_PREFIX",
    "STORAGE_ROUTING_KEYS",
]

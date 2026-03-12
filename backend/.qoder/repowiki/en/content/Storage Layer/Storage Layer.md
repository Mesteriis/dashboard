# Storage Layer

<cite>
**Referenced Files in This Document**
- [core/storage/__init__.py](file://core/storage/__init__.py)
- [core/storage/router.py](file://core/storage/router.py)
- [core/storage/universal.py](file://core/storage/universal.py)
- [core/storage/physical.py](file://core/storage/physical.py)
- [core/storage/repositories.py](file://core/storage/repositories.py)
- [core/storage/protocols.py](file://core/storage/protocols.py)
- [core/storage/rpc.py](file://core/storage/rpc.py)
- [core/storage/rpc_bus.py](file://core/storage/rpc_bus.py)
- [core/storage/models.py](file://core/storage/models.py)
- [core/storage/ddl_loader.py](file://core/storage/ddl_loader.py)
- [core/contracts/storage.py](file://core/contracts/storage.py)
- [core/plugins/migrations/locks.py](file://core/plugins/migrations/locks.py)
- [core/plugins/migrations/runner.py](file://core/plugins/migrations/runner.py)
- [core/plugins/migrations/registry.py](file://core/plugins/migrations/registry.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the storage abstraction layer that supports a dual-storage mode architecture. It covers:
- Dual modes: universal (logical, schemaless) and physical (schema-backed relational tables)
- Mode routing and runtime overrides
- Abstraction contracts and repository implementations
- Migration strategies, lock management, and safe transition patterns
- Query optimization techniques and consistency guarantees
- Practical operation examples and performance guidance

## Project Structure
The storage layer is organized around contracts, implementations, routing, RPC, migrations, and repositories:
- Contracts define storage configuration, limits, DDL, and RPC schemas
- Implementations provide universal and physical storage engines
- Router selects the appropriate backend per plugin and table
- RPC enables in-process and inter-service storage calls
- Repositories encapsulate domain-specific persistence logic
- Migration subsystem ensures safe transitions with locking and batch copy

```mermaid
graph TB
subgraph "Contracts"
C1["core/contracts/storage.py"]
end
subgraph "Abstractions"
P1["core/storage/protocols.py"]
M1["core/storage/models.py"]
end
subgraph "Implementations"
U1["core/storage/universal.py"]
F1["core/storage/physical.py"]
end
subgraph "Routing"
R1["core/storage/router.py"]
end
subgraph "RPC"
RPC1["core/storage/rpc.py"]
BUS1["core/storage/rpc_bus.py"]
end
subgraph "Repositories"
REPO1["core/storage/repositories.py"]
end
subgraph "Migrations"
L1["core/plugins/migrations/locks.py"]
RUN1["core/plugins/migrations/runner.py"]
REG1["core/plugins/migrations/registry.py"]
end
C1 --> P1
P1 --> U1
P1 --> F1
R1 --> U1
R1 --> F1
RPC1 --> P1
BUS1 --> RPC1
REPO1 --> M1
RUN1 --> R1
RUN1 --> U1
RUN1 --> F1
RUN1 --> L1
```

**Diagram sources**
- [core/contracts/storage.py:1-192](file://core/contracts/storage.py#L1-L192)
- [core/storage/protocols.py:1-58](file://core/storage/protocols.py#L1-L58)
- [core/storage/models.py:1-149](file://core/storage/models.py#L1-L149)
- [core/storage/universal.py:1-500](file://core/storage/universal.py#L1-L500)
- [core/storage/physical.py:1-782](file://core/storage/physical.py#L1-L782)
- [core/storage/router.py:1-120](file://core/storage/router.py#L1-L120)
- [core/storage/rpc.py:1-500](file://core/storage/rpc.py#L1-L500)
- [core/storage/rpc_bus.py:1-40](file://core/storage/rpc_bus.py#L1-L40)
- [core/storage/repositories.py:1-304](file://core/storage/repositories.py#L1-L304)
- [core/plugins/migrations/locks.py:1-41](file://core/plugins/migrations/locks.py#L1-L41)
- [core/plugins/migrations/runner.py:1-382](file://core/plugins/migrations/runner.py#L1-L382)
- [core/plugins/migrations/registry.py:1-50](file://core/plugins/migrations/registry.py#L1-L50)

**Section sources**
- [core/storage/__init__.py:1-71](file://core/storage/__init__.py#L1-L71)

## Core Components
- Storage contracts: define plugin storage configuration, limits, table specs, DDL specs, and RPC schemas
- Abstraction protocols: PluginStorage and StorageRPC define the interface for KV and table operations
- Implementations:
  - UniversalStorage: logical schemaless storage with JSON payloads and secondary indexing
  - PhysicalStorage: schema-backed relational tables with DDL enforcement and type safety
- Router: resolves storage backend per plugin/table and enforces write locks during migration
- RPC: in-process and bus-based invocation for storage operations
- Repositories: domain repositories for actions, audit logs, and configuration revisions
- Migrations: safe transition runner with read-only locks and batch copy

**Section sources**
- [core/contracts/storage.py:10-192](file://core/contracts/storage.py#L10-L192)
- [core/storage/protocols.py:9-58](file://core/storage/protocols.py#L9-L58)
- [core/storage/universal.py:85-500](file://core/storage/universal.py#L85-L500)
- [core/storage/physical.py:288-782](file://core/storage/physical.py#L288-L782)
- [core/storage/router.py:13-120](file://core/storage/router.py#L13-L120)
- [core/storage/rpc.py:65-500](file://core/storage/rpc.py#L65-L500)
- [core/storage/repositories.py:55-304](file://core/storage/repositories.py#L55-L304)
- [core/plugins/migrations/locks.py:8-41](file://core/plugins/migrations/locks.py#L8-L41)
- [core/plugins/migrations/runner.py:42-382](file://core/plugins/migrations/runner.py#L42-L382)

## Architecture Overview
The dual-storage architecture routes operations to either universal or physical storage based on plugin configuration and runtime overrides. During migrations, a read-only lock prevents writes to specific tables while data is copied to the target backend.

```mermaid
sequenceDiagram
participant Client as "Caller"
participant Router as "StorageModeRouter"
participant U as "UniversalStorage"
participant P as "PhysicalStorage"
participant Lock as "StorageMigrationLockManager"
Client->>Router : table_upsert(plugin_id, table, row)
Router->>Router : _ensure_write_allowed()
alt write locked
Router-->>Client : error (read-only)
else writable
Router->>Router : _storage_for(plugin_id, table)
alt mode == core_universal
Router->>U : table_upsert(...)
U-->>Router : row
else mode == core_physical_tables
Router->>P : table_upsert(...)
P-->>Router : row
end
Router-->>Client : row
end
```

**Diagram sources**
- [core/storage/router.py:94-117](file://core/storage/router.py#L94-L117)
- [core/storage/universal.py:189-297](file://core/storage/universal.py#L189-L297)
- [core/storage/physical.py:416-474](file://core/storage/physical.py#L416-L474)
- [core/plugins/migrations/locks.py:35-38](file://core/plugins/migrations/locks.py#L35-L38)

## Detailed Component Analysis

### Storage Mode Router
Responsibilities:
- Resolve storage backend per plugin and table
- Enforce write restrictions during migration via lock manager
- Allow per-table mode overrides for gradual migration
- Validate plugin configuration and supported modes

Key behaviors:
- get_table_mode considers per-table overrides and plugin defaults
- set_table_mode validates and applies overrides
- _ensure_write_allowed blocks writes when a table is under migration lock

```mermaid
flowchart TD
Start(["table_upsert"]) --> CheckLock["_ensure_write_allowed"]
CheckLock --> Locked{"Write locked?"}
Locked --> |Yes| Deny["Raise StorageQueryNotAllowed"]
Locked --> |No| Resolve["_storage_for"]
Resolve --> Mode{"Resolved mode"}
Mode --> |core_universal| CallU["Call UniversalStorage"]
Mode --> |core_physical_tables| CallP["Call PhysicalStorage"]
CallU --> Done(["Return row"])
CallP --> Done
Deny --> End(["Exit"])
Done --> End
```

**Diagram sources**
- [core/storage/router.py:45-117](file://core/storage/router.py#L45-L117)

**Section sources**
- [core/storage/router.py:13-120](file://core/storage/router.py#L13-L120)

### Universal Storage Engine
Capabilities:
- KV operations with secret flag and byte limits
- Table upsert with canonical JSON serialization and row/index validation
- Query by primary key or indexed fields with intersection of candidate sets
- Batch read and row counting
- Rate limiting and per-plugin limits enforced

Optimization highlights:
- Candidate set intersection for multi-field queries
- Canonical JSON normalization and byte accounting
- Index rows maintained for fast lookup

```mermaid
flowchart TD
QStart(["table_query"]) --> Validate["Validate where and fields"]
Validate --> BuildSets["Build candidate sets from PK/indexes"]
BuildSets --> Intersect["Intersect candidate sets"]
Intersect --> Empty{"Any candidates?"}
Empty --> |No| ReturnEmpty["Return []"]
Empty --> |Yes| Fetch["Fetch rows with limit/order"]
Fetch --> Decode["Deserialize JSON payloads"]
Decode --> Return(["Return list of dicts"])
```

**Diagram sources**
- [core/storage/universal.py:326-398](file://core/storage/universal.py#L326-L398)

**Section sources**
- [core/storage/universal.py:85-500](file://core/storage/universal.py#L85-L500)

### Physical Storage Engine
Capabilities:
- Schema-backed tables with strict DDL validation and type enforcement
- Upsert with payload normalization and batch read
- Query with equality filters on primary key and declared indexes
- Automatic DDL installation/upgrades guarded by a safe engine
- Per-plugin migration readiness and table caching

Safety and optimization:
- SafeDdlEngine enforces non-destructive changes and creates missing indexes
- Type normalization and timezone-aware datetime handling
- Table cache avoids repeated reflection overhead

```mermaid
flowchart TD
PStart(["table_upsert"]) --> Normalize["_normalize_payload"]
Normalize --> Exists{"PK exists?"}
Exists --> |No| CountCheck["Check rows <= limit"]
CountCheck --> Insert["INSERT row"]
Exists --> |Yes| Update["UPDATE row"]
Insert --> DoneP(["Return decoded row"])
Update --> DoneP
```

**Diagram sources**
- [core/storage/physical.py:432-474](file://core/storage/physical.py#L432-L474)

**Section sources**
- [core/storage/physical.py:288-782](file://core/storage/physical.py#L288-L782)

### Storage Contracts and Protocols
Contracts define:
- Storage limits, table specs, and DDL specs
- Plugin storage configuration with mode selection
- RPC request/response envelopes and operations

Protocols define:
- PluginStorage interface for KV and table operations
- StorageRPC interface for invocation and dispatch

```mermaid
classDiagram
class PluginStorage {
+kv_get(plugin_id, key, secret) Any?
+kv_set(plugin_id, key, value, secret) void
+kv_delete(plugin_id, key) bool
+table_get(plugin_id, table, pk) dict?
+table_upsert(plugin_id, table, row) dict
+table_delete(plugin_id, table, pk) bool
+table_query(plugin_id, table, where, limit) list[dict]
}
class StorageRPC {
+call(request) StorageRpcResponse
+kv_get(...)
+kv_set(...)
+kv_delete(...)
+table_get(...)
+table_upsert(...)
+table_delete(...)
+table_query(...)
}
```

**Diagram sources**
- [core/storage/protocols.py:9-58](file://core/storage/protocols.py#L9-L58)
- [core/contracts/storage.py:108-192](file://core/contracts/storage.py#L108-L192)

**Section sources**
- [core/contracts/storage.py:10-192](file://core/contracts/storage.py#L10-L192)
- [core/storage/protocols.py:9-58](file://core/storage/protocols.py#L9-L58)

### RPC and Bus Integration
Two RPC implementations:
- InProcStorageRPC: synchronous dispatch to a PluginStorage instance
- BusStorageRPC: asynchronous messaging over StorageRpcBus with correlation and timeouts

```mermaid
sequenceDiagram
participant Caller as "Caller"
participant RPC as "BusStorageRPC"
participant Bus as "StorageRpcBus"
participant Consumer as "StorageRpcConsumer"
participant Impl as "InProcStorageRPC"
Caller->>RPC : call(StorageRpcRequest)
RPC->>Bus : publish(envelope)
Bus-->>Consumer : deliver envelope
Consumer->>Impl : call(request)
Impl-->>Consumer : StorageRpcResponse
Consumer-->>RPC : reply
RPC-->>Caller : StorageRpcResponse
```

**Diagram sources**
- [core/storage/rpc.py:246-393](file://core/storage/rpc.py#L246-L393)
- [core/storage/rpc_bus.py:8-40](file://core/storage/rpc_bus.py#L8-L40)
- [core/storage/rpc.py:395-458](file://core/storage/rpc.py#L395-L458)

**Section sources**
- [core/storage/rpc.py:65-500](file://core/storage/rpc.py#L65-L500)
- [core/storage/rpc_bus.py:8-40](file://core/storage/rpc_bus.py#L8-L40)

### Repositories and Domain Models
Domain repositories encapsulate:
- ConfigRepository: active state and revision lifecycle
- ActionRepository: queued actions, status updates, history
- AuditRepository: audit log entries

Models define relational schemas for persistence.

```mermaid
erDiagram
CONFIG_REVISIONS {
int id PK
int revision UK
int parent_revision
text payload_json
string payload_sha256
string source
timestamptz created_at
string created_by
}
APP_STATE {
int id PK
int active_revision FK
int state_seq
timestamptz updated_at
string updated_by
string reason
}
ACTIONS {
string id PK
string type
string capability
string requested_by
timestamptz requested_at
string status
text payload_json
bool dry_run
text result_json
text error_json
string idempotency_key
string trace_id
timestamptz created_at
timestamptz started_at
timestamptz finished_at
}
AUDIT_LOG {
int id PK
timestamptz ts
string actor
string action_id
string capability
string resource
string decision
string outcome
string reason
text metadata_json
timestamptz created_at
}
APP_STATE }o--|| CONFIG_REVISIONS : "active_revision"
```

**Diagram sources**
- [core/storage/models.py:14-149](file://core/storage/models.py#L14-L149)
- [core/storage/repositories.py:55-304](file://core/storage/repositories.py#L55-L304)

**Section sources**
- [core/storage/models.py:14-149](file://core/storage/models.py#L14-L149)
- [core/storage/repositories.py:55-304](file://core/storage/repositories.py#L55-L304)

### Migration Runner and Lock Management
Migration runner coordinates:
- Plan building (row counts per table)
- Batch copy from source to target mode
- Runtime mode switch per table
- Event emission for progress and completion

Lock manager:
- Provides read-only lock for selected tables during migration
- Prevents writes while data is being copied

```mermaid
sequenceDiagram
participant GW as "ActionGateway"
participant Runner as "StorageMigrationRunner"
participant Lock as "StorageMigrationLockManager"
participant Router as "StorageModeRouter"
participant Src as "Source Storage"
participant Dst as "Target Storage"
GW->>Runner : run(action)
Runner->>Runner : _validate_request()
Runner->>Runner : _build_plan()
Runner->>Lock : read_only_lock(plugin_id, tables)
Lock-->>Runner : acquired
loop for each table
Runner->>Src : read_rows_batch(batch_size, after_pk)
Src-->>Runner : list[(pk,row)]
Runner->>Dst : migration_table_upsert(row)
Dst-->>Runner : row
Runner->>Router : set_table_mode(table, to_mode)
end
Runner-->>GW : result
```

**Diagram sources**
- [core/plugins/migrations/runner.py:58-127](file://core/plugins/migrations/runner.py#L58-L127)
- [core/plugins/migrations/locks.py:13-38](file://core/plugins/migrations/locks.py#L13-L38)
- [core/storage/router.py:66-92](file://core/storage/router.py#L66-L92)

**Section sources**
- [core/plugins/migrations/runner.py:42-382](file://core/plugins/migrations/runner.py#L42-L382)
- [core/plugins/migrations/locks.py:8-41](file://core/plugins/migrations/locks.py#L8-L41)
- [core/plugins/migrations/registry.py:15-50](file://core/plugins/migrations/registry.py#L15-L50)

## Dependency Analysis
- Router depends on plugin configs and lock manager; delegates to implementations
- Implementations depend on SQLAlchemy async sessions and DDL specs for physical mode
- RPC consumers depend on bus and storage dispatcher
- Repositories depend on SQLAlchemy ORM models
- Migration runner orchestrates router, storages, and lock manager

```mermaid
graph LR
Router["StorageModeRouter"] --> U["UniversalStorage"]
Router --> P["PhysicalStorage"]
Router --> LM["StorageMigrationLockManager"]
Runner["StorageMigrationRunner"] --> Router
Runner --> U
Runner --> P
Runner --> LM
RPC["BusStorageRPC"] --> Bus["StorageRpcBus"]
RPC --> InProc["InProcStorageRPC"]
InProc --> PS["PluginStorage"]
```

**Diagram sources**
- [core/storage/router.py:13-120](file://core/storage/router.py#L13-L120)
- [core/plugins/migrations/runner.py:42-127](file://core/plugins/migrations/runner.py#L42-L127)
- [core/storage/rpc.py:246-393](file://core/storage/rpc.py#L246-L393)
- [core/storage/rpc_bus.py:8-40](file://core/storage/rpc_bus.py#L8-L40)
- [core/storage/protocols.py:9-58](file://core/storage/protocols.py#L9-L58)

**Section sources**
- [core/storage/router.py:13-120](file://core/storage/router.py#L13-L120)
- [core/plugins/migrations/runner.py:42-127](file://core/plugins/migrations/runner.py#L42-L127)
- [core/storage/rpc.py:246-393](file://core/storage/rpc.py#L246-L393)
- [core/storage/rpc_bus.py:8-40](file://core/storage/rpc_bus.py#L8-L40)
- [core/storage/protocols.py:9-58](file://core/storage/protocols.py#L9-L58)

## Performance Considerations
- Universal storage
  - Query optimization uses candidate set intersection for multi-field filters
  - Canonical JSON normalization and byte accounting prevent oversized rows
  - Index rows enable efficient lookups; avoid non-indexed filters
- Physical storage
  - Strict type normalization and timezone handling reduce conversion overhead
  - Table cache minimizes reflection cost; invalidated on DDL changes
  - DDL engine serializes schema changes to avoid contention
- RPC
  - Bus-based RPC adds latency; use in-process RPC for local calls
  - Timeouts and correlation ids ensure reliable request-response
- Limits and rate limiting
  - Enforced per-plugin QPS and row/KV size limits protect resources
  - Query limit clamping prevents unbounded scans

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Unsupported storage mode or table
  - Ensure plugin configuration mode matches requested operation
  - Verify table specs and indexes align with queries
- Write denied during migration
  - Migration lock prevents writes; wait until lock is released
  - Confirm read-only lock scope includes the affected tables
- DDL errors
  - Non-destructive changes only; add columns, not drop
  - Primary key additions to existing tables are disallowed
- Rate limit exceeded
  - Reduce QPS or batch operations
  - Respect per-operation limits for KV and rows
- RPC timeouts
  - Increase timeout or use in-process RPC for local calls
  - Check bus connectivity and consumer readiness

**Section sources**
- [core/storage/router.py:109-117](file://core/storage/router.py#L109-L117)
- [core/storage/physical.py:212-232](file://core/storage/physical.py#L212-L232)
- [core/storage/rpc.py:273-277](file://core/storage/rpc.py#L273-L277)

## Conclusion
The storage layer provides a robust, extensible dual-mode architecture with strong contracts, safe migration controls, and performance-conscious implementations. The router and lock manager coordinate transitions, while repositories and RPC offer clean integration points for higher-level services.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Practical Operation Examples
- Universal table query
  - Use table_query with primary key or indexed fields
  - Combine multiple indexed fields for filtered results
- Physical table upsert
  - Provide complete payload with required fields
  - Respect type constraints and nullability
- Migration plan and execution
  - Build plan via row counts per table
  - Copy in batches; switch mode per table upon completion

**Section sources**
- [core/storage/universal.py:326-398](file://core/storage/universal.py#L326-L398)
- [core/storage/physical.py:416-474](file://core/storage/physical.py#L416-L474)
- [core/plugins/migrations/runner.py:215-274](file://core/plugins/migrations/runner.py#L215-L274)

### Data Consistency Guarantees
- Transactions
  - Upserts and deletes occur within transaction boundaries
- Index integrity (universal)
  - Index rows are rebuilt on upsert to maintain consistency
- Migration consistency
  - Read-only lock prevents concurrent writes during copy
  - Mode switch occurs after successful copy per table

**Section sources**
- [core/storage/universal.py:232-297](file://core/storage/universal.py#L232-L297)
- [core/storage/physical.py:459-474](file://core/storage/physical.py#L459-L474)
- [core/plugins/migrations/runner.py:93-112](file://core/plugins/migrations/runner.py#L93-L112)
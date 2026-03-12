# Plugin Architecture Overview

<cite>
**Referenced Files in This Document**
- [service.py](file://core/plugins/service.py)
- [registry.py](file://core/plugins/registry.py)
- [router.py](file://core/plugins/router.py)
- [loader.py](file://core/plugins/loader.py)
- [schemas.py](file://core/plugins/schemas.py)
- [page_manifest.py](file://core/plugins/page_manifest.py)
- [store.py](file://core/plugins/store.py)
- [plugins.py](file://api/v1/plugins.py)
- [app_factory.py](file://app_factory.py)
- [main.py](file://main.py)
- [plugin_manifest.py](file://plugins/autodiscover/plugin_manifest.py)
- [ui.yaml](file://plugins/autodiscover/ui.yaml)
- [manifest.py](file://plugins/dns_trace/manifest.py)
- [page_manifest.yaml](file://plugins/dns_trace/page_manifest.yaml)
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

## Introduction
This document explains the plugin system architecture and design patterns used in the backend. It focuses on how plugins are discovered, loaded, enabled/disabled, routed, and executed at runtime. The system centers around four key components:
- PluginService: The orchestrator that coordinates discovery, loading, enabling, routing, and lifecycle hooks.
- PluginRegistry: Manages plugin lifecycle states and loads/unloads modules.
- PluginRouter: Dynamically mounts plugin pages and APIs into the FastAPI application.
- PluginScanner and PluginLoader: Handle filesystem discovery and dynamic import of plugin packages.

The plugin system supports event-driven lifecycle hooks (startup/shutdown), dependency injection via setup kwargs, and a clear separation of concerns across discovery, loading, routing, and execution phases.

## Project Structure
The plugin system spans several modules under core/plugins and integrates with API endpoints and the application factory.

```mermaid
graph TB
subgraph "Core Plugin System"
PS["PluginService<br/>orchestrator"]
PR["PluginRegistry<br/>lifecycle manager"]
PTR["PluginRouter<br/>dynamic routes"]
PSCN["PluginScanner<br/>filesystem discovery"]
PLDR["PluginLoader<br/>dynamic import"]
PM["PluginManifest<br/>metadata"]
PUI["PluginUIConfig<br/>UI integration"]
PPM["PluginPageManifest<br/>frontend schema"]
end
subgraph "API Layer"
API["FastAPI Plugins Router<br/>/api/v1/plugins"]
end
subgraph "Application"
APP["FastAPI App"]
AF["App Factory<br/>include routers"]
end
subgraph "Plugins"
AD["autodiscover<br/>manifest + ui.yaml"]
DT["dns_trace<br/>manifest + page_manifest.yaml"]
end
PS --> PR
PS --> PTR
PR --> PSCN
PR --> PLDR
PR --> PM
PR --> PUI
PR --> PPM
PTR --> API
API --> APP
AF --> APP
AD --> PR
DT --> PR
```

**Diagram sources**
- [service.py:18-74](file://core/plugins/service.py#L18-L74)
- [registry.py:26-50](file://core/plugins/registry.py#L26-L50)
- [router.py:16-52](file://core/plugins/router.py#L16-L52)
- [loader.py:23-47](file://core/plugins/loader.py#L23-L47)
- [schemas.py:25-92](file://core/plugins/schemas.py#L25-L92)
- [page_manifest.py:152-171](file://core/plugins/page_manifest.py#L152-L171)
- [plugins.py:19-362](file://api/v1/plugins.py#L19-L362)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

**Section sources**
- [service.py:18-74](file://core/plugins/service.py#L18-L74)
- [registry.py:26-50](file://core/plugins/registry.py#L26-L50)
- [router.py:16-52](file://core/plugins/router.py#L16-L52)
- [loader.py:23-47](file://core/plugins/loader.py#L23-L47)
- [schemas.py:25-92](file://core/plugins/schemas.py#L25-L92)
- [page_manifest.py:152-171](file://core/plugins/page_manifest.py#L152-L171)
- [plugins.py:19-362](file://api/v1/plugins.py#L19-L362)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

## Core Components
- PluginService: Central orchestrator that initializes scanner, registry, and router; manages runtime lifecycle hooks; and exposes CRUD operations for plugins.
- PluginRegistry: Maintains plugin state machine, loads/unloads modules, parses manifests/UI configs, and resolves page manifests.
- PluginRouter: Mounts plugin pages and APIs into FastAPI routers; handles route unmounting and static asset hints.
- PluginScanner: Discovers plugin packages by scanning directories for valid plugin layouts.
- PluginLoader: Dynamically imports plugin modules and manages teardown.
- Schemas: Defines PluginInfo, PluginManifest, PluginUIConfig, PluginState, and PluginScope.
- Page Manifest: Validates and serializes plugin page/dashboard/frontend manifests.
- Store Integration: Provides StoreClient and PluginInstaller for remote plugin installation.

**Section sources**
- [service.py:18-299](file://core/plugins/service.py#L18-L299)
- [registry.py:26-407](file://core/plugins/registry.py#L26-L407)
- [router.py:16-448](file://core/plugins/router.py#L16-L448)
- [loader.py:23-329](file://core/plugins/loader.py#L23-L329)
- [schemas.py:9-131](file://core/plugins/schemas.py#L9-L131)
- [page_manifest.py:152-347](file://core/plugins/page_manifest.py#L152-L347)
- [store.py:17-239](file://core/plugins/store.py#L17-L239)

## Architecture Overview
The plugin system follows a layered architecture:
- Discovery: PluginScanner scans configured directories and registers plugin locations.
- Registration: PluginRegistry creates PluginInfo entries, parses manifests and UI configs, and resolves page manifests.
- Loading: PluginLoader dynamically imports plugin modules and invokes optional setup hooks.
- Routing: PluginRouter mounts plugin pages and APIs into FastAPI routers.
- Runtime: PluginService schedules startup/shutdown hooks and monitors filesystem changes.

```mermaid
sequenceDiagram
participant App as "FastAPI App"
participant PS as "PluginService"
participant PR as "PluginRegistry"
participant PSCN as "PluginScanner"
participant PLDR as "PluginLoader"
participant PTR as "PluginRouter"
App->>PS : create(plugin_dirs, base_path, api_base_path)
PS->>PSCN : scan()
PSCN-->>PR : locations
PR->>PR : initialize()/scan()
PS->>PTR : create(router)
PR->>PR : load_plugin(id) for active
PLDR->>PLDR : load_plugin()
PR-->>PS : PluginInfo
PS->>PTR : mount_all_active()
App-->>App : routes mounted
```

**Diagram sources**
- [service.py:30-73](file://core/plugins/service.py#L30-L73)
- [registry.py:71-98](file://core/plugins/registry.py#L71-L98)
- [router.py:433-436](file://core/plugins/router.py#L433-L436)
- [loader.py:119-171](file://core/plugins/loader.py#L119-L171)

## Detailed Component Analysis

### PluginService: Orchestration and Lifecycle Hooks
Responsibilities:
- Initialize scanner, registry, and router.
- Auto-load active plugins during initialization.
- Expose operations: list, get, load, unload, reload, enable, disable.
- Manage runtime lifecycle: schedule and invoke on_startup/on_shutdown hooks.
- Watch filesystem for changes and refresh runtime state.

Key behaviors:
- Startup/shutdown hooks are scheduled asynchronously and tracked per plugin.
- Runtime refresh compares fingerprints of plugin directories and triggers reloads or mounts as needed.

```mermaid
flowchart TD
Start([Startup]) --> Init["Initialize Scanner/Registry/Router"]
Init --> AutoLoad["Auto-load ACTIVE plugins"]
AutoLoad --> Mount["Mount routes for active"]
Mount --> Running(["Runtime Running"])
Running --> HookStart["Invoke on_startup hooks"]
HookStart --> Watch["Watch loop (poll)"]
Watch --> Sync["registry.sync()"]
Sync --> Changes{"Added/Removed/Reloaded?"}
Changes --> |Yes| Apply["Mount/Unmount/Reload"]
Apply --> Fingerprints["Refresh fingerprints"]
Fingerprints --> Watch
Changes --> |No| Watch
```

**Diagram sources**
- [service.py:30-73](file://core/plugins/service.py#L30-L73)
- [service.py:188-201](file://core/plugins/service.py#L188-L201)
- [service.py:224-283](file://core/plugins/service.py#L224-L283)

**Section sources**
- [service.py:18-299](file://core/plugins/service.py#L18-L299)

### PluginRegistry: Lifecycle Management and Module Loading
Responsibilities:
- Discover plugins via PluginScanner.
- Parse manifests and UI configs from either Python modules or YAML files.
- Load/unload plugin modules via PluginLoader.
- Invoke setup(teardown) hooks if present.
- Maintain state transitions: DISCOVERED → LOADING → ACTIVE → ERROR/DISABLED.

Patterns:
- Factory-like creation of PluginInfo from discovered locations.
- Signature-aware invocation of setup to inject supported kwargs.

```mermaid
classDiagram
class PluginRegistry {
+initialize()
+scan() dict
+sync() dict
+load_plugin(plugin_id) PluginInfo
+unload_plugin(plugin_id) bool
+reload_plugin(plugin_id) PluginInfo
+enable_plugin(plugin_id) PluginInfo
+disable_plugin(plugin_id) bool
+to_dict() dict
}
class PluginLoader {
+load_plugin(plugin_info) PluginInfo
+unload_plugin(plugin_id) bool
+get_module(plugin_id) Any
+is_loaded(plugin_id) bool
}
class PluginScanner {
+scan() PluginLocation[]
+get_discovered() dict
}
PluginRegistry --> PluginScanner : "uses"
PluginRegistry --> PluginLoader : "uses"
```

**Diagram sources**
- [registry.py:26-407](file://core/plugins/registry.py#L26-L407)
- [loader.py:110-218](file://core/plugins/loader.py#L110-L218)
- [loader.py:23-108](file://core/plugins/loader.py#L23-L108)

**Section sources**
- [registry.py:26-407](file://core/plugins/registry.py#L26-L407)
- [loader.py:110-218](file://core/plugins/loader.py#L110-L218)

### PluginRouter: Dynamic Route Mounting
Responsibilities:
- Mount plugin pages and APIs into FastAPI routers.
- Support route unmounting on disable/unload.
- Render default plugin pages if no custom handler exists.
- Include plugin-provided API routers when present.

Integration:
- Mounted by app factory into the main application.
- Exposes management endpoints via API router.

```mermaid
sequenceDiagram
participant PR as "PluginRegistry"
participant PS as "PluginService"
participant PTR as "PluginRouter"
participant API as "FastAPI App"
PR->>PS : load_plugin(id)
PS->>PTR : _mount_plugin_routes(plugin)
PTR->>PTR : _mount_plugin_page()
PTR->>PTR : _mount_plugin_api_routes()
API-->>API : include_router(PTR.get_router())
API-->>API : include_router(PTR.get_api_router())
```

**Diagram sources**
- [router.py:118-156](file://core/plugins/router.py#L118-L156)
- [router.py:195-236](file://core/plugins/router.py#L195-L236)
- [router.py:404-420](file://core/plugins/router.py#L404-L420)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

**Section sources**
- [router.py:16-448](file://core/plugins/router.py#L16-L448)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

### PluginScanner and PluginLoader: Discovery and Dynamic Import
Discovery:
- Scans directories for plugin packages that contain __init__.py and a manifest file.
- Supports nested subdirectories and marks discovered packages with scope.

Dynamic Import:
- Uses importlib to load plugin modules at runtime.
- Calls teardown on unload and cleans sys.modules.

```mermaid
flowchart TD
Scan["Scan directories"] --> Found{"Found plugin dir?"}
Found --> |Yes| Register["Register PluginLocation"]
Found --> |No| Next["Next item"]
Register --> Next
Next --> DoneScan["Done"]
Load["Load plugin module"] --> Spec["importlib.spec_from_file_location"]
Spec --> Exec["exec_module"]
Exec --> Active["ACTIVE state"]
Active --> Teardown["Optional teardown()"]
Teardown --> Unload["Remove from sys.modules"]
```

**Diagram sources**
- [loader.py:48-108](file://core/plugins/loader.py#L48-L108)
- [loader.py:119-171](file://core/plugins/loader.py#L119-L171)
- [loader.py:173-206](file://core/plugins/loader.py#L173-L206)

**Section sources**
- [loader.py:23-329](file://core/plugins/loader.py#L23-L329)

### Plugin Data Models and Page Manifests
- PluginInfo: Aggregates manifest, UI config, state, module, and metadata.
- PluginManifest: Metadata like name, version, capabilities, actions, events.
- PluginUIConfig: UI integration settings (page path, menu, widgets, API prefix).
- PluginPageManifestV1: Frontend page/dashboard schema validated and serialized.

```mermaid
classDiagram
class PluginInfo {
+id : str
+manifest : PluginManifest
+ui_config : PluginUIConfig
+state : PluginState
+module : Any
+to_dict() dict
}
class PluginManifest {
+name : str
+version : str
+capabilities : tuple~str~
+actions : tuple~dict~
+events : tuple~dict~
}
class PluginUIConfig {
+has_page : bool
+page_path : str
+api_prefix : str
+show_in_menu : bool
+widgets : tuple~dict~
}
class PluginPageManifestV1 {
+plugin_id : str
+version : str
+manifest_version : str
+plugin_api_version : str
+capabilities : str[]
+frontend : PluginFrontendV1
+page : PluginPageV1
+dashboard : PluginDashboardV1
}
PluginInfo --> PluginManifest
PluginInfo --> PluginUIConfig
PluginInfo --> PluginPageManifestV1 : "metadata"
```

**Diagram sources**
- [schemas.py:25-131](file://core/plugins/schemas.py#L25-L131)
- [page_manifest.py:152-347](file://core/plugins/page_manifest.py#L152-L347)

**Section sources**
- [schemas.py:25-131](file://core/plugins/schemas.py#L25-L131)
- [page_manifest.py:152-347](file://core/plugins/page_manifest.py#L152-L347)

### Plugin Store Integration
- StoreClient: Syncs plugin catalog, fetches manifests, downloads plugins.
- PluginInstaller: Installs plugins from store to local directory, resolves package roots, copies files, and returns PluginInfo for registry.

```mermaid
sequenceDiagram
participant SC as "StoreClient"
participant PI as "PluginInstaller"
participant FS as "Filesystem"
participant PR as "PluginRegistry"
SC->>SC : sync_plugins()
SC->>SC : get_plugin_manifest(id)
SC->>SC : download_plugin(id)
SC-->>PI : plugin_path
PI->>FS : resolve_plugin_root()
PI->>FS : copytree(src, dest)
PI-->>PR : PluginInfo(DISCOVERED, path=dest)
```

**Diagram sources**
- [store.py:30-239](file://core/plugins/store.py#L30-L239)

**Section sources**
- [store.py:17-239](file://core/plugins/store.py#L17-L239)

### Example Plugins: autodiscover and dns_trace
- autodiscover: Demonstrates manifest constants, UI config via YAML, page handler, and API router.
- dns_trace: Minimal manifest and page manifest for dashboard integration.

```mermaid
graph LR
AD["autodiscover<br/>plugin_manifest.py + ui.yaml"] --> PR["PluginRegistry"]
DT["dns_trace<br/>manifest.py + page_manifest.yaml"] --> PR
PR --> PM["PluginManifest"]
PR --> PUI["PluginUIConfig"]
PR --> PPM["PluginPageManifestV1"]
```

**Diagram sources**
- [plugin_manifest.py:44-77](file://plugins/autodiscover/plugin_manifest.py#L44-L77)
- [ui.yaml:4-58](file://plugins/autodiscover/ui.yaml#L4-L58)
- [manifest.py:3-9](file://plugins/dns_trace/manifest.py#L3-L9)
- [page_manifest.yaml:1-76](file://plugins/dns_trace/page_manifest.yaml#L1-L76)

**Section sources**
- [plugin_manifest.py:44-77](file://plugins/autodiscover/plugin_manifest.py#L44-L77)
- [ui.yaml:4-58](file://plugins/autodiscover/ui.yaml#L4-L58)
- [manifest.py:3-9](file://plugins/dns_trace/manifest.py#L3-L9)
- [page_manifest.yaml:1-76](file://plugins/dns_trace/page_manifest.yaml#L1-L76)

## Dependency Analysis
The plugin system exhibits clear separation of concerns:
- PluginService depends on PluginRegistry and PluginRouter.
- PluginRegistry depends on PluginScanner and PluginLoader.
- PluginRouter depends on PluginRegistry and FastAPI routers.
- API endpoints depend on PluginService via the application container.
- Application factory includes PluginRouter into the main app.

```mermaid
graph TB
PS["PluginService"] --> PR["PluginRegistry"]
PS --> PTR["PluginRouter"]
PR --> PSCN["PluginScanner"]
PR --> PLDR["PluginLoader"]
PTR --> PR
API["API v1 Plugins"] --> PS
APP["FastAPI App"] --> API
APP --> PTR
```

**Diagram sources**
- [service.py:18-74](file://core/plugins/service.py#L18-L74)
- [registry.py:26-50](file://core/plugins/registry.py#L26-L50)
- [router.py:16-52](file://core/plugins/router.py#L16-L52)
- [plugins.py:19-362](file://api/v1/plugins.py#L19-L362)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

**Section sources**
- [service.py:18-74](file://core/plugins/service.py#L18-L74)
- [registry.py:26-50](file://core/plugins/registry.py#L26-L50)
- [router.py:16-52](file://core/plugins/router.py#L16-L52)
- [plugins.py:19-362](file://api/v1/plugins.py#L19-L362)
- [app_factory.py:20-28](file://app_factory.py#L20-L28)

## Performance Considerations
- Asynchronous lifecycle hooks prevent blocking the event loop.
- Fingerprint-based change detection minimizes unnecessary reloads.
- Route mounting/unmounting avoids stale route conflicts.
- Dynamic imports occur only when needed; teardown clears sys.modules to reduce memory footprint.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Plugin fails to load: Check error state and error message in PluginInfo; verify manifest presence and import path.
- Routes not appearing: Confirm plugin is ACTIVE and UI config has_page/api_prefix set; ensure router mounted by app factory.
- Startup/Shutdown hooks failing: Inspect logs for exceptions raised during hook invocation; ensure hooks are callable and awaitable if needed.
- Runtime refresh not triggering: Verify fingerprint calculation and polling interval; ensure plugin directory permissions allow scanning.

**Section sources**
- [registry.py:307-315](file://core/plugins/registry.py#L307-L315)
- [router.py:118-156](file://core/plugins/router.py#L118-L156)
- [service.py:156-187](file://core/plugins/service.py#L156-L187)
- [service.py:285-296](file://core/plugins/service.py#L285-L296)

## Conclusion
The plugin system is designed around a robust orchestration pattern with clear boundaries between discovery, loading, routing, and runtime execution. It leverages dependency injection for setup, factory-style creation of plugin metadata, and event-driven lifecycle hooks. The integration with FastAPI ensures dynamic route mounting, while the store client enables remote plugin installation. Together, these patterns deliver a scalable, maintainable, and extensible plugin framework.
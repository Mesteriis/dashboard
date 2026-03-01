# Plugin Store Integration

## Overview

The Plugin Store integration allows the OKO Dashboard backend to discover, install, and manage plugins from a centralized store service.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OKO Dashboard Backend                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Store API   │  │   Store      │  │   Plugin     │          │
│  │  Endpoints   │  │   Client     │  │  Installer   │          │
│  │              │  │  (HTTP RPC)  │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                    │                │
│         │                 │                    │                │
│         └─────────────────┴────────────────────┘                │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Plugin Store Service                        │
│                   (http://store:8001/api/v1)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Plugin     │  │   Storage    │  │   GitHub     │          │
│  │  Registry    │  │   Service    │  │   Import     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                           │                                     │
│                    plugins/                                     │
│                    ├── uploads/                                 │
│                    └── plugins.json                             │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow

### 1. Plugin Discovery

```
User opens Plugins page
       │
       ▼
Backend calls GET /api/v1/store
       │
       ▼
Store returns list of available plugins
       │
       ▼
Backend shows plugins with "Install" buttons
```

### 2. Plugin Installation

```
User clicks "Install" on plugin
       │
       ▼
Backend calls POST /api/v1/store/{id}/install
       │
       ▼
Store Client downloads plugin from Store
       │
       ▼
Plugin Installer copies to backend/plugins/
       │
       ▼
Plugin Service discovers and loads plugin
       │
       ▼
Plugin becomes available in dashboard
```

### 3. Plugin Management

```
User can:
- Install plugin from catalog to backend/plugins/
- Uninstall plugin (removes from backend/plugins/)
- View plugin details
```

## API Endpoints

### Store Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/store` | List available plugins in store |
| GET | `/api/v1/store/{plugin_id}` | Get plugin details from store |
| POST | `/api/v1/store/{plugin_id}/install` | Install plugin from store |
| POST | `/api/v1/store/{plugin_id}/uninstall` | Uninstall plugin |
| GET | `/api/v1/store/health` | Check store availability |

### Plugin Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/plugins` | List installed plugins |
| GET | `/api/v1/plugins/{id}` | Get plugin details |
| POST | `/api/v1/plugins/{id}/load` | Load plugin |
| POST | `/api/v1/plugins/{id}/unload` | Unload plugin |
| POST | `/api/v1/plugins/{id}/enable` | Enable plugin |
| POST | `/api/v1/plugins/{id}/disable` | Disable plugin |

## Configuration

### Environment Variables

```bash
# Backend configuration
OKO_STORE_URL=http://store:8001/api/v1

# Store configuration
OKO_STORE_STORAGE_PATH=/app/plugins
OKO_STORE_MAX_PLUGIN_SIZE_MB=100
OKO_STORE_DEBUG=false
GITHUB_TOKEN=your_github_token  # For private repositories
```

### Docker Compose

The backend and store services are configured in `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      OKO_STORE_URL: http://store:8001/api/v1
    volumes:
      - oko-plugins-data:/app/backend/plugins
    depends_on:
      store:
        condition: service_healthy

  store:
    build:
      context: .
      dockerfile: docker/Dockerfile.plugin-store
    volumes:
      - oko-plugin-store-data:/app/plugins
```

## Plugin States

### Store Catalog Status

Store does not track runtime state of plugins in backend.
It only stores catalog metadata and plugin source files.

### Backend Plugin State

- **discovered**: Plugin found in `backend/plugins/` but not loaded
- **loading**: Plugin is being loaded
- **active**: Plugin is loaded and running
- **error**: Plugin failed to load
- **disabled**: Plugin is disabled

## Plugin Directory Structure

```
backend/plugins/           # Backend installation directory
├── my_plugin/            # Installed plugin
│   ├── __init__.py
│   ├── manifest.py
│   └── ui.yaml
└── another_plugin/

store/plugins/            # Store storage directory
├── plugins.json          # Plugin metadata registry
├── uploads/              # Uploaded plugin packages
│   ├── zip_20240101_120000/
│   │   ├── plugin.zip
│   │   └── extracted/
│   └── github_user_repo_20240101_120000/
│       └── extracted/
└── ...
```

## Usage Examples

### List Available Plugins in Store

```bash
curl http://localhost:8000/api/v1/store
```

Response:
```json
{
  "available": true,
  "plugins": [
    {
      "id": "abc123",
      "name": "my_plugin",
      "version": "1.0.0",
      "description": "My awesome plugin",
      "author": "John Doe",
      "source": "zip_upload",
      "manifest": {
        "name": "my_plugin",
        "version": "1.0.0",
        "capabilities": ["exec.my_plugin.action"]
      }
    }
  ],
  "total": 1
}
```

### Install Plugin from Store

```bash
curl -X POST http://localhost:8000/api/v1/store/abc123/install
```

Response:
```json
{
  "status": "installed",
  "plugin": {
    "id": "my_plugin",
    "name": "my_plugin",
    "version": "1.0.0",
    "state": "discovered",
    "scope": "external"
  },
  "message": "Plugin my_plugin installed successfully"
}
```

### Load Installed Plugin

```bash
curl -X POST http://localhost:8000/api/v1/plugins/my_plugin/load
```

### Uninstall Plugin

```bash
# First unload if active
curl -X POST http://localhost:8000/api/v1/plugins/my_plugin/unload

# Then uninstall from backend
curl -X POST http://localhost:8000/api/v1/store/my_plugin/uninstall
```

## Frontend Integration

### Current UI Integration (UiBlankLayout)

Store UI and plugin runtime pages are rendered in `UiBlankLayout` and must use current slot names.

#### Slots used by `/plugins` (control center)

- `sidebar-mid`: brand + left navigation + install actions
- `sidebar-bottom-indicators`: back action
- `header-tabs`: installed/store/settings tabs
- `drawer`: placeholder/control to enable header accordion
- `drawer-actions`: close action
- `canvas-main`: tab content

`UiBaseModal` dialogs are rendered outside `UiBlankLayout` root (not through a layout slot).

#### Slots used by `/plugins/:pluginId` (details page)

- `sidebar-mid`: plugin runtime header + back action
- `header-tabs`: page tab/title
- `canvas-main`: plugin manifest sections renderer

#### Important

- Use `content-label` prop for canvas aria label.
- Do not use legacy slot names (`app.sidebar.*`, `app.header.*`, `page.canvas.main`, `app.modals`).

### Legacy Generic Example (Reference Only)

```vue
<template>
  <div class="plugins-page">
    <h1>Plugin Store</h1>
    
    <div v-if="loading">Loading...</div>
    <div v-else>
      <div v-for="plugin in storePlugins" :key="plugin.id" class="plugin-card">
        <h3>{{ plugin.name }} v{{ plugin.version }}</h3>
        <p>{{ plugin.description }}</p>
        
        <div v-if="isInstalled(plugin.id)">
          <span class="badge">Installed</span>
          <button @click="unloadPlugin(plugin.id)" v-if="isActive(plugin.id)">
            Unload
          </button>
          <button @click="loadPlugin(plugin.id)" v-else>
            Load
          </button>
          <button @click="uninstallPlugin(plugin.id)">
            Uninstall
          </button>
        </div>
        <button v-else @click="installPlugin(plugin.id)">
          Install
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const storePlugins = ref([])
const installedPlugins = ref([])
const loading = ref(true)

const loadStorePlugins = async () => {
  const response = await api.get('/api/v1/store')
  storePlugins.value = response.data.plugins
}

const loadInstalledPlugins = async () => {
  const response = await api.get('/api/v1/plugins')
  installedPlugins.value = response.data.plugins
}

const installPlugin = async (pluginId) => {
  await api.post(`/api/v1/store/${pluginId}/install`)
  await loadInstalledPlugins()
}

const uninstallPlugin = async (pluginId) => {
  await api.post(`/api/v1/store/${pluginId}/uninstall`)
  await loadInstalledPlugins()
}

const loadPlugin = async (pluginId) => {
  await api.post(`/api/v1/plugins/${pluginId}/load`)
  await loadInstalledPlugins()
}

const unloadPlugin = async (pluginId) => {
  await api.post(`/api/v1/plugins/${pluginId}/unload`)
  await loadInstalledPlugins()
}

const isInstalled = (pluginId) => {
  return installedPlugins.value.some(p => p.id === pluginId)
}

const isActive = (pluginId) => {
  const plugin = installedPlugins.value.find(p => p.id === pluginId)
  return plugin?.state === 'active'
}

onMounted(async () => {
  await Promise.all([loadStorePlugins(), loadInstalledPlugins()])
  loading.value = false
})
</script>
```

## Error Handling

### Store Unavailable

If the store is unavailable, the backend will:
- Continue to function normally
- Show store as "unavailable" in UI
- Allow management of already installed plugins

### Installation Failures

Common failure scenarios:
- **Network error**: Store temporarily unavailable
- **Validation error**: Plugin manifest invalid
- **Disk space**: Insufficient space for plugin
- **Permission error**: Cannot write to plugins directory

## Security Considerations

1. **Plugin Validation**: All plugins are validated before installation
2. **Source Verification**: Plugins from GitHub use verified URLs
3. **File Size Limits**: Maximum plugin size prevents DoS
4. **Sandboxing**: Plugins run in isolated context (future enhancement)

## Troubleshooting

### Store Not Available

```bash
# Check store health
curl http://localhost:8001/api/v1/health

# Check store logs
docker-compose logs store
```

### Plugin Installation Fails

```bash
# Check backend logs
docker-compose logs backend

# Verify plugins directory permissions
docker-compose exec backend ls -la /app/plugins

# Check store has plugin
curl http://localhost:8001/api/v1/plugins/{plugin_id}
```

### Plugin Not Loading

```bash
# Check plugin structure
docker-compose exec backend ls -la /app/plugins/{plugin_name}

# Verify manifest.py exists
docker-compose exec backend cat /app/plugins/{plugin_name}/manifest.py

# Check backend logs for load errors
docker-compose logs backend | grep -i plugin
```

## Future Enhancements

- [ ] Plugin version management and updates
- [ ] Plugin dependency resolution
- [ ] Plugin signature verification
- [ ] Automatic plugin updates from GitHub
- [ ] Plugin rating and review system
- [ ] Plugin sandboxing for security
- [ ] Hot reload support

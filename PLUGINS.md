# Plugin System Documentation

## Overview

The OKO Dashboard plugin system provides real-time runtime discovery, loading, and management of plugins. Plugins can extend the dashboard with new features, pages, widgets, and API endpoints.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Plugin System                          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Scanner    │  │    Loader    │  │   Registry   │  │
│  │  Discovery   │  │   Runtime    │  │  Management  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Router    │  │    Service   │  │     API      │  │
│  │  Pages/Routes│  │  Lifecycle   │  │  Endpoints   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Plugin Structure

A plugin is a Python package with the following structure:

```
my_plugin/
├── __init__.py          # Package initialization
├── manifest.py          # Plugin metadata (name, version, capabilities)
├── ui.yaml              # UI configuration (optional)
├── plugin_manifest.py   # Plugin implementation (optional)
└── static/              # Static assets (optional)
    ├── css/
    └── js/
```

### Manifest (manifest.py)

```python
PLUGIN_NAME = "my_plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "My awesome plugin"
PLUGIN_AUTHOR = "Your Name"
PLUGIN_HOMEPAGE = "https://example.com"
PLUGIN_LICENSE = "MIT"
PLUGIN_TAGS = ("network", "scanner")
PLUGIN_CAPABILITIES = ("exec.my_plugin.action",)
```

### UI Configuration (ui.yaml)

```yaml
# Page configuration
has_page: true
page_path: /my-plugin
page_title: My Plugin
page_icon: radar

# Navigation
show_in_menu: true
menu_group: Tools
menu_order: 10

# Widgets
provides_widgets: true
widgets:
  - id: my_widget
    title: My Widget
    type: custom

# API
api_prefix: my-plugin

# Permissions
required_permissions:
  - actions.execute
```

## Plugin Lifecycle

### States

- **discovered**: Plugin found but not loaded
- **loading**: Plugin is being loaded
- **active**: Plugin is loaded and active
- **error**: Plugin failed to load
- **disabled**: Plugin is disabled

### Operations

- **load**: Load plugin into memory
- **unload**: Unload plugin from memory
- **reload**: Reload plugin (unload + load)
- **enable**: Enable disabled plugin
- **disable**: Disable plugin (unload + mark disabled)

## API Endpoints

### Plugin Management

```
GET    /api/v1/plugins              # List all plugins
GET    /api/v1/plugins/{id}         # Get plugin details
POST   /api/v1/plugins/{id}/load    # Load plugin
POST   /api/v1/plugins/{id}/unload  # Unload plugin
POST   /api/v1/plugins/{id}/reload  # Reload plugin
POST   /api/v1/plugins/{id}/enable  # Enable plugin
POST   /api/v1/plugins/{id}/disable # Disable plugin
GET    /api/v1/plugins/registry     # Get plugin registry
```

### Plugin Pages

```
GET    /plugins/{plugin-path}       # Plugin page (if has_page: true)
GET    /api/v1/plugins/{prefix}/*   # Plugin API routes
```

## Creating a Plugin

### Step 1: Create Plugin Directory

```bash
mkdir -p plugins/my_plugin
cd plugins/my_plugin
```

### Step 2: Create Manifest

```python
# manifest.py
PLUGIN_NAME = "my_plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "My awesome plugin"
```

### Step 3: Create UI Config

```yaml
# ui.yaml
has_page: true
page_path: /my-plugin
page_title: My Plugin
show_in_menu: true
```

### Step 4: Create Plugin Code

```python
# __init__.py
from fastapi import Request

PLUGIN_NAME = "my_plugin"
PLUGIN_VERSION = "1.0.0"

def setup(action_gateway=None, event_bus=None):
    """Called when plugin is loaded."""
    pass

def teardown():
    """Called when plugin is unloaded."""
    pass

def handle_page(request: Request) -> str:
    """Handle plugin page requests."""
    return "<h1>My Plugin</h1>"
```

## Autodiscover Plugin

The autodiscover plugin is the first built-in plugin that provides network scanning capabilities.

### Features

- Network host discovery
- Port scanning
- HTTP service probing
- Device type detection
- Hostname resolution
- MAC vendor lookup

### Access

- **Page**: `/plugins/autodiscover`
- **API**: `/api/v1/plugins/autodiscover/*`
- **Action**: `autodiscover.scan`

### Usage

```bash
# Start a scan via API
curl -X POST http://localhost:8000/api/v1/actions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "type": "autodiscover.scan",
    "capability": "exec.autodiscover.scan",
    "requested_at": "2024-01-01T00:00:00Z",
    "payload": {
      "cidrs": ["192.168.1.0/24"],
      "ports": [80, 443, 22],
      "include_http_services": true
    }
  }'
```

## Plugin Directories

Plugins are discovered in:

- `_tmp/` - Development plugins
- `plugins/` - Production plugins

## Security

Plugins require permissions to execute actions:

- `actions.execute` - Execute plugin actions
- `actions.history` - View action history
- `actions.registry` - View action registry

## Best Practices

1. **Manifest**: Always provide complete manifest information
2. **Error Handling**: Wrap plugin code in try-except blocks
3. **Cleanup**: Implement `teardown()` for resource cleanup
4. **Logging**: Use Python's logging module
5. **Versioning**: Follow semantic versioning
6. **Documentation**: Document all plugin capabilities

## Frontend Layout Contract (`UiBlankLayout`)

Plugin UI in frontend must integrate through the current `UiBlankLayout` API.
Legacy slot names like `app.sidebar.*`, `app.header.*`, `page.canvas.main`, `app.modals` are deprecated and should not be used.

### Supported props (commonly used by plugin pages)

- `emblem-src`
- `sidebar-hidden`
- `sidebar-particles-id`
- `content-label`
- `header-panel-initially-open`
- `header-panel-storage-key`

### Supported slots

- `sidebar-mid`
- `sidebar-bottom-indicators`
- `header-tabs`
- `drawer`
- `drawer-actions`
- `drawer-footer`
- `indicators`
- `canvas-main`
- `plugins`

### Plugin page mapping

- Plugin center (`/plugins`):
  - Sidebar content: `sidebar-mid`
  - Bottom actions/links: `sidebar-bottom-indicators`
  - Top tabs: `header-tabs`
  - Header action buttons: `drawer-actions` (requires `drawer` slot to render accordion)
  - Main content: `canvas-main`
  - Modal overlays: render outside `UiBlankLayout` (not a layout slot)

- Plugin details (`/plugins/:pluginId`):
  - Sidebar content: `sidebar-mid`
  - Top tabs/title: `header-tabs`
  - Main details renderer: `canvas-main`

## Troubleshooting

### Plugin Not Discovered

- Check plugin directory structure
- Ensure `__init__.py` exists
- Verify manifest.py has required fields

### Plugin Failed to Load

- Check error logs for details
- Verify dependencies are installed
- Ensure no import errors

### Page Not Accessible

- Verify `has_page: true` in UI config
- Check `page_path` is correct
- Ensure plugin is in `active` state

## Future Enhancements

- Remote plugin repository
- Plugin version management
- Plugin dependencies
- Hot reload support
- Plugin sandboxing
- Widget framework integration

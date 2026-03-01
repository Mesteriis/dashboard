# Store Service

FastAPI-based plugin storage and management service for the OKO Dashboard plugin system.

## Overview

The Store provides a centralized API for:
- Uploading plugins via ZIP files
- Importing plugins from GitHub repositories
- Managing plugin catalog entries
- Providing plugin metadata and manifests to the main dashboard application

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Store API                            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Upload ZIP  │  │ GitHub Import│  │   Registry   │  │
│  │  Endpoint    │  │  Endpoint    │  │   Service    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Storage    │  │   Metadata   │  │   Health     │  │
│  │   Service    │  │   Manager    │  │   Monitor    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Development

```bash
# Install dependencies
uv sync

# Run locally
cd store
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up -d store

# View logs
docker-compose logs -f store
```

## API Endpoints

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/info` | System information |

### Plugins

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/plugins` | List all plugins |
| GET | `/api/v1/plugins/{id}` | Get plugin details |
| POST | `/api/v1/plugins/upload/zip` | Upload plugin from ZIP |
| POST | `/api/v1/plugins/upload/github` | Import plugin from GitHub |
| DELETE | `/api/v1/plugins/{id}` | Delete plugin |
| GET | `/api/v1/plugins/{id}/path` | Get plugin file path |

## Usage Examples

### Upload Plugin via ZIP

```bash
curl -X POST http://localhost:8001/api/v1/plugins/upload/zip \
  -F "file=@my-plugin.zip"
```

Response:
```json
{
  "success": true,
  "plugin_id": "abc123",
  "message": "Plugin my_plugin uploaded successfully",
  "plugin": {
    "id": "abc123",
    "name": "my_plugin",
    "version": "1.0.0",
    "source": "zip_upload"
  }
}
```

### Import Plugin from GitHub

```bash
curl -X POST http://localhost:8001/api/v1/plugins/upload/github \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/my-plugin",
    "branch": "main"
  }'
```

### Import Plugin from GitHub Subdirectory

```bash
curl -X POST http://localhost:8001/api/v1/plugins/upload/github \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/my-repo",
    "branch": "main",
    "subdirectory": "plugins/my-plugin"
  }'
```

### List All Plugins

```bash
curl http://localhost:8001/api/v1/plugins
```

### Delete Plugin

```bash
curl -X DELETE http://localhost:8001/api/v1/plugins/{id}
```

## Plugin Structure

Plugins must follow the OKO plugin structure:

```
my-plugin/
├── __init__.py
├── manifest.py          # Required: Plugin metadata
├── ui.yaml              # Optional: UI configuration
└── plugin_manifest.py   # Optional: Plugin implementation
```

### manifest.py

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

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OKO_STORE_STORAGE_PATH` | `./plugins` | Plugin storage directory |
| `OKO_STORE_MAX_PLUGIN_SIZE_MB` | `100` | Maximum plugin file size (MB) |
| `OKO_STORE_DEBUG` | `false` | Enable debug mode |
| `OKO_STORE_API_KEY` | - | Optional API key for authentication |
| `GITHUB_TOKEN` | - | GitHub token for private repositories |

## Integration with Main Dashboard

The main dashboard can integrate with the Store via HTTP API:

```python
import httpx

STORE_URL = "http://store:8001/api/v1"

# List plugins
async def list_plugins():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{STORE_URL}/plugins")
        return response.json()

# Upload plugin
async def upload_plugin(zip_path: Path):
    async with httpx.AsyncClient() as client:
        with open(zip_path, "rb") as f:
            files = {"file": ("plugin.zip", f, "application/zip")}
            response = await client.post(f"{STORE_URL}/plugins/upload/zip", files=files)
            return response.json()

# Get plugin path for loading
async def get_plugin_path(plugin_id: str) -> Path | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{STORE_URL}/plugins/{plugin_id}/path")
        if response.status_code == 200:
            data = response.json()
            return Path(data["path"]) if data["exists"] else None
    return None
```

## Storage Layout

```
plugins/
├── plugins.json           # Plugin metadata registry
├── uploads/               # Uploaded plugin packages
│   ├── {plugin_id}/
│   │   ├── plugin.zip
│   │   └── extracted/
│   └── ...
```

## Health Check

```bash
curl http://localhost:8001/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "storage_path": "/app/plugins",
  "plugins_count": 5
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Security Considerations

1. **Plugin Validation**: All plugins are validated for proper manifest structure before being stored
2. **File Size Limits**: Configurable maximum plugin size to prevent DoS
3. **API Authentication**: Optional API key support for production deployments
4. **GitHub Rate Limits**: Use `GITHUB_TOKEN` for higher rate limits when importing from GitHub

## Troubleshooting

### Plugin Upload Fails

- Check file size is within limits
- Verify ZIP contains valid plugin structure
- Ensure `manifest.py` exists with required fields

### GitHub Import Fails

- Verify repository URL is correct
- Check branch name exists
- For private repos, ensure `GITHUB_TOKEN` is set
- Check subdirectory path if specified

### Storage Issues

- Verify storage directory has write permissions
- Check disk space availability
- Review logs for detailed error messages

## Future Enhancements

- [ ] Plugin version management
- [ ] Plugin dependency resolution
- [ ] Remote plugin repository support
- [ ] Plugin signature verification
- [ ] Automatic plugin updates from GitHub
- [ ] Plugin rating and review system
- [ ] Search and discovery features

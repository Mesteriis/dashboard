"""
Autodiscover Plugin - Network Scanner for Dashboard

This plugin provides network scanning capabilities, discovering hosts,
services, and HTTP metadata on your local network.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse

# Import autodiscover functionality
from .manifest import (
    ACTIONS,
    ACTION_SCAN,
    CAPABILITY_SCAN,
    EVENTS,
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_FAILED,
    EVENT_SCAN_PROGRESS,
    EVENT_SCAN_STARTED,
    PLUGIN_NAME,
    PLUGIN_VERSION,
)
from .registry import register_autodiscover_actions

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_NAME = "autodiscover"
PLUGIN_VERSION = "2.0.0"
PLUGIN_DESCRIPTION = "Network scanner for discovering hosts, services, and HTTP metadata on your local network"
PLUGIN_AUTHOR = "OKO Dashboard Team"
PLUGIN_HOMEPAGE = "https://github.com/oko-dashboard/autodiscover"
PLUGIN_LICENSE = "MIT"
PLUGIN_TAGS = ("network", "scanner", "discovery", "lan")
PLUGIN_CAPABILITIES = (CAPABILITY_SCAN,)

# Plugin manifest for the plugin system
PLUGIN_MANIFEST = {
    "name": PLUGIN_NAME,
    "version": PLUGIN_VERSION,
    "description": PLUGIN_DESCRIPTION,
    "author": PLUGIN_AUTHOR,
    "homepage": PLUGIN_HOMEPAGE,
    "license": PLUGIN_LICENSE,
    "tags": PLUGIN_TAGS,
    "capabilities": PLUGIN_CAPABILITIES,
    "actions": tuple(dict(action) for action in ACTIONS),
    "events": tuple(dict(event) for event in EVENTS),
}

# UI configuration for the plugin
PLUGIN_UI_CONFIG = {
    "has_page": True,
    "page_path": "/autodiscover",
    "page_title": "Network Discovery",
    "page_icon": "radar",
    "show_in_menu": True,
    "menu_group": "Tools",
    "menu_order": 10,
    "provides_widgets": True,
    "widgets": (
        {
            "id": "network_scanner",
            "title": "Network Scanner",
            "type": "scanner",
            "description": "Scan your local network for devices and services",
        },
    ),
    "api_prefix": "autodiscover",
    "required_permissions": ("actions.execute", "actions.history"),
}

# Global state
_plugin_state: dict[str, Any] = {}
_action_gateway = None
_event_bus = None


def setup(
    action_gateway: Any | None = None,
    event_bus: Any | None = None,
) -> None:
    """
    Initialize the autodiscover plugin.
    
    This is called when the plugin is loaded by the plugin system.
    Register actions and event handlers.
    """
    global _action_gateway, _event_bus, _plugin_state
    
    logger.info(f"Setting up autodiscover plugin v{PLUGIN_VERSION}")
    
    _action_gateway = action_gateway
    _event_bus = event_bus
    _plugin_state = {
        "last_scan": None,
        "scan_history": [],
        "discovered_hosts": [],
    }
    
    # Register actions with the gateway
    if action_gateway and event_bus:
        try:
            register_autodiscover_actions(
                action_gateway,
                event_bus=event_bus,
            )
            logger.info("Autodiscover actions registered successfully")
        except Exception as exc:
            logger.exception(f"Failed to register autodiscover actions: {exc}")
            raise


def teardown() -> None:
    """
    Cleanup when plugin is unloaded.
    """
    global _action_gateway, _event_bus, _plugin_state
    
    logger.info("Tearing down autodiscover plugin")
    
    _action_gateway = None
    _event_bus = None
    _plugin_state = {}


def handle_page(request: Request) -> str:
    """
    Handle plugin page requests.
    Returns HTML content for the autodiscover plugin page.
    """
    from datetime import UTC, datetime
    
    # Get scan history from state
    last_scan = _plugin_state.get("last_scan")
    discovered_hosts = _plugin_state.get("discovered_hosts", [])
    
    # Format last scan time
    last_scan_str = "Never"
    if last_scan:
        if isinstance(last_scan, datetime):
            last_scan_str = last_scan.strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_scan_str = str(last_scan)
    
    # Generate hosts table
    hosts_rows = ""
    for host in discovered_hosts[:20]:  # Show last 20 hosts
        ip = host.get("ip", "Unknown")
        hostname = host.get("hostname", "N/A")
        device_type = host.get("device_type", "Unknown")
        ports = len(host.get("open_ports", []))
        hosts_rows += f"""
        <tr>
            <td>{ip}</td>
            <td>{hostname}</td>
            <td>{device_type}</td>
            <td>{ports} ports</td>
        </tr>
        """
    
    if not hosts_rows:
        hosts_rows = """
        <tr>
            <td colspan="4" style="text-align: center; color: var(--text-secondary);">
                No hosts discovered yet. Start a scan to discover devices on your network.
            </td>
        </tr>
        """
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Discovery - Autodiscover</title>
    <style>
        :root {{
            --bg-primary: #050a0f;
            --bg-card: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.08);
            --text-primary: #ffffff;
            --text-secondary: rgba(255,255,255,0.7);
            --accent: #2dd4bf;
            --accent-hover: #14b8a6;
            --danger: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .title-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .icon {{ 
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--accent), #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .title {{ font-size: 2rem; font-weight: 600; }}
        .version {{
            background: var(--bg-card);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.5rem;
        }}
        .card h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        .stat {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
        }}
        .stat:last-child {{ border-bottom: none; }}
        .stat-label {{ color: var(--text-secondary); }}
        .stat-value {{ font-weight: 600; color: var(--accent); }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            font-size: 1rem;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--accent), var(--accent-hover));
            color: #000;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(45, 212, 191, 0.3);
        }}
        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
        .scan-controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .table-container {{
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        tr:hover {{
            background: rgba(255,255,255,0.02);
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .badge-device {{
            background: rgba(59, 130, 246, 0.1);
            color: #60a5fa;
        }}
        .progress-bar {{
            height: 4px;
            background: var(--border);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 1rem;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #3b82f6);
            width: 0%;
            transition: width 0.3s;
        }}
        .status-text {{
            margin-top: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-section">
                <span class="icon">📡</span>
                <div>
                    <h1 class="title">Network Discovery</h1>
                    <span class="version">v{PLUGIN_VERSION}</span>
                </div>
            </div>
            <button class="btn btn-primary" id="scanBtn" onclick="startScan()">
                <span>🔍</span>
                Start Scan
            </button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>Scan Status</h2>
                <div class="stat">
                    <span class="stat-label">Last Scan</span>
                    <span class="stat-value">{last_scan_str}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Discovered Hosts</span>
                    <span class="stat-value" id="hostsCount">{len(discovered_hosts)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Plugin Status</span>
                    <span class="stat-value" style="color: var(--accent);">● Active</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressBar"></div>
                </div>
                <div class="status-text" id="statusText">Ready to scan</div>
            </div>
            
            <div class="card">
                <h2>Quick Actions</h2>
                <div class="stat">
                    <span class="stat-label">Quick Scan</span>
                    <button class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.875rem;" onclick="startScan('quick')">
                        Fast
                    </button>
                </div>
                <div class="stat">
                    <span class="stat-label">Full Scan</span>
                    <button class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.875rem;" onclick="startScan('full')">
                        Deep
                    </button>
                </div>
                <div class="stat">
                    <span class="stat-label">Export Results</span>
                    <button class="btn" style="padding: 0.5rem 1rem; font-size: 0.875rem; background: var(--bg-card);" onclick="exportResults()">
                        Download
                    </button>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Discovered Hosts</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Hostname</th>
                            <th>Device Type</th>
                            <th>Open Ports</th>
                        </tr>
                    </thead>
                    <tbody>
                        {hosts_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let isScanning = false;
        
        async function startScan(type = 'quick') {{
            if (isScanning) return;
            
            const btn = document.getElementById('scanBtn');
            const progress = document.getElementById('progressBar');
            const status = document.getElementById('statusText');
            
            isScanning = true;
            btn.disabled = true;
            btn.innerHTML = '<span>⏳</span> Scanning...';
            progress.style.width = '0%';
            status.textContent = 'Initializing scan...';
            
            try {{
                const response = await fetch('/api/v1/actions/execute', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        type: 'autodiscover.scan',
                        capability: 'exec.autodiscover.scan',
                        requested_at: new Date().toISOString(),
                        dry_run: false,
                        payload: {{
                            scan_type: type,
                            include_dashboard_items: true,
                            include_http_services: true,
                            resolve_hostnames: true,
                            resolve_macs: true,
                        }}
                    }})
                }});
                
                const result = await response.json();
                
                if (result.status === 'succeeded') {{
                    status.textContent = 'Scan completed!';
                    progress.style.width = '100%';
                    // Reload page to show results
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    throw new Error(result.error || 'Scan failed');
                }}
            }} catch (error) {{
                status.textContent = 'Scan failed: ' + error.message;
                progress.style.width = '0%';
            }} finally {{
                isScanning = false;
                btn.disabled = false;
                btn.innerHTML = '<span>🔍</span> Start Scan';
            }}
        }}
        
        function exportResults() {{
            alert('Export functionality coming soon!');
        }}
    </script>
</body>
</html>
"""


# API router for plugin-specific endpoints
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/status")
async def get_scan_status() -> dict[str, Any]:
    """Get current scan status."""
    return {
        "plugin": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "state": "active",
        "last_scan": _plugin_state.get("last_scan"),
        "discovered_hosts_count": len(_plugin_state.get("discovered_hosts", [])),
    }


@api_router.get("/hosts")
async def get_discovered_hosts(limit: int = 100) -> dict[str, Any]:
    """Get list of discovered hosts."""
    hosts = _plugin_state.get("discovered_hosts", [])[:limit]
    return {
        "plugin": PLUGIN_NAME,
        "hosts": hosts,
        "total": len(hosts),
    }


@api_router.post("/scan")
async def trigger_scan(scan_type: str = "quick") -> dict[str, Any]:
    """Trigger a network scan."""
    # This would integrate with the action gateway
    return {
        "status": "scan_initiated",
        "scan_type": scan_type,
        "message": "Scan started. Check action history for results.",
    }


__all__ = [
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "PLUGIN_MANIFEST",
    "PLUGIN_UI_CONFIG",
    "setup",
    "teardown",
    "handle_page",
    "api_router",
]

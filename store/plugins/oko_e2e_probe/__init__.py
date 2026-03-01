from fastapi import Request

PLUGIN_NAME = "oko_e2e_probe"
PLUGIN_VERSION = "0.1.1"
PLUGIN_DESCRIPTION = "E2E probe plugin flat"
PLUGIN_AUTHOR = "codex"
PLUGIN_CAPABILITIES = ("exec.oko_e2e_probe.ping",)


def setup() -> None:
    pass


def teardown() -> None:
    pass


def handle_page(request: Request) -> str:
    return "<h1>OKO E2E Plugin Page</h1><p>runtime watcher hot-reload ok</p>"

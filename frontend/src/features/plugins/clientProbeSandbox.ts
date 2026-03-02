interface RunClientProbeOptions {
  script: string;
  context?: Record<string, unknown>;
  timeoutMs?: number;
}

const CHANNEL = "oko-client-probe-v1";

function toMessage(error: unknown): string {
  if (error instanceof Error) return error.message || "Client probe failed";
  return String(error || "Client probe failed");
}

function createSandboxSrcdoc(): string {
  return `<!doctype html><html><head><meta charset="utf-8"></head><body><script>
const CHANNEL = "${CHANNEL}";
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;

window.addEventListener("message", async (event) => {
  const data = event && event.data ? event.data : {};
  if (data.channel !== CHANNEL || data.type !== "run") return;
  const runId = String(data.runId || "");
  if (!runId) return;
  try {
    const script = String(data.script || "");
    const ctx = Object.freeze((data.context && typeof data.context === "object") ? data.context : {});
    const fn = new AsyncFunction("ctx", script);
    const payload = await fn(ctx);
    parent.postMessage({ channel: CHANNEL, type: "result", runId, payload }, "*");
  } catch (error) {
    parent.postMessage(
      {
        channel: CHANNEL,
        type: "result",
        runId,
        error: error instanceof Error ? error.message : String(error || "Probe failed"),
      },
      "*",
    );
  }
});

parent.postMessage({ channel: CHANNEL, type: "ready" }, "*");
<\/script></body></html>`;
}

export function runClientProbeScript(
  options: RunClientProbeOptions,
): Promise<unknown> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.reject(new Error("Client probe is only available in browser"));
  }

  const script = String(options.script || "").trim();
  if (!script) {
    return Promise.reject(new Error("Client probe script is empty"));
  }

  const runId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const timeoutMs = Math.max(1000, Number(options.timeoutMs || 5000));

  return new Promise((resolve, reject) => {
    const iframe = document.createElement("iframe");
    iframe.setAttribute("sandbox", "allow-scripts");
    iframe.setAttribute("title", "Plugin client probe sandbox");
    iframe.style.position = "fixed";
    iframe.style.width = "1px";
    iframe.style.height = "1px";
    iframe.style.opacity = "0";
    iframe.style.pointerEvents = "none";
    iframe.style.left = "-10000px";
    iframe.style.top = "-10000px";
    iframe.srcdoc = createSandboxSrcdoc();

    let done = false;
    let timer = 0;

    const cleanup = (): void => {
      if (done) return;
      done = true;
      if (timer) window.clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
    };

    const fail = (error: unknown): void => {
      cleanup();
      reject(new Error(toMessage(error)));
    };

    const onMessage = (event: MessageEvent): void => {
      if (event.source !== iframe.contentWindow) return;
      const data = (event.data || {}) as Record<string, unknown>;
      if (data.channel !== CHANNEL) return;
      const type = String(data.type || "");

      if (type === "ready") {
        iframe.contentWindow?.postMessage(
          {
            channel: CHANNEL,
            type: "run",
            runId,
            script,
            context: options.context || {},
          },
          "*",
        );
        return;
      }

      if (type !== "result") return;
      if (String(data.runId || "") !== runId) return;
      if (typeof data.error === "string" && data.error.trim()) {
        fail(data.error);
        return;
      }
      const payload = (data as { payload?: unknown }).payload;
      cleanup();
      resolve(payload);
    };

    window.addEventListener("message", onMessage);
    document.body.appendChild(iframe);
    timer = window.setTimeout(() => {
      fail(`Client probe timeout after ${timeoutMs}ms`);
    }, timeoutMs);
  });
}


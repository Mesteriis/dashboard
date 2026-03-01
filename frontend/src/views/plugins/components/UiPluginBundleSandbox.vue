<template>
  <section class="plugin-bundle-sandbox panel">
    <section v-if="status === 'loading'" class="plugin-bundle-state">
      Loading custom bundle...
    </section>
    <section v-else-if="status === 'error'" class="plugin-bundle-state plugin-bundle-error">
      {{ errorMessage || "Failed to load custom bundle." }}
    </section>
    <iframe
      ref="iframeRef"
      class="plugin-bundle-frame"
      title="Plugin custom bundle sandbox"
      :sandbox="sandboxAttr"
      :srcdoc="srcdoc"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { requestJson } from "@/features/services/requestJson";
import type { PluginPageManifestV1 } from "@/features/plugins/manifest";

type BundleStatus = "loading" | "ready" | "error";

const props = defineProps<{
  pluginId: string;
  manifest: PluginPageManifestV1;
  entry: string;
  sandboxEnabled: boolean;
}>();

const emit = defineEmits<{
  failed: [message: string];
}>();

const iframeRef = ref<HTMLIFrameElement | null>(null);
const status = ref<BundleStatus>("loading");
const errorMessage = ref("");
const pendingRequests = new Map<string, AbortController>();

const sandboxAttr = computed(() =>
  props.sandboxEnabled
    ? "allow-scripts allow-forms allow-downloads"
    : "allow-scripts allow-forms allow-downloads allow-same-origin",
);

const srcdoc = computed(() => {
  const escapedManifest = JSON.stringify(props.manifest).replace(/</g, "\\u003c");
  const escapedEntry = JSON.stringify(props.entry);
  return `<!doctype html><html><head><meta charset="utf-8"></head><body><div id="app"></div><script type="module">
const manifest = ${escapedManifest};
const entry = ${escapedEntry};
const pending = new Map();
window.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.channel !== "oko-plugin-bridge" || data.type !== "response") return;
  const resolver = pending.get(data.id);
  if (!resolver) return;
  pending.delete(data.id);
  if (data.error) {
    resolver.reject(new Error(data.error));
    return;
  }
  resolver.resolve(data.payload);
});
const bridge = {
  request(method, path, body) {
    return new Promise((resolve, reject) => {
      const id = String(Date.now()) + "-" + Math.random().toString(16).slice(2);
      pending.set(id, { resolve, reject });
      parent.postMessage({
        channel: "oko-plugin-bridge",
        type: "request",
        id,
        payload: { method, path, body }
      }, "*");
    });
  }
};
(async () => {
  try {
    const module = await import(entry);
    if (!module || typeof module.mount !== "function") {
      throw new Error("Custom bundle must export mount(ctx)");
    }
    await module.mount({
      container: document.getElementById("app"),
      bridge,
      manifest
    });
    parent.postMessage({ channel: "oko-plugin-bridge", type: "bundle-ready" }, "*");
  } catch (error) {
    parent.postMessage({
      channel: "oko-plugin-bridge",
      type: "bundle-error",
      error: error instanceof Error ? error.message : String(error)
    }, "*");
  }
})();
<\\/script></body></html>`;
});

function isAllowedPath(path: string): boolean {
  return path.startsWith("/api/v1/");
}

async function onBridgeMessage(event: MessageEvent): Promise<void> {
  if (event.source !== iframeRef.value?.contentWindow) return;
  const data = event.data as Record<string, unknown>;
  if (!data || data.channel !== "oko-plugin-bridge") return;

  if (data.type === "bundle-ready") {
    status.value = "ready";
    return;
  }

  if (data.type === "bundle-error") {
    status.value = "error";
    errorMessage.value = String(data.error || "Unknown bundle error");
    emit("failed", errorMessage.value);
    return;
  }

  if (data.type !== "request") return;
  const requestId = String(data.id || "").trim();
  const payload = (data.payload || {}) as Record<string, unknown>;
  const method = String(payload.method || "GET").toUpperCase();
  const path = String(payload.path || "").trim();
  const body = payload.body;

  if (!requestId || !path || !isAllowedPath(path)) {
    iframeRef.value?.contentWindow?.postMessage(
      {
        channel: "oko-plugin-bridge",
        type: "response",
        id: requestId,
        error: "Blocked by sandbox policy",
      },
      "*",
    );
    return;
  }

  const controller = new AbortController();
  pendingRequests.set(requestId, controller);
  try {
    const response = await requestJson(path, {
      method,
      signal: controller.signal,
      ...(method === "POST"
        ? {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {}),
          }
        : {}),
    });
    iframeRef.value?.contentWindow?.postMessage(
      {
        channel: "oko-plugin-bridge",
        type: "response",
        id: requestId,
        payload: response,
      },
      "*",
    );
  } catch (error: unknown) {
    iframeRef.value?.contentWindow?.postMessage(
      {
        channel: "oko-plugin-bridge",
        type: "response",
        id: requestId,
        error: error instanceof Error ? error.message : "Request failed",
      },
      "*",
    );
  } finally {
    pendingRequests.delete(requestId);
  }
}

onMounted(() => {
  window.addEventListener("message", onBridgeMessage);
});

onBeforeUnmount(() => {
  window.removeEventListener("message", onBridgeMessage);
  for (const controller of pendingRequests.values()) {
    controller.abort();
  }
  pendingRequests.clear();
});
</script>

<style scoped>
.plugin-bundle-sandbox {
  padding: 12px;
}

.plugin-bundle-state {
  margin-bottom: 10px;
  color: rgba(186, 206, 229, 0.85);
}

.plugin-bundle-error {
  color: rgba(248, 170, 170, 0.92);
}

.plugin-bundle-frame {
  width: 100%;
  min-height: 520px;
  border: 1px solid rgba(104, 138, 171, 0.32);
  border-radius: var(--ui-radius);
  background: rgba(8, 17, 28, 0.72);
}
</style>

<template>
  <div class="shell" :class="{ 'shell-desktop': desktopShell }">
    <div
      v-if="desktopShell"
      class="desktop-window-drag-strip"
      data-tauri-drag-region
      aria-hidden="true"
    ></div>

    <RouterView />

    <div v-if="isPleiadOverlayVisible" class="pleiad-overlay-backdrop">
      <PleiadExperience :mode="pleiadOverlayMode" @close="handleCloseOverlay" />
    </div>

    <section
      v-if="apiErrorNotice.message"
      class="api-error-toast"
      role="status"
      aria-live="polite"
    >
      <header>
        <strong>API error</strong>
        <button
          type="button"
          class="api-error-toast-close"
          aria-label="Dismiss API error message"
          @click="clearApiErrorNotice"
        >
          Close
        </button>
      </header>
      <p>{{ apiErrorNotice.message }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import PleiadExperience from "@/views/overlays/pleiad/PleiadExperience.vue";
import { useIdleScreensaver } from "@/features/composables/useIdleScreensaver";
import { closeOverlay, openPleiadOverlay } from "@/app/navigation/nav";
import { isDesktopShell } from "@/features/services/desktopRuntime";
import { EVENT_API_ERROR, onOkoEvent } from "@/features/services/events";
import {
  connectOkoSseStream,
  type OkoSseStream,
} from "@/features/services/eventStream";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const route = useRoute();
const dashboard = useDashboardStore();
const {
  closeCommandPalette,
  commandPaletteOpen,
  setUiRouteScope,
  toggleCommandPalette,
} = dashboard;

const desktopShell = isDesktopShell();
const apiErrorNotice = ref<{ message: string }>({ message: "" });

const isPleiadOverlayVisible = computed(
  () => String(route.query.overlay || "") === "pleiad",
);
const pleiadOverlayMode = computed<"route" | "screensaver">(() =>
  String(route.query.mode || "") === "screensaver" ? "screensaver" : "route",
);
const isDashboardRoute = computed(
  () => route.path === "/" || route.path === "/settings",
);
const isImmersiveRoute = computed(() => isPleiadOverlayVisible.value);

watch(
  () => route.path,
  (path) => {
    setUiRouteScope(path);
  },
  { immediate: true },
);

// ── SSE ────────────────────────────────────────────────────────────────────

let sseStream: OkoSseStream | null = null;

function connectSse(): void {
  sseStream?.close();
  sseStream = connectOkoSseStream({
    path: "/api/v1/events/stream",
    onEvent: () => {},
    onError: () => {
      // при обрыве переподключаемся через 3 с
      window.setTimeout(connectSse, 3000);
    },
  });
}

// ── API-error toast ────────────────────────────────────────────────────────

let apiErrorNoticeTimerId: number | null = null;
let removeApiErrorListener: () => void = () => {};

function clearApiErrorNotice(): void {
  apiErrorNotice.value.message = "";
  if (!apiErrorNoticeTimerId) return;
  window.clearTimeout(apiErrorNoticeTimerId);
  apiErrorNoticeTimerId = null;
}

function handleApiError(event: CustomEvent<{ message?: string }>): void {
  const message = String(event?.detail?.message || "").trim();
  if (!message) return;
  apiErrorNotice.value.message = message;
  if (apiErrorNoticeTimerId) window.clearTimeout(apiErrorNoticeTimerId);
  apiErrorNoticeTimerId = window.setTimeout(() => {
    apiErrorNoticeTimerId = null;
    apiErrorNotice.value.message = "";
  }, 6400);
}

// ── Screensaver ────────────────────────────────────────────────────────────

useIdleScreensaver({
  timeoutMs: 10 * 60 * 1000,
  onIdle: () => {
    if (isImmersiveRoute.value) return;
    if (isPleiadOverlayVisible.value) return;
    void openPleiadOverlay("screensaver");
  },
  onActive: () => {
    if (!isPleiadOverlayVisible.value) return;
    if (pleiadOverlayMode.value !== "screensaver") return;
    void closeOverlay();
  },
});

function handleCloseOverlay(): void {
  void closeOverlay();
}

// ── Keyboard shortcuts ─────────────────────────────────────────────────────

function handleGlobalShortcut(event: KeyboardEvent): void {
  if (event.key === "Escape" && isPleiadOverlayVisible.value) {
    event.preventDefault();
    void closeOverlay();
    return;
  }

  if (event.key === "Escape" && commandPaletteOpen.value) {
    event.preventDefault();
    closeCommandPalette();
    return;
  }

  const isSearchShortcut =
    (event.metaKey || event.ctrlKey) &&
    !event.altKey &&
    !event.shiftKey &&
    event.key.toLowerCase() === "k";

  if (isSearchShortcut) {
    event.preventDefault();
    if (!isDashboardRoute.value || isPleiadOverlayVisible.value) return;
    toggleCommandPalette();
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
  connectSse();
  window.addEventListener("keydown", handleGlobalShortcut);
  removeApiErrorListener = onOkoEvent(EVENT_API_ERROR, handleApiError);
});

onBeforeUnmount(() => {
  sseStream?.close();
  sseStream = null;
  if (apiErrorNoticeTimerId) {
    window.clearTimeout(apiErrorNoticeTimerId);
    apiErrorNoticeTimerId = null;
  }
  window.removeEventListener("keydown", handleGlobalShortcut);
  removeApiErrorListener();
  removeApiErrorListener = () => {};
});
</script>

<style scoped>
.api-error-toast {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 62;
  width: min(440px, calc(100vw - 32px));
  border: 1px solid rgba(203, 79, 79, 0.34);
  border-radius: var(--ui-radius);
  background: rgba(19, 29, 44, 0.95);
  color: #f3f7ff;
  box-shadow: 0 12px 24px rgba(6, 10, 19, 0.32);
  padding: 12px 14px 13px;
}

.api-error-toast header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.api-error-toast strong {
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #ffabb0;
}

.api-error-toast p {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: rgba(231, 239, 255, 0.93);
}

.api-error-toast-close {
  appearance: none;
  border: 1px solid rgba(163, 184, 214, 0.34);
  border-radius: 999px;
  background: rgba(11, 18, 33, 0.62);
  color: rgba(233, 240, 253, 0.95);
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  padding: 6px 10px;
  cursor: pointer;
}
</style>

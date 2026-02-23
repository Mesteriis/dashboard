<template>
  <main
    class="page"
    :class="{
      'indicator-open': Boolean(activeIndicatorWidget),
      'page--lan': isLanPage && !activeIndicatorWidget,
      'page--split-scroll': Boolean(activePage) && !loadingConfig && !configError,
    }"
  >
    <section v-if="loadingConfig" class="panel status-panel">
      <h2>Загрузка конфигурации...</h2>
      <p class="subtitle">Получаем dashboard-модель из backend.</p>
    </section>

    <section v-else-if="configError" class="panel status-panel error-state">
      <h2>Ошибка загрузки конфигурации</h2>
      <p class="subtitle">{{ configError }}</p>
      <button class="ghost" type="button" @click="loadConfig">Повторить</button>
    </section>

    <template v-else-if="activePage">
      <section
        v-if="activeIndicatorWidget"
        class="page-right-bottom page-motion-zone"
      >
        <IndicatorTabPanel />
      </section>

      <template v-else>
        <section v-if="isLanPage" class="lan-workspace-backdrop">
          <section class="lan-workspace-shell">
            <section class="page-right-top">
              <LanHeroPanel />
            </section>

            <section class="page-right-bottom page-motion-zone">
              <LanPageView />
            </section>
          </section>
        </section>

        <section v-else class="page-right-shell">
          <section class="page-right-top">
            <ServicesHeroPanel />
          </section>

          <section class="page-right-bottom page-motion-zone">
            <ServicesGroupsPanel />
          </section>
        </section>
      </template>
    </template>

    <section v-else class="panel status-panel">
      <h2>Нет доступных страниц</h2>
      <p class="subtitle">Проверьте `layout.pages` в конфигурации панели.</p>
    </section>
  </main>

  <section
    v-if="showConfigErrorPopup"
    class="system-popup-backdrop"
    @click.self="dismissConfigErrorPopup"
  >
    <div
      class="system-popup"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="config-error-popup-title"
    >
      <h3 id="config-error-popup-title">{{ configErrorPopup.title }}</h3>
      <p>{{ configErrorPopup.message }}</p>
      <p class="system-popup-hint">{{ configErrorPopup.hint }}</p>
      <p
        v-if="configErrorPopup.details"
        class="system-popup-details"
        :title="configErrorPopup.details"
      >
        {{ configErrorPopup.details }}
      </p>
      <div class="system-popup-actions">
        <button
          class="system-popup-primary"
          type="button"
          @click="retryLoadFromPopup"
        >
          Повторить
        </button>
        <button class="ghost" type="button" @click="dismissConfigErrorPopup">
          Закрыть
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from "vue";
import LanHeroPanel from "../components/main/LanHeroPanel.vue";
import ServicesGroupsPanel from "../components/main/ServicesGroupsPanel.vue";
import ServicesHeroPanel from "../components/main/ServicesHeroPanel.vue";
import { useDashboardStore } from "../stores/dashboardStore.js";

const IndicatorTabPanel = defineAsyncComponent(
  () => import("../components/main/IndicatorTabPanel.vue"),
);
const LanPageView = defineAsyncComponent(
  () => import("../components/main/LanPageView.vue"),
);

const dashboard = useDashboardStore();
const {
  activePage,
  activeIndicatorWidget,
  loadingConfig,
  configError,
  isLanPage,
  loadConfig,
} = dashboard;

const dismissedConfigError = ref("");
const popupOpen = ref(false);

const configErrorPopup = computed(() => {
  const rawError = String(configError.value || "").trim();
  const normalized = rawError.toLowerCase();
  const isBackendConnectionError =
    normalized.includes("request failed: 500") ||
    normalized.includes("failed to fetch") ||
    normalized.includes("networkerror") ||
    normalized.includes("ecconnrefused") ||
    normalized.includes("не удалось связаться с backend") ||
    normalized.includes("не удалось подключиться к backend");

  if (isBackendConnectionError) {
    return {
      title: "Нет соединения с backend",
      message: "Не получилось загрузить конфигурацию панели.",
      hint: "Проверьте, что backend запущен на http://127.0.0.1:8000.",
      details: "После запуска backend нажмите «Повторить».",
    };
  }

  return {
    title: "Ошибка загрузки",
    message:
      rawError || "Не удалось загрузить dashboard-конфигурацию.",
    hint: "Исправьте проблему и повторите запрос.",
    details: "",
  };
});

const showConfigErrorPopup = computed(
  () => popupOpen.value && Boolean(configError.value),
);

watch(
  () => String(configError.value || "").trim(),
  (nextError) => {
    if (!nextError) {
      popupOpen.value = false;
      dismissedConfigError.value = "";
      return;
    }

    if (dismissedConfigError.value !== nextError) {
      popupOpen.value = true;
    }
  },
  { immediate: true },
);

function dismissConfigErrorPopup() {
  dismissedConfigError.value = String(configError.value || "").trim();
  popupOpen.value = false;
}

async function retryLoadFromPopup() {
  dismissedConfigError.value = "";
  popupOpen.value = false;
  await loadConfig();
}
</script>

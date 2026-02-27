<template>
  <main
    class="page"
    :class="{
      'page--embedded': hideHero,
      'indicator-open': Boolean(activeIndicatorWidget),
      'page--split-scroll':
        Boolean(activePage) && !loadingConfig && !configError,
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
        <UiIndicatorTabPanelFacade />
      </section>

      <section v-else-if="hideHero" class="page-right-bottom page-motion-zone">
        <UiServicesGroupsPanelFacade />
      </section>

      <section v-else class="page-right-shell">
        <section class="page-right-top">
          <UiServicesHeroPanelFacade />
        </section>

        <section class="page-right-bottom page-motion-zone">
          <UiServicesGroupsPanelFacade />
        </section>
      </section>
    </template>

    <section v-else class="panel status-panel">
      <h2>Панель не настроена</h2>
      <p class="subtitle">
        Создайте новую панель или импортируйте `dashboard.yaml`.
      </p>
    </section>
  </main>

  <UiBootstrapDashboardModalFacade
    :open="showBootstrapModal"
    :creating="creatingInitialDashboard"
    :importing="importingInitialDashboard"
    :error="bootstrapModalError"
    @create="createInitialDashboard"
    @import-yaml="importInitialDashboard"
  />

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

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from "vue";
import UiBootstrapDashboardModalFacade from "@/views/dashboard/facades/UiBootstrapDashboardModalFacade.vue";
import UiServicesGroupsPanelFacade from "@/views/dashboard/facades/UiServicesGroupsPanelFacade.vue";
import UiServicesHeroPanelFacade from "@/views/dashboard/facades/UiServicesHeroPanelFacade.vue";
import { restoreDashboardConfig } from "@/features/services/dashboardApi";
import { useDashboardStore } from "@/features/stores/dashboardStore";

withDefaults(
  defineProps<{
    hideHero?: boolean;
  }>(),
  {
    hideHero: false,
  },
);

const UiIndicatorTabPanelFacade = defineAsyncComponent(
  () => import("@/views/dashboard/facades/UiIndicatorTabPanelFacade.vue"),
);

const dashboard = useDashboardStore();
const {
  activePage,
  activeIndicatorWidget,
  loadingConfig,
  configError,
  bootstrapInitialDashboard,
  loadConfig,
  saveError,
} = dashboard;

const dismissedConfigError = ref("");
const popupOpen = ref(false);
const creatingInitialDashboard = ref(false);
const importingInitialDashboard = ref(false);
const bootstrapModalError = ref("");
const showBootstrapModal = computed(
  () => !loadingConfig.value && !configError.value && !activePage.value,
);

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
    message: rawError || "Не удалось загрузить dashboard-конфигурацию.",
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

function resolveErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

async function createInitialDashboard() {
  if (creatingInitialDashboard.value || importingInitialDashboard.value) return;
  creatingInitialDashboard.value = true;
  bootstrapModalError.value = "";

  try {
    const created = await bootstrapInitialDashboard();
    if (!created && !activePage.value) {
      bootstrapModalError.value =
        "Не удалось создать стартовую страницу. Проверьте конфигурацию.";
      return;
    }
  } catch (error: unknown) {
    bootstrapModalError.value =
      resolveErrorMessage(error, "") ||
      saveError.value ||
      "Не удалось создать стартовую панель";
  } finally {
    creatingInitialDashboard.value = false;
  }
}

async function importInitialDashboard(payload: { name: string; yaml: string }) {
  void payload.name;
  if (creatingInitialDashboard.value || importingInitialDashboard.value) return;
  importingInitialDashboard.value = true;
  bootstrapModalError.value = "";

  try {
    await restoreDashboardConfig(payload.yaml);
    await loadConfig();
  } catch (error: unknown) {
    bootstrapModalError.value = resolveErrorMessage(
      error,
      "Не удалось импортировать dashboard.yaml",
    );
  } finally {
    importingInitialDashboard.value = false;
  }
}

async function retryLoadFromPopup() {
  dismissedConfigError.value = "";
  popupOpen.value = false;
  await loadConfig();
}

watch(
  () => showBootstrapModal.value,
  (visible) => {
    if (!visible) {
      bootstrapModalError.value = "";
    }
  },
);
</script>

<style scoped>
.page.page--embedded {
  height: 100%;
  min-height: 100%;
}

.page.page--embedded .page-right-bottom {
  min-height: 100%;
}
</style>

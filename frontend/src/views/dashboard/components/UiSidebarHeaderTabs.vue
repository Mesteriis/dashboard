<template>
  <div class="brand brand--with-tools">
    <div class="brand-main">
      <img :src="EMBLEM_SRC" alt="Oko" />
      <div>
        <p class="brand-title">{{ appTitle }}</p>
        <p class="brand-subtitle">{{ appTagline }}</p>
      </div>
    </div>

    <div class="sidebar-nav-tools">
      <label class="sidebar-nav-search" for="sidebar-tree-search">
        <Search class="ui-icon sidebar-nav-search-icon" />
        <input
          id="sidebar-tree-search"
          v-model.trim="treeFilter"
          type="search"
          placeholder="Поиск: title url desc name"
          autocomplete="off"
        />
      </label>

      <UiHeroDropdown
        v-if="showSiteFilter"
        class="sidebar-nav-filter-dropdown"
        :model-value="siteFilter"
        label="Site"
        aria-label="Фильтр по site"
        :options="siteFilterOptions"
        @update:model-value="setSiteFilter"
      >
        <template #prefix>
          <span class="sidebar-nav-filter-prefix">
            <Filter class="ui-icon sidebar-nav-filter-icon" />
            <span class="sidebar-nav-filter-label">Site</span>
          </span>
        </template>
      </UiHeroDropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { Filter, Search } from "lucide-vue-next";
import UiHeroDropdown from "@/primitives/selection/UiHeroDropdown.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const {
  EMBLEM_SRC,
  appTitle,
  appTagline,
  treeFilter,
  siteFilter,
  siteFilterOptions,
  setSiteFilter,
} = dashboard;

const showSiteFilter = computed(
  () =>
    siteFilterOptions.value.filter((option: any) => option.value !== "all")
      .length > 1,
);

watch(
  () => showSiteFilter.value,
  (visible) => {
    if (!visible && siteFilter.value !== "all") {
      setSiteFilter("all");
    }
  },
  { immediate: true },
);
</script>

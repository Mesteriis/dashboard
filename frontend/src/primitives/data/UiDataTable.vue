<template>
  <section class="ui-table">
    <header class="ui-table__toolbar">
      <div class="ui-table__controls">
        <input
          v-if="showSearch"
          class="ui-table__search"
          type="search"
          placeholder="Поиск..."
          :value="search"
          @input="onSearch"
        />
      </div>

      <button
        v-if="showExport"
        type="button"
        class="ui-table__export ui-table__export--compact"
        title="Экспорт CSV"
        @click="exportCsv"
      >
        CSV
      </button>
    </header>

    <div ref="wrapElement" class="ui-table__wrap" :style="tableWrapStyle">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key" :class="{ sortable: column.sortable }">
              <div class="ui-table__th-main">
                <button
                  v-if="column.sortable"
                  type="button"
                  class="ui-table__sort-btn"
                  @click="toggleSort(column)"
                >
                  <span>{{ column.label }}</span>
                  <small v-if="sort.key === column.key">
                    {{ sort.direction === "asc" ? "▲" : "▼" }}
                  </small>
                </button>
                <span v-else>{{ column.label }}</span>
              </div>

              <div
                v-if="showFilters && column.filterable"
                class="ui-table__th-filter"
                @click.stop
              >
                <UiSelect
                  :model-value="resolveColumnFilterModel(column.key)"
                  :options="columnFilterOptions(column.key)"
                  :placeholder="`${column.label}: все`"
                  multiple
                  search
                  search-placeholder="Поиск значения..."
                  @update:model-value="onColumnFilterModelUpdate(column.key, $event)"
                >
                  <template #trigger="{ open, selectedLabels }">
                    <span class="ui-table__th-filter-value">
                      {{
                        selectedLabels.length
                          ? `${column.label}: ${selectedLabels.length}`
                          : `${column.label}: все`
                      }}
                    </span>
                    <span class="ui-table__th-filter-caret" :class="{ open }">▾</span>
                  </template>
                </UiSelect>
              </div>
            </th>
            <th v-if="actions.length">Actions</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="row in pagedRows"
            :key="resolveRowKey(row)"
            :class="{ 'ui-table__row-clickable': rowClickable }"
            :tabindex="rowClickable ? 0 : undefined"
            @click="onRowClick(row)"
            @keydown.enter.prevent="onRowKeyActivate(row)"
            @keydown.space.prevent="onRowKeyActivate(row)"
          >
            <td
              v-for="column in columns"
              :key="`${resolveRowKey(row)}-${column.key}`"
            >
              {{ formatCell(row, column.key) }}
            </td>
            <td v-if="actions.length" class="ui-table__actions">
              <button
                v-for="action in actions"
                :key="`${resolveRowKey(row)}-${action.id}`"
                type="button"
                @click.stop="emit('action', { id: action.id, row })"
              >
                {{ action.label }}
              </button>
            </td>
          </tr>

          <tr v-if="!pagedRows.length">
            <td
              :colspan="columns.length + (actions.length ? 1 : 0)"
              class="ui-table__empty"
            >
              Нет данных
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="showPagination" class="ui-table__pagination">
      <label v-if="showPageSizeSelector" class="ui-table__page-size">
        <span>Rows</span>
        <UiSelect
          class="ui-table__page-size-select"
          :model-value="String(effectivePageSize)"
          :options="pageSizeSelectOptions"
          placeholder=""
          @update:model-value="onPageSizeUpdate"
        />
      </label>

      <div class="ui-table__pagination-controls">
        <button type="button" :disabled="page <= 1" @click="page = page - 1">
          Назад
        </button>
        <span>Страница {{ page }} / {{ totalPages }}</span>
        <button
          type="button"
          :disabled="page >= totalPages"
          @click="page = page + 1"
        >
          Вперёд
        </button>
      </div>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import UiSelect from "@/ui/forms/UiSelect.vue";

interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
}

interface TableAction {
  id: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    rows: Array<Record<string, unknown>>;
    columns: TableColumn[];
    actions?: TableAction[];
    rowKey?: string;
    showSearch?: boolean;
    showFilters?: boolean;
    showExport?: boolean;
    showPagination?: boolean;
    pageSize?: number;
    pageSizeOptions?: number[];
    showPageSizeSelector?: boolean;
    autoPageSize?: boolean;
    availableHeightPx?: number | null;
    estimatedRowHeight?: number;
    headerRowHeight?: number;
    rowClickable?: boolean;
    maxHeight?: string | null;
  }>(),
  {
    actions: () => [],
    rowKey: "id",
    showSearch: true,
    showFilters: true,
    showExport: true,
    showPagination: true,
    pageSize: 8,
    pageSizeOptions: () => [8, 12, 16, 20, 30, 50],
    showPageSizeSelector: true,
    autoPageSize: false,
    availableHeightPx: null,
    estimatedRowHeight: 44,
    headerRowHeight: 42,
    rowClickable: false,
    maxHeight: null,
  },
);

const emit = defineEmits<{
  action: [payload: { id: string; row: Record<string, unknown> }];
  export: [payload: string];
  rowClick: [payload: Record<string, unknown>];
}>();

const search = ref("");
const page = ref(1);
const manualPageSize = ref<number | null>(null);
const wrapElement = ref<HTMLElement | null>(null);
const measuredWrapHeight = ref(0);
const sort = reactive<{ key: string; direction: "asc" | "desc" }>({
  key: "",
  direction: "asc",
});
const filters = reactive<Record<string, string[]>>({});
let wrapResizeObserver: ResizeObserver | null = null;

const actions = computed(() => props.actions || []);
const rowClickable = computed(() => Boolean(props.rowClickable));
const showPageSizeSelector = computed(
  () => Boolean(props.showPagination) && Boolean(props.showPageSizeSelector),
);
const pageSizeSelectOptions = computed(() =>
  normalizedPageSizeOptions.value.map((size) => ({
    label: String(size),
    value: String(size),
  })),
);

const normalizedPageSizeOptions = computed(() => {
  const values = new Set<number>();
  for (const value of props.pageSizeOptions || []) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) continue;
    const normalized = Math.max(1, Math.floor(parsed));
    values.add(normalized);
  }
  const fallback = Math.max(1, Math.floor(Number(props.pageSize) || 1));
  values.add(fallback);
  return Array.from(values).sort((left, right) => left - right);
});

const autoHeightPx = computed(() => {
  if (typeof props.availableHeightPx === "number" && Number.isFinite(props.availableHeightPx)) {
    return Math.max(0, props.availableHeightPx);
  }
  return measuredWrapHeight.value;
});

const autoPageSize = computed<number | null>(() => {
  if (!props.autoPageSize) return null;
  const heightPx = autoHeightPx.value;
  if (heightPx <= 0) return null;
  const headerHeight = Math.max(0, Number(props.headerRowHeight) || 0);
  const rowHeight = Math.max(20, Number(props.estimatedRowHeight) || 44);
  const visibleRows = Math.max(1, Math.floor((heightPx - headerHeight) / rowHeight));
  const options = normalizedPageSizeOptions.value;
  if (!options.length) return visibleRows;
  let selected = options[0];
  for (const option of options) {
    if (option <= visibleRows) {
      selected = option;
      continue;
    }
    break;
  }
  return selected;
});

const effectivePageSize = computed(() => {
  if (manualPageSize.value && manualPageSize.value > 0) {
    return manualPageSize.value;
  }
  if (autoPageSize.value && autoPageSize.value > 0) {
    return autoPageSize.value;
  }
  return Math.max(1, Math.floor(Number(props.pageSize) || 1));
});

const tableWrapStyle = computed<Record<string, string> | undefined>(() => {
  if (!props.maxHeight) return undefined;
  return { maxHeight: props.maxHeight };
});

const preparedRows = computed(() => {
  const normalizedSearch = search.value.trim().toLowerCase();

  let filtered = props.rows.filter((row) => {
    if (normalizedSearch) {
      const searchableText = props.columns
        .map((column) => String(row[column.key] ?? ""))
        .join(" ")
        .toLowerCase();
      if (!searchableText.includes(normalizedSearch)) return false;
    }

    for (const [key, value] of Object.entries(filters)) {
      if (!value.length) continue;
      const raw = row[key];
      if (Array.isArray(raw)) {
        const normalized = new Set(raw.map((entry) => String(entry ?? "")));
        const hasAnyMatch = value.some((selectedValue) =>
          normalized.has(selectedValue),
        );
        if (!hasAnyMatch) return false;
        continue;
      }
      const current = String(raw ?? "");
      if (!value.includes(current)) return false;
    }

    return true;
  });

  if (sort.key) {
    filtered = filtered.slice().sort((left, right) => {
      const leftValue = String(left[sort.key] ?? "").toLowerCase();
      const rightValue = String(right[sort.key] ?? "").toLowerCase();
      const comparison = leftValue.localeCompare(rightValue, "ru", {
        sensitivity: "base",
      });
      return sort.direction === "asc" ? comparison : -comparison;
    });
  }

  return filtered;
});

const totalPages = computed(() =>
  Math.max(1, Math.ceil(preparedRows.value.length / effectivePageSize.value)),
);

const pagedRows = computed(() => {
  if (!props.showPagination) return preparedRows.value;
  const start = (page.value - 1) * effectivePageSize.value;
  return preparedRows.value.slice(start, start + effectivePageSize.value);
});

watch(
  () => [preparedRows.value.length, effectivePageSize.value],
  () => {
    if (page.value > totalPages.value) {
      page.value = totalPages.value;
    }
    if (page.value < 1) {
      page.value = 1;
    }
  },
);

watch(
  () => props.pageSize,
  (nextValue) => {
    if (manualPageSize.value == null) return;
    if (manualPageSize.value === Math.max(1, Math.floor(Number(nextValue) || 1))) {
      manualPageSize.value = null;
    }
  },
);

watch(
  () => props.maxHeight,
  async () => {
    await nextTick();
    updateMeasuredWrapHeight();
  },
);

onMounted(async () => {
  await nextTick();
  updateMeasuredWrapHeight();
  if (typeof ResizeObserver !== "undefined" && wrapElement.value) {
    wrapResizeObserver = new ResizeObserver(() => updateMeasuredWrapHeight());
    wrapResizeObserver.observe(wrapElement.value);
  } else if (typeof window !== "undefined") {
    window.addEventListener("resize", updateMeasuredWrapHeight);
  }
});

onBeforeUnmount(() => {
  if (wrapResizeObserver) {
    wrapResizeObserver.disconnect();
    wrapResizeObserver = null;
  }
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", updateMeasuredWrapHeight);
  }
});

function resolveRowKey(row: Record<string, unknown>): string {
  const keyValue = row[props.rowKey];
  if (keyValue != null) return String(keyValue);
  return JSON.stringify(row);
}

function formatCell(row: Record<string, unknown>, key: string): string {
  const value = row[key];
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }
  if (value == null) return "";
  return String(value);
}

function onSearch(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  search.value = String(target?.value || "");
  page.value = 1;
}

function resolveColumnFilterModel(key: string): string[] {
  return filters[key] || [];
}

function onColumnFilterModelUpdate(key: string, value: string | string[]): void {
  filters[key] = normalizeFilterModel(value);
  page.value = 1;
}

function onPageSizeUpdate(value: string | string[]): void {
  const rawValue = Array.isArray(value) ? value[0] : value;
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) return;
  manualPageSize.value = Math.max(1, Math.floor(parsed));
  page.value = 1;
}

function updateMeasuredWrapHeight(): void {
  measuredWrapHeight.value = Math.max(0, wrapElement.value?.clientHeight || 0);
}

function columnFilterValues(key: string): string[] {
  const values = new Set<string>();
  for (const row of props.rows) {
    const raw = row[key];
    if (Array.isArray(raw)) {
      for (const item of raw) {
        const token = String(item ?? "");
        if (!token) continue;
        values.add(token);
      }
      continue;
    }
    if (raw == null || raw === "") continue;
    values.add(String(raw));
  }
  return Array.from(values).sort((left, right) =>
    left.localeCompare(right, "ru"),
  );
}

function columnFilterOptions(key: string): Array<{ label: string; value: string }> {
  return columnFilterValues(key).map((value) => ({
    label: value,
    value,
  }));
}

function normalizeFilterModel(value: string | string[]): string[] {
  const rawValues = Array.isArray(value) ? value : value ? [value] : [];
  const unique = new Set<string>();
  for (const item of rawValues) {
    const token = String(item || "").trim();
    if (!token) continue;
    unique.add(token);
  }
  return Array.from(unique);
}

function onRowClick(row: Record<string, unknown>): void {
  if (!rowClickable.value) return;
  emit("rowClick", row);
}

function onRowKeyActivate(row: Record<string, unknown>): void {
  if (!rowClickable.value) return;
  emit("rowClick", row);
}

function toggleSort(column: TableColumn): void {
  if (!column.sortable) return;
  if (sort.key !== column.key) {
    sort.key = column.key;
    sort.direction = "asc";
    return;
  }
  sort.direction = sort.direction === "asc" ? "desc" : "asc";
}

function exportCsv(): void {
  const header = props.columns.map((column) => column.label).join(",");
  const body = preparedRows.value
    .map((row) =>
      props.columns
        .map((column) => escapeCsv(formatCell(row, column.key)))
        .join(","),
    )
    .join("\n");
  const csv = `${header}\n${body}`;
  emit("export", csv);

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = "table-export.csv";
  link.click();
  URL.revokeObjectURL(href);
}

function escapeCsv(value: string): string {
  if (!value.includes(",") && !value.includes('"') && !value.includes("\n")) {
    return value;
  }
  return `"${value.replaceAll('"', '""')}"`;
}
</script>

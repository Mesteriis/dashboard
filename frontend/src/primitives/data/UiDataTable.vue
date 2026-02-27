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

        <template v-if="showFilters">
          <select
            v-for="column in filterColumns"
            :key="column.key"
            class="ui-table__filter"
            :value="filters[column.key] || ''"
            @change="onFilterChange(column.key, $event)"
          >
            <option value="">{{ column.label }}: все</option>
            <option
              v-for="value in columnFilterValues(column.key)"
              :key="`${column.key}-${value}`"
              :value="value"
            >
              {{ value }}
            </option>
          </select>
        </template>
      </div>

      <button
        v-if="showExport"
        type="button"
        class="ui-table__export"
        @click="exportCsv"
      >
        Export CSV
      </button>
    </header>

    <div class="ui-table__wrap">
      <table>
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              :class="{ sortable: column.sortable }"
              @click="toggleSort(column)"
            >
              <span>{{ column.label }}</span>
              <small v-if="sort.key === column.key">
                {{ sort.direction === "asc" ? "▲" : "▼" }}
              </small>
            </th>
            <th v-if="actions.length">Actions</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="row in pagedRows" :key="resolveRowKey(row)">
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
                @click="emit('action', { id: action.id, row })"
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
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";

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
  }>(),
  {
    actions: () => [],
    rowKey: "id",
    showSearch: true,
    showFilters: true,
    showExport: true,
    showPagination: true,
    pageSize: 8,
  },
);

const emit = defineEmits<{
  action: [payload: { id: string; row: Record<string, unknown> }];
  export: [payload: string];
}>();

const search = ref("");
const page = ref(1);
const sort = reactive<{ key: string; direction: "asc" | "desc" }>({
  key: "",
  direction: "asc",
});
const filters = reactive<Record<string, string>>({});

const actions = computed(() => props.actions || []);
const filterColumns = computed(() =>
  props.columns.filter((column) => column.filterable),
);

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
      if (!value) continue;
      if (String(row[key] ?? "") !== value) return false;
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
  Math.max(1, Math.ceil(preparedRows.value.length / props.pageSize)),
);

const pagedRows = computed(() => {
  if (!props.showPagination) return preparedRows.value;
  const start = (page.value - 1) * props.pageSize;
  return preparedRows.value.slice(start, start + props.pageSize);
});

watch(
  () => [preparedRows.value.length, props.pageSize],
  () => {
    if (page.value > totalPages.value) {
      page.value = totalPages.value;
    }
    if (page.value < 1) {
      page.value = 1;
    }
  },
);

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

function onFilterChange(key: string, event: Event): void {
  const target = event.target as HTMLSelectElement | null;
  filters[key] = String(target?.value || "");
  page.value = 1;
}

function columnFilterValues(key: string): string[] {
  const values = new Set<string>();
  for (const row of props.rows) {
    const raw = row[key];
    if (raw == null || raw === "") continue;
    values.add(String(raw));
  }
  return Array.from(values).sort((left, right) =>
    left.localeCompare(right, "ru"),
  );
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

<template>
  <nav class="ui-pagination" aria-label="Pagination">
    <button type="button" :disabled="page <= 1" @click="setPage(page - 1)">
      Назад
    </button>
    <button
      v-for="value in pages"
      :key="value"
      type="button"
      :class="{ 'is-active': value === page }"
      @click="setPage(value)"
    >
      {{ value }}
    </button>
    <button
      type="button"
      :disabled="page >= totalPages"
      @click="setPage(page + 1)"
    >
      Вперёд
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    total: number;
    page: number;
    pageSize?: number;
    maxButtons?: number;
  }>(),
  {
    pageSize: 10,
    maxButtons: 7,
  },
);

const emit = defineEmits<{
  "update:page": [value: number];
}>();

const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.total / props.pageSize)),
);

const pages = computed(() => {
  const safePage = Math.min(totalPages.value, Math.max(1, props.page));
  const half = Math.floor(props.maxButtons / 2);
  let start = Math.max(1, safePage - half);
  let end = Math.min(totalPages.value, start + props.maxButtons - 1);
  if (end - start + 1 < props.maxButtons) {
    start = Math.max(1, end - props.maxButtons + 1);
  }

  const result: number[] = [];
  for (let index = start; index <= end; index += 1) {
    result.push(index);
  }
  return result;
});

function setPage(value: number): void {
  const next = Math.min(totalPages.value, Math.max(1, value));
  emit("update:page", next);
}
</script>

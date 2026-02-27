<template>
  <div class="ui-tree" role="tree">
    <button
      v-for="node in visibleNodes"
      :key="node.id"
      type="button"
      class="ui-tree__node"
      :class="{ 'is-selected': modelValue === node.id }"
      :style="{ paddingInlineStart: `${node.depth * 20 + 8}px` }"
      @click="selectNode(node.id)"
    >
      <span
        v-if="node.hasChildren"
        class="ui-tree__toggle"
        @click.stop="toggleNode(node.id)"
      >
        {{ expanded.has(node.id) ? "▾" : "▸" }}
      </span>
      <span v-else class="ui-tree__toggle is-empty">•</span>
      <span>{{ node.label }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

interface TreeNode {
  id: string;
  label: string;
  children?: TreeNode[];
}

interface VisibleNode {
  id: string;
  label: string;
  depth: number;
  hasChildren: boolean;
}

const props = defineProps<{
  nodes: TreeNode[];
  modelValue: string;
  defaultExpanded?: string[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  toggle: [id: string, expanded: boolean];
}>();

const expanded = ref<Set<string>>(new Set(props.defaultExpanded || []));

watch(
  () => props.defaultExpanded,
  (value) => {
    expanded.value = new Set(value || []);
  },
);

const visibleNodes = computed<VisibleNode[]>(() => {
  const result: VisibleNode[] = [];

  function visit(nodes: TreeNode[], depth: number): void {
    for (const node of nodes) {
      const hasChildren =
        Array.isArray(node.children) && node.children.length > 0;
      result.push({
        id: node.id,
        label: node.label,
        depth,
        hasChildren,
      });
      if (hasChildren && expanded.value.has(node.id)) {
        visit(node.children || [], depth + 1);
      }
    }
  }

  visit(props.nodes, 0);
  return result;
});

function toggleNode(id: string): void {
  const next = new Set(expanded.value);
  let isNowExpanded = true;
  if (next.has(id)) {
    next.delete(id);
    isNowExpanded = false;
  } else {
    next.add(id);
  }
  expanded.value = next;
  emit("toggle", id, isNowExpanded);
}

function selectNode(id: string): void {
  emit("update:modelValue", id);
}
</script>

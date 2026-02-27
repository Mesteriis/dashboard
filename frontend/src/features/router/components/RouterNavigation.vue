<template>
  <div class="router-navigation" :class="`router-navigation--${displayMode}`">
    <template v-if="displayMode === 'dropdown'">
      <!-- Выпадающее меню со всеми роутами -->
      <div class="router-navigation__dropdown">
        <button
          class="router-navigation__trigger"
          type="button"
          @click="toggleDropdown"
          :aria-expanded="isDropdownOpen"
        >
          <span class="router-navigation__trigger-content">
            <component
              :is="triggerIcon"
              v-if="triggerIcon"
              class="ui-icon router-navigation__icon"
            />
            <span>{{ triggerLabel }}</span>
          </span>
          <span
            class="router-navigation__caret"
            :class="{ 'router-navigation__caret--open': isDropdownOpen }"
            >▾</span
          >
        </button>

        <Transition name="router-navigation-fade">
          <div
            v-if="isDropdownOpen"
            class="router-navigation__menu"
            role="menu"
          >
            <RouterMenuItems
              :items="menuItems"
              @navigate="handleNavigateAndClose"
            />
          </div>
        </Transition>
      </div>
    </template>

    <template v-else-if="displayMode === 'inline'">
      <!-- Inline список роутов -->
      <RouterMenuItems :items="menuItems" @navigate="handleNavigate" />
    </template>

    <template v-else-if="displayMode === 'sidebar'">
      <!-- Sidebar дерево роутов -->
      <div class="router-navigation__sidebar">
        <RouterMenuItems :items="menuItems" @navigate="handleNavigate" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, type Component } from "vue";
import { useRouter, type RouteLocationRaw } from "vue-router";
import { Palette } from "lucide-vue-next";
import {
  buildRouterTree,
  routerTreeToMenuItems,
  type RouterTreeNode,
} from "@/features/router/utils/buildRouterTree";
import RouterMenuItems from "@/features/router/components/RouterMenuItem.vue";

type DisplayMode = "dropdown" | "inline" | "sidebar";

const props = withDefaults(
  defineProps<{
    displayMode?: DisplayMode;
    triggerLabel?: string;
    triggerIcon?: Component | string;
    maxDepth?: number;
    includeHidden?: boolean;
  }>(),
  {
    displayMode: "dropdown",
    triggerLabel: "Навигация",
    triggerIcon: Palette,
    maxDepth: 10,
    includeHidden: false,
  },
);

const emit = defineEmits<{
  navigate: [path: RouteLocationRaw];
}>();

const router = useRouter();
const routes = router.getRoutes();
const isDropdownOpen = ref(false);

// Строим дерево роутов
const routerTree = computed<RouterTreeNode[]>(() => {
  const tree = buildRouterTree(routes);
  return filterByDepth(tree, props.maxDepth);
});

// Преобразуем в формат меню
const menuItems = computed(() => routerTreeToMenuItems(routerTree.value));

function filterByDepth(
  tree: RouterTreeNode[],
  maxDepth: number,
  currentDepth = 0,
): RouterTreeNode[] {
  if (currentDepth >= maxDepth) return [];

  return tree
    .filter((node) => !node.hidden || props.includeHidden)
    .map((node) => ({
      ...node,
      children: node.children
        ? filterByDepth(node.children, maxDepth, currentDepth + 1)
        : undefined,
    }));
}

function toggleDropdown(): void {
  isDropdownOpen.value = !isDropdownOpen.value;
}

function closeDropdown(): void {
  isDropdownOpen.value = false;
}

function handleNavigate(item: {
  id: string;
  label: string;
  route?: string;
}): void {
  if (item.route) {
    void router.push(item.route);
    emit("navigate", item.route);
  }
}

function handleNavigateAndClose(item: {
  id: string;
  label: string;
  route?: string;
}): void {
  handleNavigate(item);
  closeDropdown();
}

// Закрытие при клике вне
function handleOutsideClick(event: MouseEvent): void {
  const target = event.target as Node;
  const dropdownEl = document.querySelector(".router-navigation__dropdown");
  if (dropdownEl && !dropdownEl.contains(target)) {
    closeDropdown();
  }
}

onMounted(() => {
  document.addEventListener("click", handleOutsideClick);
});

onUnmounted(() => {
  document.removeEventListener("click", handleOutsideClick);
});
</script>

<style scoped>
.router-navigation {
  display: inline-block;
  position: relative;
}

.router-navigation__dropdown {
  position: relative;
}

.router-navigation__trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(30, 60, 90, 0.3);
  border: 1px solid rgba(120, 183, 218, 0.2);
  border-radius: 8px;
  color: rgba(200, 230, 255, 0.9);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms ease;
}

.router-navigation__trigger:hover {
  background: rgba(30, 60, 90, 0.5);
  border-color: rgba(120, 183, 218, 0.4);
}

.router-navigation__trigger-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.router-navigation__icon {
  width: 16px;
  height: 16px;
}

.router-navigation__caret {
  font-size: 0.75rem;
  transition: transform 200ms ease;
  opacity: 0.7;
}

.router-navigation__caret--open {
  transform: rotate(180deg);
}

.router-navigation__menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 200px;
  max-height: 80vh;
  overflow-y: auto;
  background: rgba(15, 34, 51, 0.98);
  border: 1px solid rgba(120, 183, 218, 0.2);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 1000;
  padding: 4px 0;
}

.router-navigation__sidebar {
  padding: 8px;
}

/* Transition */
.router-navigation-fade-enter-active,
.router-navigation-fade-leave-active {
  transition: all 200ms ease;
}

.router-navigation-fade-enter-from,
.router-navigation-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

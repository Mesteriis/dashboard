<template>
  <li v-if="item.divider" class="router-menu__divider" role="separator" />

  <li
    v-else-if="item.children && item.children.length"
    class="router-menu__item router-menu__item--has-children"
  >
    <button
      class="router-menu__trigger"
      type="button"
      role="menuitem"
      aria-haspopup="true"
      :aria-expanded="expandedItems.includes(item.id)"
      @click="toggleExpand(item.id)"
    >
      <span class="router-menu__label">{{ item.label }}</span>
      <span
        class="router-menu__arrow"
        :class="{ 'router-menu__arrow--open': expandedItems.includes(item.id) }"
      >
        ▸
      </span>
    </button>

    <!-- Вложенное меню -->
    <Transition name="router-menu-slide">
      <ul
        v-show="expandedItems.includes(item.id)"
        class="router-menu router-menu--nested"
        role="menu"
      >
        <RouterMenuItem
          v-for="child in item.children"
          :key="child.id"
          :item="child"
          :active-route="activeRoute"
          @navigate="handleNavigate"
        />
      </ul>
    </Transition>
  </li>

  <li v-else class="router-menu__item">
    <button
      class="router-menu__link"
      :class="{ 'router-menu__link--active': isActive(item.route) }"
      type="button"
      role="menuitem"
      @click="handleNavigate(item)"
    >
      <span class="router-menu__label">{{ item.label }}</span>
    </button>
  </li>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";

export interface RouterMenuItemType {
  id: string;
  label: string;
  route?: string;
  children?: RouterMenuItemType[];
  divider?: boolean;
}

const props = defineProps<{
  item: RouterMenuItemType;
  activeRoute: string;
}>();

const emit = defineEmits<{
  navigate: [item: RouterMenuItemType];
}>();

const route = useRoute();
const expandedItems = ref<string[]>([]);

watch(
  () => route.path,
  () => {
    expandPathToRoute(route.path);
  },
  { immediate: true },
);

function isActive(routePath?: string): boolean {
  if (!routePath) return false;
  return (
    props.activeRoute === routePath ||
    props.activeRoute.startsWith(`${routePath}/`)
  );
}

function expandPathToRoute(path: string): void {
  if (props.item.children) {
    if (hasActiveChild(props.item.children, path)) {
      if (!expandedItems.value.includes(props.item.id)) {
        expandedItems.value.push(props.item.id);
      }
    }
  }
}

function hasActiveChild(
  items: RouterMenuItemType[],
  targetPath: string,
): boolean {
  return items.some((item) => {
    if (item.route === targetPath) return true;
    if (item.children) return hasActiveChild(item.children, targetPath);
    return false;
  });
}

function toggleExpand(itemId: string): void {
  const index = expandedItems.value.indexOf(itemId);
  if (index > -1) {
    expandedItems.value = expandedItems.value.filter((id) => id !== itemId);
  } else {
    expandedItems.value.push(itemId);
  }
}

function handleNavigate(item: RouterMenuItemType): void {
  emit("navigate", item);
}
</script>

<style scoped>
.router-menu {
  list-style: none;
  margin: 0;
  padding: 0;
}

.router-menu--nested {
  margin-left: 16px;
  margin-top: 4px;
}

.router-menu__item {
  margin: 0;
}

.router-menu__trigger,
.router-menu__link {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: rgba(200, 230, 255, 0.9);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms ease;
}

.router-menu__trigger:hover,
.router-menu__link:hover {
  background: rgba(30, 60, 90, 0.4);
}

.router-menu__link--active {
  background: rgba(45, 212, 191, 0.15);
  color: rgba(45, 212, 191, 1);
  font-weight: 500;
}

.router-menu__label {
  flex: 1;
  text-align: left;
}

.router-menu__arrow {
  font-size: 0.75rem;
  transition: transform 200ms ease;
  opacity: 0.7;
}

.router-menu__arrow--open {
  transform: rotate(90deg);
}

.router-menu__divider {
  height: 1px;
  margin: 8px 0;
  background-color: rgba(120, 183, 218, 0.2);
}

/* Transition */
.router-menu-slide-enter-active,
.router-menu-slide-leave-active {
  transition: all 200ms ease;
}

.router-menu-slide-enter-from,
.router-menu-slide-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>

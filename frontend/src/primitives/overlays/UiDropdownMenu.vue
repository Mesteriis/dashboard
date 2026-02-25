<template>
  <div
    ref="rootRef"
    class="ui-menu"
    :class="[`align-${align}`, { open }]"
  >
    <button
      class="ui-menu__trigger"
      :class="triggerClass"
      type="button"
      :aria-label="ariaLabel || label"
      aria-haspopup="menu"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <span class="ui-menu__trigger-content">
        <slot name="trigger">{{ label }}</slot>
      </span>
      <span
        v-if="showCaret"
        class="ui-icon ui-menu__caret"
        :class="{ open }"
        aria-hidden="true"
      >
        <slot name="caret" :open="open">▾</slot>
      </span>
    </button>

    <Transition name="ui-menu-transition">
      <ul
        v-if="open"
        class="ui-menu__list"
        role="menu"
        :aria-label="ariaLabel || label"
      >
        <li
          v-for="item in items"
          :key="item.id"
          role="none"
        >
          <button
            class="ui-menu__item"
            :class="[itemClass, { 'is-danger': item.danger }]"
            type="button"
            role="menuitem"
            :disabled="Boolean(item.disabled)"
            @click="selectItem(item.id)"
          >
            <span class="ui-menu__item-content">
              <slot name="item-icon" :item="item">
                <component
                  :is="item.icon"
                  v-if="isComponentIcon(item.icon)"
                  class="ui-icon ui-menu__item-icon"
                  aria-hidden="true"
                />
                <span
                  v-else-if="typeof item.icon === 'string' && item.icon.trim()"
                  class="ui-icon ui-menu__item-icon"
                  aria-hidden="true"
                >
                  {{ item.icon }}
                </span>
              </slot>
              <span>{{ item.label }}</span>
            </span>
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, type Component } from "vue";

interface DropdownMenuItem {
  id: string;
  label: string;
  icon?: Component | string;
  danger?: boolean;
  disabled?: boolean;
}

const props = withDefaults(
  defineProps<{
    items: DropdownMenuItem[];
    label?: string;
    ariaLabel?: string;
    align?: "left" | "right";
    disabled?: boolean;
    closeOnSelect?: boolean;
    showCaret?: boolean;
    triggerClass?: string;
    itemClass?: string;
  }>(),
  {
    label: "Menu",
    ariaLabel: "",
    align: "right",
    disabled: false,
    closeOnSelect: true,
    showCaret: true,
    triggerClass: "",
    itemClass: "",
  },
);

const emit = defineEmits<{
  action: [id: string];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);

function isComponentIcon(icon: DropdownMenuItem["icon"]): icon is Component {
  return typeof icon === "object" || typeof icon === "function";
}

function toggleOpen(): void {
  if (props.disabled) return;
  open.value = !open.value;
}

function closeMenu(): void {
  open.value = false;
}

function selectItem(id: string): void {
  emit("action", id);
  if (props.closeOnSelect) {
    closeMenu();
  }
}

function handleOutsidePointer(event: PointerEvent): void {
  if (!open.value) return;
  const targetNode = event.target as Node | null;
  if (rootRef.value && targetNode && !rootRef.value.contains(targetNode)) {
    closeMenu();
  }
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  closeMenu();
}

onMounted(() => {
  if (typeof window === "undefined") return;
  window.addEventListener("pointerdown", handleOutsidePointer);
  window.addEventListener("keydown", handleEscape);
});

onBeforeUnmount(() => {
  if (typeof window === "undefined") return;
  window.removeEventListener("pointerdown", handleOutsidePointer);
  window.removeEventListener("keydown", handleEscape);
});
</script>

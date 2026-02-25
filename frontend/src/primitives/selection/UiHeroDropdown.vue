<template>
  <div ref="rootRef" class="hero-dropdown" :class="{ open }">
    <button
      class="hero-dropdown-trigger"
      type="button"
      :aria-label="ariaLabel || label"
      :aria-haspopup="'listbox'"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <slot name="prefix">
        <span class="hero-dropdown-label">{{ label }}</span>
      </slot>
      <span class="hero-dropdown-value">{{ selectedLabel }}</span>
      <span class="ui-icon hero-dropdown-caret" :class="{ open }" aria-hidden="true">
        <slot name="caret" :open="open">▾</slot>
      </span>
    </button>

    <Transition name="hero-dropdown-menu-transition">
      <ul
        v-if="open"
        ref="menuRef"
        class="hero-dropdown-menu"
        :class="menuPlacementClass"
        :style="menuStyles"
        role="listbox"
        :aria-label="ariaLabel || label"
      >
        <li
          v-for="option in options"
          :key="option.value"
          role="option"
          :aria-selected="modelValue === option.value"
        >
          <button
            class="hero-dropdown-option"
            :class="{ active: modelValue === option.value }"
            type="button"
            @click="selectOption(option.value)"
          >
            <span>{{ option.label }}</span>
            <span
              v-if="modelValue === option.value"
              class="ui-icon hero-dropdown-check"
              aria-hidden="true"
            >
              <slot name="check-icon" :option="option">✓</slot>
            </span>
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

interface HeroDropdownOption {
  value: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    label?: string;
    ariaLabel?: string;
    options?: HeroDropdownOption[];
    disabled?: boolean;
  }>(),
  {
    modelValue: "",
    label: "",
    ariaLabel: "",
    options: () => [],
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const menuDirection = ref<"down" | "up">("down");
const menuMaxHeight = ref(360);

const selectedLabel = computed(() => {
  const selected = props.options.find(
    (option) => option.value === props.modelValue,
  );
  if (selected) return selected.label;
  return props.options[0]?.label || "";
});

const menuPlacementClass = computed(() =>
  menuDirection.value === "up"
    ? "hero-dropdown-menu--up"
    : "hero-dropdown-menu--down",
);

const menuStyles = computed(() => ({
  maxHeight: `${menuMaxHeight.value}px`,
}));

function toggleOpen(): void {
  if (props.disabled) return;
  open.value = !open.value;
}

function selectOption(value: string): void {
  emit("update:modelValue", value);
  open.value = false;
}

function handleOutsidePointer(event: PointerEvent): void {
  if (!open.value) return;
  const targetNode = event.target as Node | null;
  if (rootRef.value && targetNode && !rootRef.value.contains(targetNode)) {
    open.value = false;
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    open.value = false;
  }
}

function updateMenuPlacement(): void {
  if (typeof window === "undefined") return;
  if (!rootRef.value) return;

  const triggerRect = rootRef.value.getBoundingClientRect();
  const viewportHeight = window.innerHeight || 0;
  const margin = 12;
  const spaceBelow = Math.max(0, viewportHeight - triggerRect.bottom - margin);
  const spaceAbove = Math.max(0, triggerRect.top - margin);
  const menuHeight = Math.min(menuRef.value?.scrollHeight || 260, 360);
  const preferUp = spaceBelow < menuHeight && spaceAbove > spaceBelow;

  menuDirection.value = preferUp ? "up" : "down";
  const availableSpace = preferUp ? spaceAbove : spaceBelow;
  menuMaxHeight.value = Math.max(140, Math.min(360, Math.floor(availableSpace)));
}

function handleViewportChange(): void {
  if (!open.value) return;
  updateMenuPlacement();
}

watch(open, (isOpen) => {
  if (!isOpen) return;
  void nextTick(() => {
    updateMenuPlacement();
  });
});

onMounted(() => {
  if (typeof window === "undefined") return;
  window.addEventListener("pointerdown", handleOutsidePointer);
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("resize", handleViewportChange);
  window.addEventListener("scroll", handleViewportChange, true);
});

onBeforeUnmount(() => {
  if (typeof window === "undefined") return;
  window.removeEventListener("pointerdown", handleOutsidePointer);
  window.removeEventListener("keydown", handleKeydown);
  window.removeEventListener("resize", handleViewportChange);
  window.removeEventListener("scroll", handleViewportChange, true);
});
</script>

<template>
  <div
    ref="rootRef"
    class="hero-dropdown hero-multiselect"
    :class="{ open }"
  >
    <button
      class="hero-dropdown-trigger"
      type="button"
      :aria-label="ariaLabel || label"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <slot name="prefix">
        <span class="hero-dropdown-label">{{ label }}</span>
      </slot>
      <span class="hero-dropdown-value hero-multiselect-value">{{
        selectedSummary
      }}</span>
      <ChevronDown class="ui-icon hero-dropdown-caret" :class="{ open }" />
    </button>

    <Transition name="hero-dropdown-menu-transition">
      <ul
        v-if="open"
        ref="menuRef"
        class="hero-dropdown-menu hero-multiselect-menu"
        :class="menuPlacementClass"
        :style="menuStyles"
        role="listbox"
        aria-multiselectable="true"
        :aria-label="ariaLabel || label"
      >
        <li
          v-for="option in options"
          :key="option.value"
          role="option"
          :aria-selected="isSelected(option.value)"
        >
          <button
            class="hero-dropdown-option hero-multiselect-option"
            :class="{ active: isSelected(option.value) }"
            type="button"
            @click="toggleOption(option.value)"
          >
            <span>{{ option.label }}</span>
            <Check
              v-if="isSelected(option.value)"
              class="ui-icon hero-dropdown-check"
            />
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Check, ChevronDown } from "lucide-vue-next";

interface HeroMultiSelectOption {
  value: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    modelValue?: string[];
    label?: string;
    ariaLabel?: string;
    options?: HeroMultiSelectOption[];
    disabled?: boolean;
    placeholder?: string;
  }>(),
  {
    modelValue: () => [],
    label: "",
    ariaLabel: "",
    options: () => [],
    disabled: false,
    placeholder: "Выбрать",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const menuDirection = ref<"down" | "up">("down");
const menuMaxHeight = ref(360);

const selectedValues = computed(() =>
  Array.from(
    new Set(
      (props.modelValue || [])
        .map((value) => String(value || "").trim())
        .filter(Boolean),
    ),
  ),
);

const selectedSummary = computed(() => {
  if (!selectedValues.value.length) return props.placeholder;
  const optionByValue = new Map(
    props.options.map((option) => [option.value, option.label]),
  );
  const labels = selectedValues.value.map(
    (value) => optionByValue.get(value) || value,
  );
  return labels.join(", ");
});

const menuPlacementClass = computed(() =>
  menuDirection.value === "up"
    ? "hero-dropdown-menu--up"
    : "hero-dropdown-menu--down",
);

const menuStyles = computed(() => ({
  maxHeight: `${menuMaxHeight.value}px`,
}));

function isSelected(value: string): boolean {
  return selectedValues.value.includes(value);
}

function toggleOpen(): void {
  if (props.disabled) return;
  open.value = !open.value;
}

function toggleOption(value: string): void {
  if (!value) return;
  if (isSelected(value)) {
    emit(
      "update:modelValue",
      selectedValues.value.filter((entry) => entry !== value),
    );
    return;
  }
  emit("update:modelValue", [...selectedValues.value, value]);
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

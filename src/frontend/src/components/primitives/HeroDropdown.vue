<template>
  <div ref="rootRef" class="hero-dropdown">
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
      <ChevronDown class="ui-icon hero-dropdown-caret" :class="{ open }" />
    </button>

    <Transition name="hero-dropdown-menu-transition">
      <ul v-if="open" class="hero-dropdown-menu" role="listbox" :aria-label="ariaLabel || label">
        <li v-for="option in options" :key="option.value" role="option" :aria-selected="modelValue === option.value">
          <button class="hero-dropdown-option" :class="{ active: modelValue === option.value }" type="button" @click="selectOption(option.value)">
            <span>{{ option.label }}</span>
            <Check v-if="modelValue === option.value" class="ui-icon hero-dropdown-check" />
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  label: {
    type: String,
    default: '',
  },
  ariaLabel: {
    type: String,
    default: '',
  },
  options: {
    type: Array,
    default: () => [],
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const rootRef = ref(null)

const selectedLabel = computed(() => {
  const selected = props.options.find((option) => option.value === props.modelValue)
  if (selected) return selected.label
  return props.options[0]?.label || ''
})

function toggleOpen() {
  if (props.disabled) return
  open.value = !open.value
}

function selectOption(value) {
  emit('update:modelValue', value)
  open.value = false
}

function handleOutsidePointer(event) {
  if (!open.value) return
  if (rootRef.value && !rootRef.value.contains(event.target)) {
    open.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    open.value = false
  }
}

onMounted(() => {
  window.addEventListener('pointerdown', handleOutsidePointer)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', handleOutsidePointer)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

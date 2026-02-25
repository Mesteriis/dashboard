<template>
  <div class="fx-toggle" role="group" aria-label="Agent FX mode">
    <button
      v-for="option in options"
      :key="option.id"
      type="button"
      class="fx-toggle-btn"
      :class="{ active: fxMode === option.id }"
      :aria-pressed="fxMode === option.id"
      @click="selectMode(option.id)"
    >
      {{ option.label }}
    </button>

    <span v-if="prefersReducedMotion" class="fx-toggle-hint">
      Reduced motion: FX forced to OFF.
    </span>
  </div>
</template>

<script setup lang="ts">
import { useFxMode, type FxMode } from "@/features/composables/useFxMode";

const emit = defineEmits<{
  change: [mode: FxMode];
}>();

const options: ReadonlyArray<{ id: FxMode; label: string }> = [
  { id: "off", label: "OFF" },
  { id: "plasma", label: "PLASMA" },
  { id: "particles", label: "PARTICLES" },
];

const { fxMode, prefersReducedMotion, setFxMode } = useFxMode();

function selectMode(mode: FxMode): void {
  setFxMode(mode, { source: "toggle" });
  emit("change", mode);
}
</script>

<style scoped>
.fx-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.fx-toggle-btn {
  min-width: 88px;
  padding: 8px 12px;
  border-radius: var(--ui-radius);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: 0.73rem;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition:
    border-color 150ms ease,
    color 150ms ease,
    background 150ms ease;
}

.fx-toggle-btn:hover {
  border-color: color-mix(in oklab, var(--border), var(--accent) 46%);
  color: var(--text);
}

.fx-toggle-btn.active {
  border-color: color-mix(in oklab, var(--accent), white 22%);
  background: color-mix(in oklab, var(--accent), transparent 84%);
  color: var(--text);
}

.fx-toggle-hint {
  font-size: 0.68rem;
  color: var(--muted);
  margin-left: 4px;
}
</style>

<template>
  <article class="ui-showcase-node ui-kit-node">
    <p class="ui-showcase-node__group">Group: {{ groupLabel }}</p>
    <h3 class="ui-showcase-node__title">Element: {{ elementLabel }}</h3>

    <div class="ui-showcase-node__content">
      <slot />
    </div>

    <div class="ui-showcase-node__output">
      <slot name="output">
        <div class="ui-showcase-node__output-row">
          <strong>value</strong>
          <code>{{ formattedValue }}</code>
        </div>
        <div class="ui-showcase-node__output-row">
          <strong>type</strong>
          <code>{{ resolvedType }}</code>
        </div>
      </slot>
    </div>

    <div class="ui-showcase-node__api">
      <section class="ui-showcase-node__api-group">
        <h4>props</h4>
        <div class="ui-showcase-node__chips">
          <code
            v-for="item in apiProps"
            :key="`prop-${item}`"
            class="ui-showcase-node__chip"
          >
            {{ item }}
          </code>
        </div>
      </section>
      <section class="ui-showcase-node__api-group">
        <h4>slots</h4>
        <div class="ui-showcase-node__chips">
          <code
            v-for="item in apiSlots"
            :key="`slot-${item}`"
            class="ui-showcase-node__chip"
          >
            {{ item }}
          </code>
        </div>
      </section>
      <section class="ui-showcase-node__api-group">
        <h4>signals</h4>
        <div class="ui-showcase-node__chips">
          <code
            v-for="item in apiSignals"
            :key="`signal-${item}`"
            class="ui-showcase-node__chip"
          >
            {{ item }}
          </code>
        </div>
      </section>
      <section class="ui-showcase-node__api-group">
        <h4>model</h4>
        <div class="ui-showcase-node__chips">
          <code
            v-for="item in apiModel"
            :key="`model-${item}`"
            class="ui-showcase-node__chip"
          >
            {{ item }}
          </code>
        </div>
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ShowcaseNodeApi } from "@/views/ui-showcase/showcaseNodeApi";

const props = defineProps<{
  groupLabel: string;
  elementLabel: string;
  value?: unknown;
  typeLabel?: string;
  api?: ShowcaseNodeApi;
}>();

const apiProps = computed(() =>
  props.api?.props && props.api.props.length ? props.api.props : ["none"],
);

const apiSlots = computed(() =>
  props.api?.slots && props.api.slots.length ? props.api.slots : ["none"],
);

const apiSignals = computed(() =>
  props.api?.signals && props.api.signals.length ? props.api.signals : ["none"],
);

const apiModel = computed(() =>
  props.api?.model && props.api.model.length ? props.api.model : ["none"],
);

const resolvedType = computed(() => {
  if (props.typeLabel) return props.typeLabel;

  const rawValue = props.value;
  if (rawValue === null) return "null";
  if (rawValue === undefined) return "n/a";
  if (Array.isArray(rawValue)) return "array";
  if (typeof rawValue === "number") {
    return Number.isInteger(rawValue) ? "int" : "number";
  }
  if (typeof rawValue === "object") return "object";
  return typeof rawValue;
});

const formattedValue = computed(() => {
  const rawValue = props.value;
  if (rawValue === undefined) return "n/a";
  if (rawValue === null) return "null";
  if (typeof rawValue === "string") return `"${rawValue}"`;
  if (typeof rawValue === "number" || typeof rawValue === "boolean" || typeof rawValue === "bigint") {
    return String(rawValue);
  }

  try {
    const serialized = JSON.stringify(rawValue);
    if (!serialized) return "n/a";
    return serialized.length > 180 ? `${serialized.slice(0, 177)}...` : serialized;
  } catch {
    return "[unserializable]";
  }
});
</script>

<style scoped>
.ui-showcase-node.ui-kit-node {
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
  display: grid;
  gap: 10px;
}

.ui-showcase-node__group {
  margin: 0;
  color: #9fc4dc;
  font-size: 0.74rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ui-showcase-node__title {
  margin: 0;
}

.ui-showcase-node__content {
  display: grid;
  gap: 8px;
}

.ui-showcase-node__output {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 8px;
  color: #afcbde;
  font-size: 0.82rem;
}

.ui-showcase-node__output-row {
  min-height: 64px;
  border: 1px solid rgba(109, 167, 198, 0.28);
  border-radius: 10px;
  background: rgba(10, 28, 43, 0.58);
  padding: 6px 8px;
  display: grid;
  gap: 3px;
}

.ui-showcase-node__output-row strong {
  color: #9ec4dc;
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ui-showcase-node__output-row code {
  display: block;
  max-height: 44px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: #dff1fd;
}

.ui-showcase-node__api {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  color: #a9c8dd;
  font-size: 0.78rem;
}

.ui-showcase-node__api-group {
  border: 1px solid rgba(109, 167, 198, 0.24);
  border-radius: 10px;
  background: rgba(9, 25, 39, 0.54);
  padding: 7px 8px;
  display: grid;
  align-content: start;
  gap: 6px;
  min-height: 86px;
}

.ui-showcase-node__api-group h4 {
  margin: 0;
  color: #9ec4dc;
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ui-showcase-node__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  max-height: 64px;
  overflow: auto;
  align-content: flex-start;
}

.ui-showcase-node__chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid rgba(120, 181, 215, 0.32);
  background: rgba(14, 37, 55, 0.68);
  color: #d8ecfb;
  font-size: 0.72rem;
  line-height: 1.2;
}

.ui-showcase-node__api code {
  color: #d9eefc;
}

@media (max-width: 940px) {
  .ui-showcase-node__output {
    grid-template-columns: minmax(0, 1fr);
  }

  .ui-showcase-node__api {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

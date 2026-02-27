<template>
  <section
    v-for="block in blocks"
    :key="`${itemId}:${block.plugin_id}`"
    class="item-plugin-zone"
  >
    <p class="item-plugin-title">
      {{ block.title || block.plugin_id }}
    </p>

    <div class="item-plugin-elements">
      <template v-for="element in block.elements" :key="element.id">
        <p v-if="element.kind === 'text'" class="item-plugin-text">
          <span v-if="element.label" class="item-plugin-label">{{
            element.label
          }}</span>
          <span class="item-plugin-value">{{ element.value }}</span>
        </p>

        <span
          v-else-if="element.kind === 'badge'"
          class="item-plugin-badge"
          :class="`tone-${element.tone || 'neutral'}`"
        >
          {{ element.value }}
        </span>

        <div v-else-if="element.kind === 'link'" class="item-plugin-link-row">
          <p class="item-plugin-link-label">{{ element.label }}</p>
          <div class="item-plugin-link-actions">
            <button
              class="ghost"
              type="button"
              @click.stop="
                emit('open-link', element.url, element.open || 'new_tab')
              "
            >
              Открыть
            </button>
            <button
              class="ghost"
              type="button"
              @click.stop="emit('copy-link', element.url)"
            >
              Копировать
            </button>
          </div>
        </div>

        <article
          v-else-if="element.kind === 'html'"
          class="item-plugin-html-block"
        >
          <iframe
            v-if="element.trust === 'server_sanitized_v1'"
            class="item-plugin-html-frame"
            sandbox=""
            :srcdoc="element.html"
            title="Plugin HTML extension"
          ></iframe>
          <p v-else class="item-plugin-html-denied">
            HTML extension denied by default security policy.
          </p>
        </article>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import type {
  ServiceCardOpenV1,
  ServiceCardPluginBlockV1,
} from "@/shared/contracts/serviceCard";

defineProps<{
  itemId: string;
  blocks: ServiceCardPluginBlockV1[];
}>();

const emit = defineEmits<{
  "open-link": [url: string, open: ServiceCardOpenV1];
  "copy-link": [value: string];
}>();
</script>

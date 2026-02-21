<template>
  <article
    class="item-card"
    :class="{ selected: !isIconCardView && isItemSelected(item.id), compact: isIconCardView }"
    :title="isIconCardView ? item.title : undefined"
    @click="onItemCardClick(groupKey, subgroupId, item)"
  >
    <template v-if="isIconCardView">
      <div class="item-compact-body">
        <img
          v-if="itemFaviconSrc(item)"
          :src="itemFaviconSrc(item)"
          class="service-favicon compact-item-favicon"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markItemFaviconFailed(item)"
        />
        <component v-else :is="resolveItemIcon(item)" class="ui-icon item-icon compact-item-icon" />
        <span class="health-dot compact-health-dot" :class="healthClass(item.id)"></span>
      </div>
    </template>

    <template v-else>
      <div class="item-head">
        <div class="item-title-row">
          <img
            v-if="itemFaviconSrc(item)"
            :src="itemFaviconSrc(item)"
            class="service-favicon item-favicon"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="markItemFaviconFailed(item)"
          />
          <component v-else :is="resolveItemIcon(item)" class="ui-icon item-icon" />
          <h4>{{ item.title }}</h4>
        </div>
        <span class="item-type">{{ item.type }}</span>
      </div>

      <p class="item-url">{{ item.url }}</p>

      <div class="item-health">
        <span class="health-dot" :class="healthClass(item.id)"></span>
        <span class="health-text">{{ healthLabel(item.id) }}</span>
      </div>

      <div v-if="item.tags?.length" class="item-tags">
        <span v-for="tag in item.tags" :key="tag" class="tag-pill">{{ tag }}</span>
      </div>

      <div class="item-actions">
        <IconButton :title="item.type === 'iframe' ? 'Открыть iframe' : 'Открыть'" :aria-label="item.type === 'iframe' ? 'Открыть iframe' : 'Открыть'" @click.stop="openItem(item)">
          <component :is="item.type === 'iframe' ? Globe : Link2" class="ui-icon item-action-icon" />
        </IconButton>
        <IconButton title="Копировать URL" aria-label="Копировать URL" @click.stop="copyUrl(item.url)">
          <Copy class="ui-icon item-action-icon" />
        </IconButton>
      </div>
    </template>
  </article>
</template>

<script setup>
import { Copy, Globe, Link2 } from 'lucide-vue-next'
import IconButton from '../primitives/IconButton.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

defineProps({
  groupKey: {
    type: String,
    required: true,
  },
  subgroupId: {
    type: String,
    required: true,
  },
  item: {
    type: Object,
    required: true,
  },
})

const dashboard = useDashboardStore()

const {
  isIconCardView,
  isItemSelected,
  onItemCardClick,
  itemFaviconSrc,
  markItemFaviconFailed,
  resolveItemIcon,
  healthClass,
  healthLabel,
  openItem,
  copyUrl,
} = dashboard
</script>

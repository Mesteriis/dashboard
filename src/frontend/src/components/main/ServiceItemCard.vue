<template>
  <article
    class="item-card"
    :class="itemCardClasses"
    :title="isCompactServiceCardView ? item.title : undefined"
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
        <span class="health-dot compact-health-dot" :class="healthVisualClass"></span>
      </div>
    </template>

    <template v-else-if="isTileCardView">
      <div class="item-tile-head">
        <img
          v-if="itemFaviconSrc(item)"
          :src="itemFaviconSrc(item)"
          class="service-favicon tile-item-favicon"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markItemFaviconFailed(item)"
        />
        <component v-else :is="resolveItemIcon(item)" class="ui-icon item-icon tile-item-icon" />
        <span class="health-dot tile-health-dot" :class="healthVisualClass"></span>
      </div>
      <p class="item-tile-title">{{ item.title }}</p>
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
        <span class="health-dot" :class="healthVisualClass"></span>
        <span class="health-text" :class="{ 'is-updating': healthFlashActive }">{{ healthLabelText }}</span>
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
import { computed, onBeforeUnmount, ref, toRef, watch } from 'vue'
import { Copy, Globe, Link2 } from 'lucide-vue-next'
import IconButton from '../primitives/IconButton.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const props = defineProps({
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
const groupKey = toRef(props, 'groupKey')
const subgroupId = toRef(props, 'subgroupId')
const item = toRef(props, 'item')

const dashboard = useDashboardStore()

const {
  isIconCardView,
  isTileCardView,
  isCompactServiceCardView,
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

const healthVisualClass = computed(() => healthClass(item.value.id))
const healthLabelText = computed(() => healthLabel(item.value.id))
const healthFlashActive = ref(false)
const dataSweepActive = ref(false)
let healthFlashTimer = 0
let dataSweepTimer = 0

const itemCardClasses = computed(() => ({
  selected: !isCompactServiceCardView.value && isItemSelected(item.value.id),
  compact: isCompactServiceCardView.value,
  tile: isTileCardView.value,
  [`status-${healthVisualClass.value}`]: true,
  'data-updated': dataSweepActive.value,
}))

function triggerHealthFlash() {
  if (healthFlashTimer) {
    clearTimeout(healthFlashTimer)
  }
  healthFlashActive.value = false
  window.requestAnimationFrame(() => {
    healthFlashActive.value = true
    healthFlashTimer = window.setTimeout(() => {
      healthFlashActive.value = false
      healthFlashTimer = 0
    }, 900)
  })
}

function triggerDataSweep() {
  if (dataSweepTimer) {
    clearTimeout(dataSweepTimer)
  }
  dataSweepActive.value = false
  window.requestAnimationFrame(() => {
    dataSweepActive.value = true
    dataSweepTimer = window.setTimeout(() => {
      dataSweepActive.value = false
      dataSweepTimer = 0
    }, 1250)
  })
}

watch([healthVisualClass, healthLabelText], ([nextClass, nextLabel], [prevClass, prevLabel]) => {
  if (prevClass === undefined && prevLabel === undefined) {
    return
  }
  if (nextClass !== prevClass || nextLabel !== prevLabel) {
    triggerDataSweep()
  }
  if (nextLabel !== prevLabel) {
    triggerHealthFlash()
  }
})

onBeforeUnmount(() => {
  if (healthFlashTimer) {
    clearTimeout(healthFlashTimer)
    healthFlashTimer = 0
  }
  if (dataSweepTimer) {
    clearTimeout(dataSweepTimer)
    dataSweepTimer = 0
  }
})
</script>

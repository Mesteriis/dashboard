<template>
  <BaseModal
    :open="iframeModal.open"
    backdrop-class="iframe-modal-backdrop"
    modal-class="iframe-modal"
    @backdrop="closeIframeModal"
  >
    <header class="iframe-modal-header">
      <h3>{{ iframeModal.title }}</h3>
      <button class="ghost" type="button" @click="closeIframeModal">Закрыть</button>
    </header>

    <p v-if="iframeModal.loading" class="subtitle iframe-modal-status">Подготовка iframe...</p>
    <p v-else-if="iframeModal.error" class="widget-error iframe-modal-status">{{ iframeModal.error }}</p>
    <iframe
      v-else
      class="iframe-view"
      :src="iframeModal.src"
      :allow="iframeModal.allow || undefined"
      :sandbox="iframeModal.sandbox ? '' : undefined"
      :referrerpolicy="iframeModal.referrerPolicy || undefined"
    ></iframe>
  </BaseModal>
</template>

<script setup>
import BaseModal from '../primitives/BaseModal.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { iframeModal, closeIframeModal } = dashboard
</script>

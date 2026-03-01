<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="false"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    :header-panel-active="false"
    content-label="Настройки"
  >
    <template #sidebar-mid>
      <SettingsNavigationView v-model:active-section="activeSection" />
    </template>

    <template #canvas-main>
      <main class="settings-main">
        <SettingsAppearanceSection v-if="activeSection === 'appearance'" />
        <SettingsRuntimeSection v-else-if="activeSection === 'runtime'" />
        <SettingsQuickActionsSection v-else-if="activeSection === 'actions'" />
        <SettingsBackupSection v-else-if="activeSection === 'backup'" />
        <SettingsValidationSection v-else-if="activeSection === 'validation'" />
      </main>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
  SIDEBAR_PARTICLES_ID,
} from "@/features/stores/ui/storeConstants";
import { useSidebarParticles } from "@/features/composables/useSidebarParticles";
import SettingsNavigationView from "@/views/settings/SettingsNavigationView.vue";
import SettingsAppearanceSection from "@/views/settings/sections/SettingsAppearanceSection.vue";
import SettingsBackupSection from "@/views/settings/sections/SettingsBackupSection.vue";
import SettingsQuickActionsSection from "@/views/settings/sections/SettingsQuickActionsSection.vue";
import SettingsRuntimeSection from "@/views/settings/sections/SettingsRuntimeSection.vue";
import SettingsValidationSection from "@/views/settings/sections/SettingsValidationSection.vue";

const activeSection = ref("appearance");

useSidebarParticles({
  containerId: SIDEBAR_PARTICLES_ID,
  baseConfig: SIDEBAR_PARTICLES_CONFIG,
  isSidebarHidden: ref(false),
});
</script>

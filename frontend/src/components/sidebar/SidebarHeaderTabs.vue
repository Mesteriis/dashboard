<template>
  <div class="brand brand--with-action">
    <div class="brand-main">
      <img :src="EMBLEM_SRC" alt="Oko" />
      <div>
        <p class="brand-title">{{ appTitle }}</p>
        <p class="brand-subtitle">{{ appTagline }}</p>
      </div>
    </div>

    <div class="brand-action-stack">
      <button
        class="brand-pleiad-btn"
        type="button"
        title="Открыть Pleiad"
        aria-label="Открыть Pleiad"
        @click="openPleiad"
      >
        <Orbit class="ui-icon brand-pleiad-icon" />
        <span>Pleiad</span>
      </button>

      <button
        class="brand-pleiad-btn brand-aura-btn"
        type="button"
        title="Открыть Agent Aura FX"
        aria-label="Открыть Agent Aura FX"
        @click="openAuraDemo"
      >
        <Sparkles class="ui-icon brand-pleiad-icon" />
        <span>Aura FX</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { Orbit, Sparkles } from "lucide-vue-next";
import { dispatchOpenAgentAuraDemo } from "../../services/agentAuraNavigation.js";
import { dispatchOpenPleiad } from "../../services/pleiadNavigation.js";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const { EMBLEM_SRC, appTitle, appTagline } = dashboard;

function openPleiad() {
  dispatchOpenPleiad();
}

function openAuraDemo() {
  dispatchOpenAgentAuraDemo();
}
</script>

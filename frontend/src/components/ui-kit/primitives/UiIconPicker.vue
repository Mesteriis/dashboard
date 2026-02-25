<template>
  <section class="ui-icon-picker">
    <header class="ui-icon-picker__toolbar">
      <label class="ui-icon-picker__field">
        <span>Search icons</span>
        <input
          v-model.trim="searchQuery"
          type="search"
          :placeholder="searchPlaceholder"
          autocomplete="off"
        />
      </label>

      <label class="ui-icon-picker__field ui-icon-picker__field--pack">
        <span>Pack</span>
        <select v-model="activePack">
          <option value="all">All packs</option>
          <option value="tabler">Tabler</option>
          <option value="heroicons">Heroicons</option>
        </select>
      </label>
    </header>

    <div class="ui-icon-picker__meta">
      <p>
        Showing <strong>{{ filteredOptions.length }}</strong> of
        {{ ICON_OPTIONS.length }} icons
      </p>
      <p v-if="selectedOption">
        Selected:
        <code>{{ selectedOption.id }}</code>
      </p>
    </div>

    <div class="ui-icon-picker__list" role="listbox" :aria-label="ariaLabel">
      <button
        v-for="option in filteredOptions"
        :key="option.id"
        type="button"
        class="ui-icon-picker__item"
        role="option"
        :aria-selected="option.id === selectedId"
        :class="{ active: option.id === selectedId }"
        @click="selectIcon(option.id)"
      >
        <component
          :is="option.component"
          class="ui-icon ui-icon-picker__glyph"
        />
        <span class="ui-icon-picker__label">{{ option.label }}</span>
        <small class="ui-icon-picker__pack">{{ option.packLabel }}</small>
      </button>

      <p v-if="!filteredOptions.length" class="ui-icon-picker__empty">
        No icons found for current filters.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Component } from "vue";
import { computed, ref } from "vue";
import {
  IconActivityHeartbeat,
  IconAlarm,
  IconBellRinging,
  IconBolt,
  IconBrandDocker,
  IconBrandGithub,
  IconCloud,
  IconCpu,
  IconDatabase,
  IconFingerprint,
  IconRocket,
  IconShieldCheck,
  IconSparkles,
  IconTerminal2,
  IconTopologyStar3,
  IconWorld,
} from "@tabler/icons-vue";
import {
  AcademicCapIcon,
  ArchiveBoxIcon,
  BeakerIcon,
  BoltIcon as HeroBoltIcon,
  ChartBarSquareIcon,
  CircleStackIcon,
  CloudIcon as HeroCloudIcon,
  CommandLineIcon,
  CpuChipIcon,
  CubeTransparentIcon,
  GlobeAltIcon,
  RocketLaunchIcon,
  ShieldCheckIcon as HeroShieldCheckIcon,
  SparklesIcon as HeroSparklesIcon,
  SwatchIcon,
  WrenchScrewdriverIcon,
} from "@heroicons/vue/24/outline";

type IconPack = "tabler" | "heroicons";

interface IconPickerOption {
  id: string;
  label: string;
  pack: IconPack;
  packLabel: string;
  keywords: string[];
  component: Component;
}

const ICON_OPTIONS: IconPickerOption[] = [
  {
    id: "tabler:activity-heartbeat",
    label: "Activity Heartbeat",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["monitoring", "health", "pulse"],
    component: IconActivityHeartbeat,
  },
  {
    id: "tabler:alarm",
    label: "Alarm",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["clock", "time", "alert"],
    component: IconAlarm,
  },
  {
    id: "tabler:bell-ringing",
    label: "Bell Ringing",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["notification", "alert"],
    component: IconBellRinging,
  },
  {
    id: "tabler:bolt",
    label: "Bolt",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["energy", "flash", "power"],
    component: IconBolt,
  },
  {
    id: "tabler:brand-docker",
    label: "Brand Docker",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["container", "devops", "brand"],
    component: IconBrandDocker,
  },
  {
    id: "tabler:brand-github",
    label: "Brand GitHub",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["repository", "git", "brand"],
    component: IconBrandGithub,
  },
  {
    id: "tabler:cloud",
    label: "Cloud",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["infra", "saas", "storage"],
    component: IconCloud,
  },
  {
    id: "tabler:cpu",
    label: "CPU",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["chip", "compute"],
    component: IconCpu,
  },
  {
    id: "tabler:database",
    label: "Database",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["storage", "sql", "records"],
    component: IconDatabase,
  },
  {
    id: "tabler:fingerprint",
    label: "Fingerprint",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["security", "access", "auth"],
    component: IconFingerprint,
  },
  {
    id: "tabler:rocket",
    label: "Rocket",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["launch", "deploy", "speed"],
    component: IconRocket,
  },
  {
    id: "tabler:shield-check",
    label: "Shield Check",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["security", "protected", "safe"],
    component: IconShieldCheck,
  },
  {
    id: "tabler:sparkles",
    label: "Sparkles",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["magic", "effects", "shine"],
    component: IconSparkles,
  },
  {
    id: "tabler:terminal-2",
    label: "Terminal 2",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["cli", "console", "shell"],
    component: IconTerminal2,
  },
  {
    id: "tabler:topology-star-3",
    label: "Topology Star 3",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["network", "nodes", "topology"],
    component: IconTopologyStar3,
  },
  {
    id: "tabler:world",
    label: "World",
    pack: "tabler",
    packLabel: "Tabler",
    keywords: ["global", "planet", "internet"],
    component: IconWorld,
  },
  {
    id: "heroicons:academic-cap",
    label: "Academic Cap",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["learning", "education"],
    component: AcademicCapIcon,
  },
  {
    id: "heroicons:archive-box",
    label: "Archive Box",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["archive", "box", "history"],
    component: ArchiveBoxIcon,
  },
  {
    id: "heroicons:beaker",
    label: "Beaker",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["lab", "science", "experiment"],
    component: BeakerIcon,
  },
  {
    id: "heroicons:bolt",
    label: "Bolt",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["power", "energy", "flash"],
    component: HeroBoltIcon,
  },
  {
    id: "heroicons:chart-bar-square",
    label: "Chart Bar Square",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["analytics", "report", "metrics"],
    component: ChartBarSquareIcon,
  },
  {
    id: "heroicons:circle-stack",
    label: "Circle Stack",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["database", "stack"],
    component: CircleStackIcon,
  },
  {
    id: "heroicons:cloud",
    label: "Cloud",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["cloud", "infra", "network"],
    component: HeroCloudIcon,
  },
  {
    id: "heroicons:command-line",
    label: "Command Line",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["terminal", "cli", "shell"],
    component: CommandLineIcon,
  },
  {
    id: "heroicons:cpu-chip",
    label: "CPU Chip",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["chip", "hardware", "compute"],
    component: CpuChipIcon,
  },
  {
    id: "heroicons:cube-transparent",
    label: "Cube Transparent",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["3d", "shape", "object"],
    component: CubeTransparentIcon,
  },
  {
    id: "heroicons:globe-alt",
    label: "Globe Alt",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["world", "internet", "global"],
    component: GlobeAltIcon,
  },
  {
    id: "heroicons:rocket-launch",
    label: "Rocket Launch",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["deploy", "launch", "growth"],
    component: RocketLaunchIcon,
  },
  {
    id: "heroicons:shield-check",
    label: "Shield Check",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["security", "safe", "approved"],
    component: HeroShieldCheckIcon,
  },
  {
    id: "heroicons:sparkles",
    label: "Sparkles",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["effects", "shine", "magic"],
    component: HeroSparklesIcon,
  },
  {
    id: "heroicons:swatch",
    label: "Swatch",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["design", "theme", "palette"],
    component: SwatchIcon,
  },
  {
    id: "heroicons:wrench-screwdriver",
    label: "Wrench Screwdriver",
    pack: "heroicons",
    packLabel: "Heroicons",
    keywords: ["tools", "settings", "setup"],
    component: WrenchScrewdriverIcon,
  },
];

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    ariaLabel?: string;
    searchPlaceholder?: string;
  }>(),
  {
    modelValue: "",
    ariaLabel: "Icon picker",
    searchPlaceholder: "Search by name or keyword...",
  },
);

const emit = defineEmits<{
  "update:modelValue": [iconId: string];
}>();

const searchQuery = ref("");
const activePack = ref<IconPack | "all">("all");

const selectedId = computed(() => String(props.modelValue || "").trim());

const filteredOptions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return ICON_OPTIONS.filter((option) => {
    if (activePack.value !== "all" && option.pack !== activePack.value) {
      return false;
    }
    if (!query) return true;
    const haystack = [
      option.id,
      option.label,
      option.packLabel,
      ...option.keywords,
    ].join(" ");
    return haystack.toLowerCase().includes(query);
  });
});

const selectedOption = computed(
  () => ICON_OPTIONS.find((option) => option.id === selectedId.value) || null,
);

function selectIcon(iconId: string): void {
  emit("update:modelValue", iconId);
}
</script>

<style scoped>
.ui-icon-picker {
  display: grid;
  gap: 10px;
}

.ui-icon-picker__toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;
  gap: 8px;
}

.ui-icon-picker__field {
  display: grid;
  gap: 5px;
}

.ui-icon-picker__field span {
  font-size: 0.74rem;
  color: #9ec0d8;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ui-icon-picker__field input,
.ui-icon-picker__field select {
  width: 100%;
  min-height: 36px;
  border-radius: var(--ui-radius);
  border: 1px solid rgba(115, 173, 209, 0.3);
  background: rgba(12, 28, 42, 0.68);
  color: #dbe9f4;
  padding: 8px 10px;
  font: inherit;
}

.ui-icon-picker__field input:focus-visible,
.ui-icon-picker__field select:focus-visible {
  outline: none;
  border-color: rgba(157, 218, 252, 0.62);
  box-shadow: 0 0 0 3px rgba(81, 149, 187, 0.26);
}

.ui-icon-picker__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  color: #a7c5d9;
  font-size: 0.78rem;
}

.ui-icon-picker__meta p {
  margin: 0;
}

.ui-icon-picker__meta code {
  color: #d6e8f6;
}

.ui-icon-picker__list {
  border: 1px solid rgba(100, 159, 193, 0.24);
  border-radius: var(--ui-radius);
  background: linear-gradient(
    150deg,
    rgba(10, 26, 40, 0.6),
    rgba(8, 20, 33, 0.54)
  );
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(116px, 1fr));
  gap: 8px;
  min-height: 180px;
  max-height: 380px;
  overflow-y: auto;
}

.ui-icon-picker__item {
  border: 1px solid rgba(108, 165, 197, 0.22);
  border-radius: var(--ui-radius);
  background: rgba(12, 31, 47, 0.52);
  color: #d8e8f5;
  padding: 8px;
  min-height: 92px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 4px;
  text-align: center;
  cursor: pointer;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    transform 150ms ease;
}

.ui-icon-picker__item:hover {
  border-color: rgba(163, 220, 251, 0.58);
  background: rgba(19, 43, 63, 0.62);
  transform: translateY(-1px);
}

.ui-icon-picker__item.active {
  border-color: rgba(130, 214, 186, 0.68);
  background: linear-gradient(
    165deg,
    rgba(23, 56, 58, 0.6),
    rgba(16, 46, 46, 0.52)
  );
  box-shadow: inset 0 0 0 1px rgba(130, 214, 186, 0.24);
}

.ui-icon-picker__glyph {
  width: 22px;
  height: 22px;
}

.ui-icon-picker__label {
  font-size: 0.75rem;
  line-height: 1.2;
}

.ui-icon-picker__pack {
  font-size: 0.68rem;
  color: #90b4cb;
}

.ui-icon-picker__empty {
  margin: 0;
  color: #95b4c8;
  font-size: 0.82rem;
}

@media (max-width: 720px) {
  .ui-icon-picker__toolbar {
    grid-template-columns: 1fr;
  }

  .ui-icon-picker__field--pack {
    max-width: 240px;
  }
}
</style>

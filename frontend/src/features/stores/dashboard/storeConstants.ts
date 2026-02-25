import type { ParticlesConfig, SidebarViewMode } from "@/features/stores/dashboard/storeTypes";

export const EMBLEM_SRC = "/static/img/emblem-mark.png";
export const EVENTS_STREAM_PATH = "/api/v1/events/stream";
export const EVENT_STREAM_RECONNECT_MS = 2000;
export const DEGRADED_LATENCY_MS = 700;
export const LARGE_INDICATOR_TYPES = new Set(["stat_list", "table"]);
export const DEFAULT_ITEM_URL = "https://example.com";
export const SIDEBAR_PARTICLES_ID = "sidebar-particles";
export const SIDEBAR_PARTICLES_CONFIG: ParticlesConfig = {
  fps_limit: 58,
  particles: {
    number: { value: 88, density: { enable: true, value_area: 700 } },
    color: { value: "#6df6e2" },
    shape: { type: "circle" },
    opacity: { value: 0.36, random: true },
    size: { value: 2.4, random: true },
    line_linked: {
      enable: true,
      distance: 120,
      color: "#2dd4bf",
      opacity: 0.24,
      width: 1.2,
    },
    move: { enable: true, speed: 1.2 },
  },
  interactivity: {
    events: {
      onhover: { enable: false },
      onclick: { enable: false },
      resize: true,
    },
  },
  retina_detect: true,
};

export const SERVICE_PRESENTATION_OPTIONS = Object.freeze([
  { value: "detailed", label: "Карточки" },
  { value: "tile", label: "Плитка" },
  { value: "icon", label: "Значки" },
] as const);

export const SERVICE_GROUPING_OPTIONS = Object.freeze([
  { value: "groups", label: "Только группы" },
  { value: "tags_in_groups", label: "Группы + теги" },
  { value: "tags", label: "Только теги" },
  { value: "flat", label: "Без групп (плитка)" },
] as const);

export const SIDEBAR_VIEW_SEQUENCE: SidebarViewMode[] = [
  "detailed",
  "hidden",
];
export const COMMAND_PALETTE_LIMIT = 18;
export const COMMAND_PALETTE_EMPTY_LIMIT = 10;
export const UI_STATE_STORAGE_KEY = "oko:dashboard-ui-state:v1";
export const SERVICE_CARD_VIEW_VALUES = new Set<string>(
  SERVICE_PRESENTATION_OPTIONS.map((option) => option.value),
);
export const SERVICE_GROUPING_VALUES = new Set<string>(
  SERVICE_GROUPING_OPTIONS.map((option) => option.value),
);

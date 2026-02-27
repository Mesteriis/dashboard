<template>
  <div ref="rootRef" class="ui-icon-picker" :class="{ open, disabled }">
    <button
      ref="triggerRef"
      class="ui-icon-picker__trigger"
      type="button"
      :aria-label="ariaLabel"
      aria-haspopup="dialog"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <span class="ui-icon-picker__trigger-main">
        <span class="ui-icon ui-icon-picker__trigger-glyph" aria-hidden="true">
          <slot name="selected-icon" :option="selectedOption">
            <svg
              v-if="selectedOption && hasSvgGlyph(selectedOption)"
              class="ui-icon-picker__svg"
              xmlns="http://www.w3.org/2000/svg"
              :viewBox="selectedOption.svgViewBox || '0 0 24 24'"
              role="img"
              aria-hidden="true"
              :style="glyphStyle(selectedOption)"
            >
              <g
                v-if="selectedOption.svgBody"
                v-html="selectedOption.svgBody"
              />
              <path v-else :d="selectedOption.svgPath" />
            </svg>
            <template v-else>
              {{ selectedOption ? fallbackPreview(selectedOption) : "IC" }}
            </template>
          </slot>
        </span>
        <span class="ui-icon-picker__trigger-copy">
          <strong>{{ selectedOption?.label || triggerPlaceholder }}</strong>
          <small>
            {{ selectedOption?.pack || "Pick from available icon sets" }}
          </small>
        </span>
      </span>
      <span
        class="ui-icon ui-icon-picker__trigger-caret"
        :class="{ open }"
        aria-hidden="true"
      >
        <slot name="caret" :open="open">▾</slot>
      </span>
    </button>
  </div>

  <Teleport to="body">
    <Transition name="ui-icon-picker-modal-transition">
      <div
        v-if="open"
        class="ui-icon-picker__overlay"
        @click="handleBackdropClick"
      >
        <section
          ref="modalRef"
          class="ui-icon-picker__modal"
          role="dialog"
          aria-modal="true"
          :aria-label="ariaLabel"
          @click.stop
        >
          <header class="ui-icon-picker__modal-header">
            <div class="ui-icon-picker__modal-heading">
              <h3>Icon Picker</h3>
              <p>Global search works across all icon sets.</p>
            </div>
            <button
              type="button"
              class="ui-icon-picker__close"
              aria-label="Close icon picker"
              @click="closePicker"
            >
              ×
            </button>
          </header>

          <label class="ui-icon-picker__search-field">
            <span>Search icons</span>
            <input
              v-model.trim="searchQuery"
              type="search"
              :placeholder="searchPlaceholder"
              autocomplete="off"
            />
          </label>

          <div class="ui-icon-picker__body">
            <aside class="ui-icon-picker__sidebar">
              <div class="ui-icon-picker__sidebar-head">
                <h4>Icon sets</h4>
                <small>Pick a set in tree or search globally.</small>
              </div>

              <div class="ui-icon-picker__tree-wrap">
                <UiTree
                  :nodes="setTreeNodes"
                  :model-value="activeSetNode"
                  :default-expanded="treeDefaultExpanded"
                  @update:model-value="handleSetNodeSelect"
                />
              </div>

              <div class="ui-icon-picker__sidebar-meta">
                <p>
                  Built-in loaded:
                  <strong
                    >{{ loadedBuiltinSetsCount }} /
                    {{ builtinSetsTotalCount }}</strong
                  >
                </p>
                <p v-if="loadingBuiltinSetIds.length > 0">
                  Loading sets:
                  <strong>{{ loadingBuiltinSetIds.length }}</strong>
                </p>
              </div>
            </aside>

            <section class="ui-icon-picker__content">
              <div class="ui-icon-picker__meta">
                <p>
                  Showing <strong>{{ filteredOptions.length }}</strong> of
                  {{ normalizedOptions.length }} icons
                </p>
                <p v-if="downloadedIconCount > 0">
                  Downloaded sets: <strong>{{ downloadedIconCount }}</strong>
                </p>
                <p v-if="selectedOption">
                  Selected:
                  <code>{{ selectedOption.id }}</code>
                </p>
                <p v-if="isGlobalSearchMode">
                  Search mode: <strong>all icon sets</strong>
                </p>
              </div>

              <div
                class="ui-icon-picker__list"
                role="listbox"
                :aria-label="ariaLabel"
                :style="{ maxHeight: `${listMaxHeight}px` }"
              >
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
                  <span
                    class="ui-icon ui-icon-picker__glyph"
                    aria-hidden="true"
                  >
                    <slot name="icon" :option="option">
                      <svg
                        v-if="hasSvgGlyph(option)"
                        class="ui-icon-picker__svg"
                        xmlns="http://www.w3.org/2000/svg"
                        :viewBox="option.svgViewBox || '0 0 24 24'"
                        role="img"
                        aria-hidden="true"
                        :style="glyphStyle(option)"
                      >
                        <g v-if="option.svgBody" v-html="option.svgBody" />
                        <path v-else :d="option.svgPath" />
                      </svg>
                      <template v-else>
                        {{ fallbackPreview(option) }}
                      </template>
                    </slot>
                  </span>
                  <span class="ui-icon-picker__label">{{ option.label }}</span>
                  <small class="ui-icon-picker__pack">{{ option.pack }}</small>
                  <small
                    v-if="option.source === 'downloaded'"
                    class="ui-icon-picker__source"
                  >
                    downloaded
                  </small>
                </button>

                <p v-if="!filteredOptions.length" class="ui-icon-picker__empty">
                  No icons found for current filters.
                </p>
              </div>
            </section>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UiTree from "@/primitives/data/UiTree.vue";
import {
  BUILTIN_ICON_SET_CATALOG,
  DEFAULT_BUILTIN_ICON_SET_ID,
  guessBuiltinSetIdByIconId,
  loadBuiltinIconSet,
  loadBuiltinIconSets,
  type BuiltinIconPickerSet,
} from "@/shared/iconsets/defaultIconSets";

export interface IconPickerOption {
  id: string;
  label: string;
  pack?: string;
  keywords?: string[];
  preview?: string;
  svgPath?: string;
  svgBody?: string;
  svgViewBox?: string;
  svgColor?: string;
}

export interface IconPickerSet {
  id: string;
  label?: string;
  options: IconPickerOption[];
}

type IconPickerSource = "builtin" | "icon-set" | "downloaded";

type SetFilterNodeId =
  | "all"
  | "group:builtin"
  | "group:custom"
  | "group:downloaded"
  | string;

interface TreeNode {
  id: string;
  label: string;
  children?: TreeNode[];
}

interface NormalizedIconOption {
  id: string;
  label: string;
  pack: string;
  keywords: string[];
  preview: string;
  svgPath: string;
  svgBody: string;
  svgViewBox: string;
  svgColor: string;
  source: IconPickerSource;
  setId: string;
}

interface SetMeta {
  id: string;
  label: string;
  source: IconPickerSource;
  loaded?: boolean;
}

const LOCAL_OPTIONS_SET_ID = "builtin:starter";

const DEFAULT_ICON_OPTIONS: IconPickerOption[] = [];

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    options?: IconPickerOption[];
    iconSets?: IconPickerSet[];
    downloadedIconSets?: IconPickerSet[];
    excludeSetIds?: string[];
    excludeIconIds?: string[];
    includeDefaultOptions?: boolean;
    disabled?: boolean;
    closeOnSelect?: boolean;
    panelMaxHeight?: number;
    ariaLabel?: string;
    searchPlaceholder?: string;
    triggerPlaceholder?: string;
  }>(),
  {
    modelValue: "",
    options: () => [],
    iconSets: () => [],
    downloadedIconSets: () => [],
    excludeSetIds: () => [],
    excludeIconIds: () => [],
    includeDefaultOptions: true,
    disabled: false,
    closeOnSelect: true,
    panelMaxHeight: 560,
    ariaLabel: "Icon picker",
    searchPlaceholder: "Search by name or keyword...",
    triggerPlaceholder: "Select icon",
  },
);

const emit = defineEmits<{
  "update:modelValue": [iconId: string];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLButtonElement | null>(null);
const modalRef = ref<HTMLElement | null>(null);
const searchQuery = ref("");
const activeSetNode = ref<SetFilterNodeId>("all");
const loadedBuiltinSetMap = ref<Record<string, BuiltinIconPickerSet>>({});
const loadingBuiltinSetIds = ref<string[]>([]);

const treeDefaultExpanded = [
  "group:builtin",
  "group:custom",
  "group:downloaded",
];

const selectedId = computed(() => String(props.modelValue || "").trim());
const listMaxHeight = computed(() =>
  Math.max(320, Number(props.panelMaxHeight) || 560),
);
const isGlobalSearchMode = computed(() => searchQuery.value.trim().length > 0);

const excludedSetIds = computed(
  () =>
    new Set(
      (props.excludeSetIds || []).map((setId) => String(setId || "").trim()),
    ),
);

const excludedIconIds = computed(
  () =>
    new Set(
      (props.excludeIconIds || []).map((iconId) => String(iconId || "").trim()),
    ),
);

const starterOptions = computed(() => [
  ...(props.includeDefaultOptions ? DEFAULT_ICON_OPTIONS : []),
  ...props.options,
]);

const builtinSetMetas = computed<SetMeta[]>(() => {
  const metas: SetMeta[] = [];

  if (
    !excludedSetIds.value.has(LOCAL_OPTIONS_SET_ID) &&
    starterOptions.value.length > 0
  ) {
    metas.push({
      id: LOCAL_OPTIONS_SET_ID,
      label: "Starter",
      source: "builtin",
      loaded: true,
    });
  }

  if (!props.includeDefaultOptions) {
    return metas;
  }

  for (const catalogEntry of BUILTIN_ICON_SET_CATALOG) {
    if (excludedSetIds.value.has(catalogEntry.id)) continue;
    metas.push({
      id: catalogEntry.id,
      label: catalogEntry.label,
      source: "builtin",
      loaded: Boolean(loadedBuiltinSetMap.value[catalogEntry.id]),
    });
  }

  return metas;
});

const customSetMetas = computed<SetMeta[]>(() =>
  props.iconSets
    .map((set, index) => {
      const id = String(set.id || `icon-set-${index + 1}`).trim();
      return {
        id,
        label: String(set.label || id || `Icon Set ${index + 1}`).trim(),
        source: "icon-set" as const,
        loaded: true,
      };
    })
    .filter((set) => Boolean(set.id) && !excludedSetIds.value.has(set.id)),
);

const downloadedSetMetas = computed<SetMeta[]>(() =>
  props.downloadedIconSets
    .map((set, index) => {
      const id = String(set.id || `downloaded-${index + 1}`).trim();
      return {
        id,
        label: String(set.label || id || `Downloaded ${index + 1}`).trim(),
        source: "downloaded" as const,
        loaded: true,
      };
    })
    .filter((set) => Boolean(set.id) && !excludedSetIds.value.has(set.id)),
);

const sourceSets = computed<
  Array<{
    id: string;
    source: IconPickerSource;
    options: IconPickerOption[];
  }>
>(() => {
  const result: Array<{
    id: string;
    source: IconPickerSource;
    options: IconPickerOption[];
  }> = [];

  if (
    !excludedSetIds.value.has(LOCAL_OPTIONS_SET_ID) &&
    starterOptions.value.length > 0
  ) {
    result.push({
      id: LOCAL_OPTIONS_SET_ID,
      source: "builtin",
      options: starterOptions.value,
    });
  }

  if (props.includeDefaultOptions) {
    for (const catalogEntry of BUILTIN_ICON_SET_CATALOG) {
      if (excludedSetIds.value.has(catalogEntry.id)) continue;
      const loadedSet = loadedBuiltinSetMap.value[catalogEntry.id];
      if (!loadedSet) continue;
      result.push({
        id: catalogEntry.id,
        source: "builtin",
        options: loadedSet.options || [],
      });
    }
  }

  for (const setMeta of customSetMetas.value) {
    const sourceSet = props.iconSets.find(
      (set) => String(set.id || "").trim() === setMeta.id,
    );
    if (!sourceSet) continue;
    result.push({
      id: setMeta.id,
      source: "icon-set",
      options: sourceSet.options || [],
    });
  }

  for (const setMeta of downloadedSetMetas.value) {
    const sourceSet = props.downloadedIconSets.find(
      (set) => String(set.id || "").trim() === setMeta.id,
    );
    if (!sourceSet) continue;
    result.push({
      id: setMeta.id,
      source: "downloaded",
      options: sourceSet.options || [],
    });
  }

  return result;
});

const normalizedOptions = computed<NormalizedIconOption[]>(() => {
  const options: NormalizedIconOption[] = [];
  const seenIds = new Set<string>();

  for (const sourceSet of sourceSets.value) {
    for (const rawOption of sourceSet.options) {
      const id = String(rawOption?.id || "").trim();
      if (!id || excludedIconIds.value.has(id) || seenIds.has(id)) continue;

      const label = String(rawOption?.label || id).trim() || id;
      const pack =
        String(rawOption?.pack || sourceSet.id || "custom").trim() || "custom";
      const keywords = (rawOption?.keywords || [])
        .map((keyword) => String(keyword || "").trim())
        .filter(Boolean);

      options.push({
        id,
        label,
        pack,
        keywords,
        preview: String(rawOption?.preview || "").trim(),
        svgPath: String(rawOption?.svgPath || "").trim(),
        svgBody: String(rawOption?.svgBody || "").trim(),
        svgViewBox: String(rawOption?.svgViewBox || "").trim() || "0 0 24 24",
        svgColor: String(rawOption?.svgColor || "").trim(),
        source: sourceSet.source,
        setId: sourceSet.id,
      });
      seenIds.add(id);
    }
  }

  return options;
});

const optionCountBySet = computed(() => {
  const counts = new Map<string, number>();
  for (const option of normalizedOptions.value) {
    counts.set(option.setId, (counts.get(option.setId) || 0) + 1);
  }
  return counts;
});

function formatSetLabel(meta: SetMeta): string {
  const count = optionCountBySet.value.get(meta.id);
  if (typeof count === "number") {
    return `${meta.label} (${count})`;
  }
  if (meta.source === "builtin" && !meta.loaded) {
    return `${meta.label} (lazy)`;
  }
  return meta.label;
}

const setTreeNodes = computed<TreeNode[]>(() => {
  const nodes: TreeNode[] = [
    {
      id: "all",
      label: `All icon sets (${normalizedOptions.value.length})`,
    },
  ];

  const builtinNodes = builtinSetMetas.value.map((meta) => ({
    id: meta.id,
    label: formatSetLabel(meta),
  }));

  if (builtinNodes.length > 0) {
    nodes.push({
      id: "group:builtin",
      label: "Built-in",
      children: builtinNodes,
    });
  }

  const customNodes = customSetMetas.value.map((meta) => ({
    id: meta.id,
    label: formatSetLabel(meta),
  }));

  if (customNodes.length > 0) {
    nodes.push({
      id: "group:custom",
      label: "Custom",
      children: customNodes,
    });
  }

  const downloadedNodes = downloadedSetMetas.value.map((meta) => ({
    id: meta.id,
    label: formatSetLabel(meta),
  }));

  if (downloadedNodes.length > 0) {
    nodes.push({
      id: "group:downloaded",
      label: "Downloaded",
      children: downloadedNodes,
    });
  }

  return nodes;
});

function matchesSetNodeFilter(
  option: NormalizedIconOption,
  nodeId: SetFilterNodeId,
): boolean {
  if (nodeId === "all") return true;
  if (nodeId === "group:builtin") return option.source === "builtin";
  if (nodeId === "group:custom") return option.source === "icon-set";
  if (nodeId === "group:downloaded") return option.source === "downloaded";
  return option.setId === nodeId;
}

const filteredOptions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();

  return normalizedOptions.value.filter((option) => {
    if (!query && !matchesSetNodeFilter(option, activeSetNode.value)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const haystack = [
      option.id,
      option.label,
      option.pack,
      option.setId,
      ...option.keywords,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

const selectedOption = computed(
  () =>
    normalizedOptions.value.find((option) => option.id === selectedId.value) ||
    null,
);

const downloadedIconCount = computed(
  () =>
    normalizedOptions.value.filter((option) => option.source === "downloaded")
      .length,
);

const builtinSetsTotalCount = computed(() => BUILTIN_ICON_SET_CATALOG.length);

const loadedBuiltinSetsCount = computed(
  () =>
    BUILTIN_ICON_SET_CATALOG.filter((entry) =>
      Boolean(loadedBuiltinSetMap.value[entry.id]),
    ).length,
);

function fallbackPreview(option: { preview?: string; label: string }): string {
  const preview = String(option.preview || "").trim();
  if (preview) return preview;

  return (
    option.label
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((chunk) => chunk[0]?.toUpperCase() || "")
      .join("") || "IC"
  );
}

function hasSvgGlyph(
  option: Pick<NormalizedIconOption, "svgPath" | "svgBody"> | null | undefined,
): boolean {
  return Boolean(option?.svgPath || option?.svgBody);
}

function glyphStyle(
  option: Pick<NormalizedIconOption, "svgColor"> | null | undefined,
): Record<string, string> | undefined {
  if (!option?.svgColor) return undefined;
  return { color: option.svgColor };
}

function addLoadedBuiltinSet(set: BuiltinIconPickerSet): void {
  loadedBuiltinSetMap.value = {
    ...loadedBuiltinSetMap.value,
    [set.id]: set,
  };
}

function markBuiltinSetLoading(setId: string): void {
  if (loadingBuiltinSetIds.value.includes(setId)) return;
  loadingBuiltinSetIds.value = [...loadingBuiltinSetIds.value, setId];
}

function unmarkBuiltinSetLoading(setId: string): void {
  loadingBuiltinSetIds.value = loadingBuiltinSetIds.value.filter(
    (entry) => entry !== setId,
  );
}

function isBuiltinSetLoaded(setId: string): boolean {
  return Boolean(loadedBuiltinSetMap.value[setId]);
}

function resolvePreferredBuiltinSetId(): string {
  const bySelectedIcon = guessBuiltinSetIdByIconId(selectedId.value);
  if (bySelectedIcon && !excludedSetIds.value.has(bySelectedIcon)) {
    return bySelectedIcon;
  }

  const firstAvailableBuiltin = BUILTIN_ICON_SET_CATALOG.find(
    (entry) => !excludedSetIds.value.has(entry.id),
  )?.id;

  return firstAvailableBuiltin || DEFAULT_BUILTIN_ICON_SET_ID;
}

function resolveInitialSetNode(): SetFilterNodeId {
  const bySelectedIcon = guessBuiltinSetIdByIconId(selectedId.value);
  if (bySelectedIcon && !excludedSetIds.value.has(bySelectedIcon)) {
    return bySelectedIcon;
  }

  if (
    !excludedSetIds.value.has(LOCAL_OPTIONS_SET_ID) &&
    starterOptions.value.length > 0
  ) {
    return LOCAL_OPTIONS_SET_ID;
  }

  return "all";
}

async function ensureBuiltinSetLoaded(setId: string | null): Promise<void> {
  if (!props.includeDefaultOptions) return;

  const normalizedSetId = String(setId || "").trim();
  if (!normalizedSetId) return;
  if (excludedSetIds.value.has(normalizedSetId)) return;
  if (isBuiltinSetLoaded(normalizedSetId)) return;
  if (loadingBuiltinSetIds.value.includes(normalizedSetId)) return;

  markBuiltinSetLoading(normalizedSetId);
  try {
    const iconSet = await loadBuiltinIconSet(normalizedSetId);
    if (!iconSet) return;
    addLoadedBuiltinSet(iconSet);
  } finally {
    unmarkBuiltinSetLoading(normalizedSetId);
  }
}

async function ensureAllBuiltinSetsLoaded(): Promise<void> {
  if (!props.includeDefaultOptions) return;

  const targetSetIds = BUILTIN_ICON_SET_CATALOG.map((entry) => entry.id).filter(
    (setId) => !excludedSetIds.value.has(setId),
  );

  const pendingSetIds = targetSetIds.filter(
    (setId) =>
      !isBuiltinSetLoaded(setId) && !loadingBuiltinSetIds.value.includes(setId),
  );

  if (!pendingSetIds.length) return;

  for (const setId of pendingSetIds) {
    markBuiltinSetLoading(setId);
  }

  try {
    const loadedSets = await loadBuiltinIconSets(pendingSetIds);
    for (const set of loadedSets) {
      addLoadedBuiltinSet(set);
    }
  } finally {
    for (const setId of pendingSetIds) {
      unmarkBuiltinSetLoading(setId);
    }
  }
}

async function ensureBuiltinSetsForCurrentContext(): Promise<void> {
  if (!open.value || !props.includeDefaultOptions) return;

  if (isGlobalSearchMode.value) {
    await ensureAllBuiltinSetsLoaded();
    return;
  }

  const activeNode = activeSetNode.value;

  if (
    activeNode.startsWith("builtin:") &&
    activeNode !== LOCAL_OPTIONS_SET_ID
  ) {
    await ensureBuiltinSetLoaded(activeNode);
    return;
  }

  if (activeNode === "group:builtin" || activeNode === "all") {
    await ensureBuiltinSetLoaded(resolvePreferredBuiltinSetId());
  }
}

function closePicker(): void {
  open.value = false;
}

function openPicker(): void {
  if (props.disabled) return;
  activeSetNode.value = resolveInitialSetNode();
  open.value = true;
}

function toggleOpen(): void {
  if (open.value) {
    closePicker();
    return;
  }
  openPicker();
}

function handleSetNodeSelect(nodeId: string): void {
  activeSetNode.value = nodeId as SetFilterNodeId;
}

function selectIcon(iconId: string): void {
  emit("update:modelValue", iconId);
  if (props.closeOnSelect) {
    closePicker();
  }
}

function handleBackdropClick(event: MouseEvent): void {
  if (event.target === event.currentTarget) {
    closePicker();
  }
}

function handleWindowKeydown(event: KeyboardEvent): void {
  if (!open.value) return;
  if (event.key === "Escape") {
    closePicker();
  }
}

watch(open, (isOpen) => {
  if (!isOpen) return;
  void ensureBuiltinSetsForCurrentContext();
});

watch(activeSetNode, () => {
  if (!open.value) return;
  void ensureBuiltinSetsForCurrentContext();
});

watch(searchQuery, () => {
  if (!open.value) return;
  if (!isGlobalSearchMode.value) return;
  void ensureAllBuiltinSetsLoaded();
});

watch(
  selectedId,
  () => {
    const setId = guessBuiltinSetIdByIconId(selectedId.value);
    if (setId) {
      void ensureBuiltinSetLoaded(setId);
    }
  },
  { immediate: true },
);

onMounted(() => {
  if (typeof window === "undefined") return;
  window.addEventListener("keydown", handleWindowKeydown);
});

onBeforeUnmount(() => {
  if (typeof window === "undefined") return;
  window.removeEventListener("keydown", handleWindowKeydown);
});
</script>

<style scoped>
.ui-icon-picker {
  position: relative;
  display: grid;
  gap: 8px;
}

.ui-icon-picker__trigger {
  width: 100%;
  border: none;
  border-radius: var(--ui-radius);
  background: rgba(12, 28, 42, 0.68);
  color: #dbe9f4;
  min-height: 44px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
}

.ui-icon-picker__trigger:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.ui-icon-picker__trigger:focus-visible {
  outline: none;
  box-shadow: none;
}

.ui-icon-picker__trigger-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.ui-icon-picker__trigger-glyph {
  width: 24px;
  height: 24px;
  display: inline-grid;
  place-items: center;
  font-size: 0.7rem;
  line-height: 1;
  letter-spacing: 0.03em;
  font-weight: 700;
  border: none;
  border-radius: 8px;
  background: rgba(8, 20, 33, 0.72);
}

.ui-icon-picker__trigger-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
  text-align: left;
}

.ui-icon-picker__trigger-copy strong {
  font-size: 0.84rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ui-icon-picker__trigger-copy small {
  color: rgba(164, 197, 220, 0.82);
  font-size: 0.72rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ui-icon-picker__trigger-caret {
  transition: transform 150ms ease;
}

.ui-icon-picker__trigger-caret.open {
  transform: rotate(180deg);
}

.ui-icon-picker__overlay {
  position: fixed;
  inset: 0;
  z-index: 1900;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(3, 12, 21, 0.7);
  backdrop-filter: blur(3px);
}

.ui-icon-picker__modal {
  width: min(1320px, calc(100vw - 32px));
  height: min(860px, calc(100vh - 32px));
  border-radius: calc(var(--ui-radius) + 6px);
  border: 1px solid rgba(105, 164, 193, 0.28);
  background: linear-gradient(
    150deg,
    rgba(9, 25, 39, 0.96),
    rgba(7, 19, 31, 0.94)
  );
  box-shadow: 0 26px 54px rgba(2, 9, 15, 0.58);
  padding: 16px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
}

.ui-icon-picker__modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ui-icon-picker__modal-heading h3 {
  margin: 0;
  font-size: 1rem;
  color: #dceaf6;
}

.ui-icon-picker__modal-heading p {
  margin: 4px 0 0;
  color: rgba(165, 197, 220, 0.82);
  font-size: 0.76rem;
}

.ui-icon-picker__close {
  border: 1px solid rgba(113, 171, 204, 0.34);
  background: rgba(13, 31, 47, 0.74);
  color: #dcecf8;
  border-radius: 10px;
  width: 34px;
  height: 34px;
  font-size: 1.05rem;
  line-height: 1;
  cursor: pointer;
}

.ui-icon-picker__close:hover {
  border-color: rgba(163, 220, 251, 0.58);
}

.ui-icon-picker__search-field {
  display: grid;
  gap: 5px;
}

.ui-icon-picker__search-field span {
  font-size: 0.74rem;
  color: #9ec0d8;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ui-icon-picker__search-field input {
  width: 100%;
  min-height: 40px;
  border-radius: var(--ui-radius);
  border: 1px solid rgba(115, 173, 209, 0.3);
  background: rgba(12, 28, 42, 0.68);
  color: #dbe9f4;
  padding: 8px 12px;
  font: inherit;
}

.ui-icon-picker__search-field input:focus-visible {
  outline: none;
  border-color: rgba(157, 218, 252, 0.62);
  box-shadow: 0 0 0 3px rgba(81, 149, 187, 0.26);
}

.ui-icon-picker__body {
  min-height: 0;
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  gap: 12px;
}

.ui-icon-picker__sidebar {
  border: 1px solid rgba(106, 165, 198, 0.24);
  border-radius: calc(var(--ui-radius) + 2px);
  background: rgba(10, 26, 40, 0.62);
  padding: 10px;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 10px;
}

.ui-icon-picker__sidebar-head {
  display: grid;
  gap: 4px;
}

.ui-icon-picker__sidebar-head h4 {
  margin: 0;
  color: #dce9f6;
  font-size: 0.88rem;
}

.ui-icon-picker__sidebar-head small {
  color: rgba(160, 194, 218, 0.82);
  font-size: 0.72rem;
}

.ui-icon-picker__tree-wrap {
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.ui-icon-picker__tree-wrap :deep(.ui-tree__node) {
  border-radius: 9px;
  margin-bottom: 2px;
}

.ui-icon-picker__sidebar-meta {
  border-top: 1px solid rgba(107, 166, 200, 0.2);
  padding-top: 8px;
  display: grid;
  gap: 4px;
  color: #9ec0d8;
  font-size: 0.74rem;
}

.ui-icon-picker__sidebar-meta p {
  margin: 0;
}

.ui-icon-picker__content {
  min-height: 0;
  border: 1px solid rgba(106, 165, 198, 0.24);
  border-radius: calc(var(--ui-radius) + 2px);
  background: rgba(10, 24, 38, 0.6);
  padding: 10px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
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
  border: none;
  border-radius: var(--ui-radius);
  background: linear-gradient(
    150deg,
    rgba(11, 28, 43, 0.68),
    rgba(8, 20, 33, 0.58)
  );
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(116px, 1fr));
  gap: 8px;
  min-height: 0;
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

.ui-icon-picker__item:focus-visible {
  outline: none;
  border-color: rgba(170, 227, 255, 0.75);
  box-shadow: 0 0 0 3px rgba(108, 174, 208, 0.28);
}

.ui-icon-picker__item.active {
  border-color: rgba(108, 239, 207, 0.72);
  background: rgba(27, 72, 78, 0.56);
}

.ui-icon-picker__glyph {
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  font-size: 0.72rem;
  line-height: 1;
  letter-spacing: 0.03em;
  font-weight: 700;
}

.ui-icon-picker__svg {
  width: 100%;
  height: 100%;
  display: block;
  fill: currentColor;
}

.ui-icon-picker__label {
  font-size: 0.72rem;
  line-height: 1.2;
}

.ui-icon-picker__pack,
.ui-icon-picker__source {
  color: rgba(163, 197, 221, 0.76);
  font-size: 0.64rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.ui-icon-picker__empty {
  grid-column: 1 / -1;
  margin: 0;
  color: #9db7ca;
  font-size: 0.78rem;
}

.ui-icon-picker-modal-transition-enter-active,
.ui-icon-picker-modal-transition-leave-active {
  transition: opacity 180ms ease;
}

.ui-icon-picker-modal-transition-enter-from,
.ui-icon-picker-modal-transition-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .ui-icon-picker__modal {
    width: min(1320px, calc(100vw - 20px));
    height: min(860px, calc(100vh - 20px));
    padding: 12px;
  }

  .ui-icon-picker__body {
    grid-template-columns: minmax(0, 1fr);
  }

  .ui-icon-picker__sidebar {
    max-height: 260px;
  }
}
</style>

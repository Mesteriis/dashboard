export interface ShowcaseNodeApi {
  props?: string[];
  slots?: string[];
  signals?: string[];
  model?: string[];
}

export const SHOWCASE_NODE_API: Record<string, ShowcaseNodeApi> = {
  "ui-node-inputgroup": {
    props: ["modelValue", "label", "placeholder", "type", "hint", "error", "prefix", "suffix", "disabled"],
    slots: ["prefix", "suffix"],
    signals: ["update:modelValue", "focus", "blur"],
    model: ["v-model<string>"],
  },
  "ui-node-label": {
    props: ["text", "hint", "required"],
    slots: ["default"],
    signals: [],
    model: [],
  },
  "ui-node-chips": {
    props: ["modelValue", "label", "placeholder"],
    slots: [],
    signals: ["update:modelValue"],
    model: ["v-model<string[]>"],
  },
  "ui-node-select": {
    props: ["modelValue", "label", "options", "placeholder", "search", "multiple", "disabled"],
    slots: ["option", "selected"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-multiselect": {
    props: ["modelValue", "label", "options", "multiple", "search", "disabled"],
    slots: ["option", "selected"],
    signals: ["update:modelValue"],
    model: ["v-model<string[]>"],
  },
  "ui-node-select-search": {
    props: ["modelValue", "options", "search"],
    slots: ["option", "selected"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-select-search-multi": {
    props: ["modelValue", "options", "search", "multiple"],
    slots: ["option", "selected"],
    signals: ["update:modelValue"],
    model: ["v-model<string[]>"],
  },
  "ui-node-checkbox": {
    props: ["modelValue", "label", "disabled"],
    slots: ["default"],
    signals: ["update:modelValue"],
    model: ["v-model<boolean>"],
  },
  "ui-node-radiobutton": {
    props: ["modelValue", "name", "value", "label", "disabled"],
    slots: ["default"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-selectbutton": {
    props: ["modelValue", "options", "disabled"],
    slots: ["item"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-togglebutton": {
    props: ["modelValue", "onLabel", "offLabel", "disabled"],
    slots: ["default"],
    signals: ["update:modelValue"],
    model: ["v-model<boolean>"],
  },
  "ui-node-button": {
    props: ["label", "variant", "size", "type", "disabled", "loading", "block", "iconPosition"],
    slots: ["default", "icon"],
    signals: ["click"],
    model: [],
  },
  "ui-node-icon-picker": {
    props: [
      "modelValue",
      "options",
      "iconSets",
      "downloadedIconSets",
      "excludeSetIds",
      "excludeIconIds",
      "includeDefaultOptions",
      "closeOnSelect",
    ],
    slots: ["selected-icon", "icon", "caret"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-datatable": {
    props: ["rows", "columns", "actions", "showSearch", "showFilters", "showExport", "showPagination"],
    slots: [],
    signals: ["action", "export"],
    model: [],
  },
  "ui-node-pagination": {
    props: ["total", "page", "pageSize", "maxButtons"],
    slots: [],
    signals: ["update:page"],
    model: [":page + @update:page"],
  },
  "ui-node-picklist": {
    props: ["sourceItems", "targetItems"],
    slots: [],
    signals: ["update:sourceItems", "update:targetItems"],
    model: ["v-model:source-items", "v-model:target-items"],
  },
  "ui-node-tree": {
    props: ["nodes", "modelValue", "defaultExpanded"],
    slots: [],
    signals: ["update:modelValue", "toggle"],
    model: ["v-model<string>"],
  },
  "ui-node-toolbar": {
    props: ["title", "subtitle"],
    slots: ["start", "default", "end"],
    signals: [],
    model: [],
  },
  "ui-node-card": {
    props: ["title", "subtitle", "footer"],
    slots: ["default"],
    signals: [],
    model: [],
  },
  "ui-node-divider": {
    props: ["label", "orientation"],
    slots: [],
    signals: [],
    model: [],
  },
  "ui-node-fieldset-static": {
    props: ["legend"],
    slots: ["default"],
    signals: [],
    model: [],
  },
  "ui-node-fieldset-collapsible": {
    props: ["legend", "modelValue", "collapsible"],
    slots: ["default"],
    signals: ["update:modelValue"],
    model: ["v-model<boolean>"],
  },
  "ui-node-accordion-vertical": {
    props: ["items", "orientation"],
    slots: [],
    signals: [],
    model: [],
  },
  "ui-node-accordion-horizontal": {
    props: ["items", "orientation"],
    slots: [],
    signals: [],
    model: [],
  },
  "ui-node-stepper": {
    props: ["steps", "modelValue", "linear"],
    slots: [],
    signals: ["update:modelValue"],
    model: ["v-model<number>"],
  },
  "ui-node-tabs": {
    props: ["tabs", "modelValue"],
    slots: ["default"],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-sidebar-list-item": {
    props: ["modelValue"],
    slots: [],
    signals: ["update:modelValue"],
    model: ["v-model<string>"],
  },
  "ui-node-modal": {
    props: ["open", "title", "closeOnBackdrop"],
    slots: ["default", "footer"],
    signals: ["close"],
    model: [],
  },
  "ui-node-speeddial": {
    props: ["items", "direction", "distance"],
    slots: ["trigger"],
    signals: ["action"],
    model: [],
  },
  "ui-node-dropdown-menu": {
    props: ["label", "items"],
    slots: [],
    signals: ["action"],
    model: [],
  },
  "ui-node-html-tags": {
    props: ["native tags / attrs"],
    slots: [],
    signals: ["browser native events"],
    model: [],
  },
  "ui-node-html-table-lists": {
    props: ["native list/table attrs"],
    slots: [],
    signals: ["browser native events"],
    model: [],
  },
  "ui-node-html-media": {
    props: ["canvas/svg/iframe/progress attrs"],
    slots: [],
    signals: ["load/change (native)"],
    model: [],
  },
  "ui-node-html-form-tags": {
    props: ["input/select/textarea attrs"],
    slots: [],
    signals: ["submit", "reset", "change", "input"],
    model: ["DOM form state"],
  },
};

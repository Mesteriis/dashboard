export interface UiKitPrimitiveNode {
  id: string;
  label: string;
}

export interface UiKitPrimitiveSection {
  id: string;
  label: string;
  items: UiKitPrimitiveNode[];
}

export interface UiKitPrimitiveGroup {
  id: string;
  label: string;
  description: string;
  sections: UiKitPrimitiveSection[];
  items: UiKitPrimitiveNode[];
}

function createGroup(params: {
  id: string;
  label: string;
  description: string;
  sections: UiKitPrimitiveSection[];
}): UiKitPrimitiveGroup {
  const { id, label, description, sections } = params;
  return {
    id,
    label,
    description,
    sections,
    items: sections.flatMap((section) => section.items),
  };
}

export const UI_KIT_SHOWCASE_GROUPS: UiKitPrimitiveGroup[] = [
  createGroup({
    id: "forms",
    label: "Forms",
    description: "Inputs, selectors and action controls.",
    sections: [
      {
        id: "forms-basic-inputs",
        label: "Basic Inputs",
        items: [
          { id: "ui-node-inputgroup", label: "InputGroup" },
          { id: "ui-node-label", label: "Label" },
          { id: "ui-node-chips", label: "Chips" },
        ],
      },
      {
        id: "forms-selects",
        label: "Selects",
        items: [
          { id: "ui-node-select", label: "Select" },
          { id: "ui-node-multiselect", label: "MultiSelect" },
          { id: "ui-node-select-search", label: "Select with search" },
          { id: "ui-node-select-search-multi", label: "Search + Multi" },
        ],
      },
      {
        id: "forms-choice-controls",
        label: "Choice Controls",
        items: [
          { id: "ui-node-checkbox", label: "Checkbox" },
          { id: "ui-node-radiobutton", label: "RadioButton" },
          { id: "ui-node-selectbutton", label: "SelectButton" },
          { id: "ui-node-togglebutton", label: "ToggleButton" },
        ],
      },
      {
        id: "forms-actions",
        label: "Actions",
        items: [{ id: "ui-node-button", label: "Button" }],
      },
      {
        id: "forms-tools",
        label: "Tools",
        items: [{ id: "ui-node-icon-picker", label: "IconPicker" }],
      },
    ],
  }),
  createGroup({
    id: "data",
    label: "Data",
    description: "Collections, pagination and tree structures.",
    sections: [
      {
        id: "data-tables",
        label: "Tables",
        items: [{ id: "ui-node-datatable", label: "DataTable" }],
      },
      {
        id: "data-navigation",
        label: "Navigation",
        items: [{ id: "ui-node-pagination", label: "Pagination" }],
      },
      {
        id: "data-transfer",
        label: "Transfer",
        items: [{ id: "ui-node-picklist", label: "PickList" }],
      },
      {
        id: "data-hierarchy",
        label: "Hierarchy",
        items: [{ id: "ui-node-tree", label: "Tree" }],
      },
    ],
  }),
  createGroup({
    id: "layout",
    label: "Layout",
    description: "Composition blocks and structural patterns.",
    sections: [
      {
        id: "layout-shells",
        label: "Shells & Surfaces",
        items: [
          { id: "ui-node-toolbar", label: "Toolbar" },
          { id: "ui-node-card", label: "Card" },
          { id: "ui-node-divider", label: "Divider" },
        ],
      },
      {
        id: "layout-disclosure",
        label: "Disclosure",
        items: [
          { id: "ui-node-fieldset-static", label: "Fieldset static" },
          { id: "ui-node-fieldset-collapsible", label: "Fieldset collapsible" },
          { id: "ui-node-accordion-vertical", label: "Accordion vertical" },
          { id: "ui-node-accordion-horizontal", label: "Accordion horizontal" },
        ],
      },
      {
        id: "layout-flow",
        label: "Flow & Navigation",
        items: [
          { id: "ui-node-stepper", label: "Stepper" },
          { id: "ui-node-tabs", label: "Tabs" },
          { id: "ui-node-sidebar-list-item", label: "NodeTree" },
        ],
      },
    ],
  }),
  createGroup({
    id: "overlay",
    label: "Overlay",
    description: "Transient layers, menus and floating actions.",
    sections: [
      {
        id: "overlay-dialogs",
        label: "Dialogs",
        items: [{ id: "ui-node-modal", label: "Modal" }],
      },
      {
        id: "overlay-actions",
        label: "Floating Actions",
        items: [{ id: "ui-node-speeddial", label: "SpeedDial" }],
      },
      {
        id: "overlay-menus",
        label: "Menus",
        items: [{ id: "ui-node-dropdown-menu", label: "Dropdown Menu" }],
      },
    ],
  }),
  createGroup({
    id: "html",
    label: "Native HTML",
    description: "Semantic markup and native browser elements.",
    sections: [
      {
        id: "html-semantics",
        label: "Semantics",
        items: [{ id: "ui-node-html-tags", label: "Semantic tags" }],
      },
      {
        id: "html-data",
        label: "Lists & Tables",
        items: [{ id: "ui-node-html-table-lists", label: "Lists & table" }],
      },
      {
        id: "html-media",
        label: "Media & Embed",
        items: [{ id: "ui-node-html-media", label: "Media & embed" }],
      },
      {
        id: "html-forms",
        label: "Form Elements",
        items: [{ id: "ui-node-html-form-tags", label: "Form tags" }],
      },
    ],
  }),
];

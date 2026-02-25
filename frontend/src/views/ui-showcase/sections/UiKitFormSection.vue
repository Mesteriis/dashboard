<template>
  <section class="ui-kit-section">
    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-inputgroup')"
        id="ui-node-inputgroup"
        group-label="Form Controls"
        element-label="UiInputGroup"
        :value="textValue"
        :api="SHOWCASE_NODE_API['ui-node-inputgroup']"
      >
        <UiInputGroup
          v-model="textValue"
          label="Input Group"
          prefix="https://"
          hint="С префиксом и подсказкой"
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-select')"
        id="ui-node-select"
        group-label="Form Controls"
        element-label="UiSelect"
        :value="singleSelect"
        :api="SHOWCASE_NODE_API['ui-node-select']"
      >
        <UiSelect
          v-model="singleSelect"
          label="Select"
          :options="options"
          placeholder="Выберите"
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-multiselect')"
        id="ui-node-multiselect"
        group-label="Form Controls"
        element-label="UiSelect (multiple)"
        :value="multiSelect"
        :api="SHOWCASE_NODE_API['ui-node-multiselect']"
      >
        <UiSelect
          v-model="multiSelect"
          label="MultiSelect"
          :options="options"
          multiple
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-select-search')"
        id="ui-node-select-search"
        group-label="Form Controls"
        element-label="UiSelect (search)"
        :value="searchSelect"
        :api="SHOWCASE_NODE_API['ui-node-select-search']"
      >
        <UiSelect
          v-model="searchSelect"
          label="Select with search"
          :options="options"
          search
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-select-search-multi')"
        id="ui-node-select-search-multi"
        group-label="Form Controls"
        element-label="UiSelect (search + multi)"
        :value="multiSearchSelect"
        :api="SHOWCASE_NODE_API['ui-node-select-search-multi']"
      >
        <UiSelect
          v-model="multiSearchSelect"
          label="Select with search + multi"
          :options="options"
          multiple
          search
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-chips')"
        id="ui-node-chips"
        group-label="Form Controls"
        element-label="UiChipsInput"
        :value="chips"
        :api="SHOWCASE_NODE_API['ui-node-chips']"
      >
        <UiChipsInput
          v-model="chips"
          label="Chips"
          placeholder="Введите и нажмите Enter"
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-label')"
        id="ui-node-label"
        group-label="Form Controls"
        element-label="UiLabel"
        :value="labelMeta"
        :api="SHOWCASE_NODE_API['ui-node-label']"
      >
        <UiLabel text="Checkbox & Radio" hint="Независимые элементы" required />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-checkbox')"
        id="ui-node-checkbox"
        group-label="Form Controls"
        element-label="UiCheckbox"
        :value="isChecked"
        :api="SHOWCASE_NODE_API['ui-node-checkbox']"
      >
        <UiCheckbox v-model="isChecked" label="Согласен с условиями" />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-radiobutton')"
        id="ui-node-radiobutton"
        group-label="Form Controls"
        element-label="UiRadioButton"
        :value="radioValue"
        :api="SHOWCASE_NODE_API['ui-node-radiobutton']"
      >
        <div class="ui-kit-inline">
          <UiRadioButton
            v-model="radioValue"
            name="size"
            value="sm"
            label="Small"
          />
          <UiRadioButton
            v-model="radioValue"
            name="size"
            value="md"
            label="Medium"
          />
          <UiRadioButton
            v-model="radioValue"
            name="size"
            value="lg"
            label="Large"
          />
        </div>
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-selectbutton')"
        id="ui-node-selectbutton"
        group-label="Form Controls"
        element-label="UiSelectButton"
        :value="segmentValue"
        :api="SHOWCASE_NODE_API['ui-node-selectbutton']"
      >
        <UiSelectButton v-model="segmentValue" :options="segmentOptions" />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-togglebutton')"
        id="ui-node-togglebutton"
        group-label="Form Controls"
        element-label="UiToggleButton"
        :value="toggleValue"
        :api="SHOWCASE_NODE_API['ui-node-togglebutton']"
      >
        <UiToggleButton
          v-model="toggleValue"
          on-label="Enabled"
          off-label="Disabled"
        />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-button')"
        id="ui-node-button"
        group-label="Form Controls"
        element-label="UiButton"
        :value="buttonVariants"
        :api="SHOWCASE_NODE_API['ui-node-button']"
      >
        <div class="ui-kit-inline">
          <UiButton label="Primary" />
          <UiButton label="Secondary" variant="secondary" />
          <UiButton label="Ghost" variant="ghost" />
          <UiButton label="Danger" variant="danger" />
        </div>
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-icon-picker')"
        id="ui-node-icon-picker"
        class="ui-kit-stack"
        group-label="Form Controls"
        element-label="UiIconPicker"
        :value="selectedIcon"
        :api="SHOWCASE_NODE_API['ui-node-icon-picker']"
      >
        <UiIconPicker
          v-model="selectedIcon"
          :downloaded-icon-sets="downloadedIconSets"
          :exclude-icon-ids="excludedIconIds"
        />
      </UiShowcaseNode>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiButton from "@/ui/actions/UiButton.vue";
import UiCheckbox from "@/ui/forms/UiCheckbox.vue";
import UiChipsInput from "@/ui/forms/UiChipsInput.vue";
import UiInputGroup from "@/ui/forms/UiInputGroup.vue";
import UiIconPicker from "@/primitives/selection/UiIconPicker.vue";
import type { IconPickerSet } from "@/primitives/selection/UiIconPicker.vue";
import UiLabel from "@/ui/forms/UiLabel.vue";
import UiRadioButton from "@/ui/forms/UiRadioButton.vue";
import UiSelect from "@/ui/forms/UiSelect.vue";
import UiSelectButton from "@/ui/forms/UiSelectButton.vue";
import UiToggleButton from "@/ui/forms/UiToggleButton.vue";
import UiShowcaseNode from "@/views/ui-showcase/components/UiShowcaseNode.vue";
import { SHOWCASE_NODE_API } from "@/views/ui-showcase/showcaseNodeApi";

const props = withDefaults(
  defineProps<{
    activeNodeId?: string;
  }>(),
  {
    activeNodeId: "",
  },
);

function isNodeVisible(nodeId: string): boolean {
  if (!props.activeNodeId) return true;
  return props.activeNodeId === nodeId;
}

const options = [
  { label: "Alpha", value: "alpha" },
  { label: "Beta", value: "beta" },
  { label: "Gamma", value: "gamma" },
  { label: "Delta", value: "delta" },
];

const segmentOptions = [
  { label: "Day", value: "day" },
  { label: "Week", value: "week" },
  { label: "Month", value: "month" },
];

const buttonVariants = ["primary", "secondary", "ghost", "danger"];
const labelMeta = { text: "Checkbox & Radio", required: true };

const textValue = ref("");
const singleSelect = ref("");
const multiSelect = ref<string[]>(["alpha", "gamma"]);
const searchSelect = ref("beta");
const multiSearchSelect = ref<string[]>(["delta"]);
const chips = ref<string[]>(["frontend", "monitoring"]);
const isChecked = ref(true);
const radioValue = ref("md");
const segmentValue = ref("week");
const toggleValue = ref(true);
const selectedIcon = ref("tabler:activity-heartbeat");

const downloadedIconSets: IconPickerSet[] = [
  {
    id: "downloaded:brand-pack",
    label: "Downloaded Brand Pack",
    options: [
      {
        id: "downloaded:prometheus",
        label: "Prometheus",
        pack: "downloaded-brand-pack",
        preview: "PR",
        keywords: ["metrics", "alerts"],
      },
      {
        id: "downloaded:grafana",
        label: "Grafana",
        pack: "downloaded-brand-pack",
        preview: "GF",
        keywords: ["dashboards", "monitoring"],
      },
      {
        id: "downloaded:jaeger",
        label: "Jaeger",
        pack: "downloaded-brand-pack",
        preview: "JG",
        keywords: ["tracing", "observability"],
      },
    ],
  },
];

const excludedIconIds = ["downloaded:jaeger"];
</script>

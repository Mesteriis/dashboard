<template>
  <section class="ui-kit-section">
    <h2>Form Controls</h2>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-inputgroup')"
        id="ui-node-inputgroup"
        class="ui-kit-node"
      >
        <h3>InputGroup</h3>
        <UiInputGroup
          v-model="textValue"
          label="Input Group"
          prefix="https://"
          hint="С префиксом и подсказкой"
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-select')"
        id="ui-node-select"
        class="ui-kit-node"
      >
        <h3>Select</h3>
        <UiSelect
          v-model="singleSelect"
          label="Select"
          :options="options"
          placeholder="Выберите"
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-multiselect')"
        id="ui-node-multiselect"
        class="ui-kit-node"
      >
        <h3>MultiSelect</h3>
        <UiSelect
          v-model="multiSelect"
          label="MultiSelect"
          :options="options"
          multiple
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-select-search')"
        id="ui-node-select-search"
        class="ui-kit-node"
      >
        <h3>Select with search</h3>
        <UiSelect
          v-model="searchSelect"
          label="Select with search"
          :options="options"
          search
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-select-search-multi')"
        id="ui-node-select-search-multi"
        class="ui-kit-node"
      >
        <h3>Select with search + multi</h3>
        <UiSelect
          v-model="multiSearchSelect"
          label="Select with search + multi"
          :options="options"
          multiple
          search
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-chips')"
        id="ui-node-chips"
        class="ui-kit-node"
      >
        <h3>Chips</h3>
        <UiChipsInput
          v-model="chips"
          label="Chips"
          placeholder="Введите и нажмите Enter"
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-label')"
        id="ui-node-label"
        class="ui-kit-node"
      >
        <h3>Label</h3>
        <UiLabel text="Checkbox & Radio" hint="Независимые элементы" required />
      </article>

      <article
        v-show="isNodeVisible('ui-node-checkbox')"
        id="ui-node-checkbox"
        class="ui-kit-node"
      >
        <h3>Checkbox</h3>
        <UiCheckbox v-model="isChecked" label="Согласен с условиями" />
      </article>

      <article
        v-show="isNodeVisible('ui-node-radiobutton')"
        id="ui-node-radiobutton"
        class="ui-kit-node"
      >
        <h3>RadioButton</h3>
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
      </article>

      <article
        v-show="isNodeVisible('ui-node-selectbutton')"
        id="ui-node-selectbutton"
        class="ui-kit-node"
      >
        <h3>SelectButton</h3>
        <UiSelectButton v-model="segmentValue" :options="segmentOptions" />
      </article>

      <article
        v-show="isNodeVisible('ui-node-togglebutton')"
        id="ui-node-togglebutton"
        class="ui-kit-node"
      >
        <h3>ToggleButton</h3>
        <UiToggleButton
          v-model="toggleValue"
          on-label="Enabled"
          off-label="Disabled"
        />
      </article>

      <article
        v-show="isNodeVisible('ui-node-button')"
        id="ui-node-button"
        class="ui-kit-node"
      >
        <h3>Button</h3>
        <div class="ui-kit-inline">
          <UiButton label="Primary" />
          <UiButton label="Secondary" variant="secondary" />
          <UiButton label="Ghost" variant="ghost" />
          <UiButton label="Danger" variant="danger" />
        </div>
      </article>

      <article
        v-show="isNodeVisible('ui-node-icon-picker')"
        id="ui-node-icon-picker"
        class="ui-kit-node ui-kit-stack"
      >
        <h3>IconPicker</h3>
        <UiIconPicker v-model="selectedIcon" />
        <p class="ui-kit-note">
          Selected icon token:
          <code>{{ selectedIcon }}</code>
        </p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiButton from "@/components/ui-kit/primitives/UiButton.vue";
import UiCheckbox from "@/components/ui-kit/primitives/UiCheckbox.vue";
import UiChipsInput from "@/components/ui-kit/primitives/UiChipsInput.vue";
import UiInputGroup from "@/components/ui-kit/primitives/UiInputGroup.vue";
import UiIconPicker from "@/components/ui-kit/primitives/UiIconPicker.vue";
import UiLabel from "@/components/ui-kit/primitives/UiLabel.vue";
import UiRadioButton from "@/components/ui-kit/primitives/UiRadioButton.vue";
import UiSelect from "@/components/ui-kit/primitives/UiSelect.vue";
import UiSelectButton from "@/components/ui-kit/primitives/UiSelectButton.vue";
import UiToggleButton from "@/components/ui-kit/primitives/UiToggleButton.vue";

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
</script>

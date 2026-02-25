<template>
  <UiShowcaseNode
    id="ui-node-html-form-tags"
    class="ui-html-card"
    group-label="Native HTML Catalog"
    element-label="Native Form Elements"
    :value="formState"
    :api="SHOWCASE_NODE_API['ui-node-html-form-tags']"
  >
    <header class="ui-html-card__head">
      <output>{{ submittedMessage }}</output>
    </header>
    <form class="ui-html-form" @submit.prevent="handleSubmit" @reset.prevent="handleReset">
      <fieldset>
        <legend>Form Controls</legend>
        <label>
          Text
          <input v-model="form.text" type="text" placeholder="Type text" />
        </label>
        <label>
          Search
          <input v-model="form.search" type="search" placeholder="Search value" />
        </label>
        <label>
          Email
          <input v-model="form.email" type="email" placeholder="name@domain.com" />
        </label>
        <label>
          Password
          <input v-model="form.password" type="password" />
        </label>
        <label>
          Number
          <input v-model.number="form.number" type="number" min="0" max="100" />
        </label>
        <label>
          URL
          <input v-model="form.url" type="url" placeholder="https://example.com" />
        </label>
        <label>
          Tel
          <input v-model="form.tel" type="tel" placeholder="+1-555-0100" />
        </label>
        <label>
          Date
          <input v-model="form.date" type="date" />
        </label>
        <label>
          Time
          <input v-model="form.time" type="time" />
        </label>
        <label>
          Datetime
          <input v-model="form.datetime" type="datetime-local" />
        </label>
        <label>
          Week
          <input v-model="form.week" type="week" />
        </label>
        <label>
          Month
          <input v-model="form.month" type="month" />
        </label>
        <label>
          Color
          <input v-model="form.color" type="color" />
        </label>
        <label>
          Range
          <input v-model.number="form.range" type="range" min="0" max="100" />
        </label>
        <label>
          File
          <input type="file" @change="handleFileChange" />
        </label>
        <label>
          Textarea
          <textarea v-model="form.message" rows="3"></textarea>
        </label>
        <label>
          Select
          <select v-model="form.select">
            <optgroup label="Core">
              <option value="api">API</option>
              <option value="auth">Auth</option>
            </optgroup>
            <optgroup label="Business">
              <option value="billing">Billing</option>
              <option value="crm">CRM</option>
            </optgroup>
          </select>
        </label>
        <label>
          Datalist
          <input v-model="form.city" list="cities" placeholder="Choose city" />
          <datalist id="cities">
            <option value="San Francisco"></option>
            <option value="New York"></option>
            <option value="Austin"></option>
          </datalist>
        </label>
        <div class="ui-html-form__checks">
          <label><input v-model="form.enabled" type="checkbox" /> Enabled</label>
          <label><input v-model="form.mode" type="radio" value="safe" name="mode" /> Safe</label>
          <label><input v-model="form.mode" type="radio" value="fast" name="mode" /> Fast</label>
        </div>
        <input type="hidden" :value="form.hidden" />
        <div class="ui-html-form__actions">
          <button type="submit">Submit</button>
          <button type="reset">Reset</button>
          <input type="button" value="Native Button" />
        </div>
      </fieldset>
    </form>
    <p class="ui-kit-note">Selected file: {{ form.fileName || "none" }}</p>
  </UiShowcaseNode>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import UiShowcaseNode from "@/views/ui-showcase/components/UiShowcaseNode.vue";
import { SHOWCASE_NODE_API } from "@/views/ui-showcase/showcaseNodeApi";

const submittedAt = ref("");

const form = reactive({
  text: "",
  search: "",
  email: "",
  password: "",
  number: 12,
  url: "",
  tel: "",
  date: "",
  time: "",
  datetime: "",
  week: "",
  month: "",
  color: "#2dd4bf",
  range: 56,
  message: "",
  select: "api",
  city: "",
  enabled: true,
  mode: "safe",
  hidden: "internal-value",
  fileName: "",
});

const submittedMessage = computed(() =>
  submittedAt.value ? `submitted at ${submittedAt.value}` : "not submitted",
);

const formState = computed(() => ({
  text: form.text,
  email: form.email,
  select: form.select,
  enabled: form.enabled,
  mode: form.mode,
  fileName: form.fileName,
}));

function handleSubmit(): void {
  submittedAt.value = new Date().toLocaleTimeString();
}

function handleReset(): void {
  form.text = "";
  form.search = "";
  form.email = "";
  form.password = "";
  form.number = 12;
  form.url = "";
  form.tel = "";
  form.date = "";
  form.time = "";
  form.datetime = "";
  form.week = "";
  form.month = "";
  form.color = "#2dd4bf";
  form.range = 56;
  form.message = "";
  form.select = "api";
  form.city = "";
  form.enabled = true;
  form.mode = "safe";
  form.fileName = "";
  submittedAt.value = "";
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement | null;
  form.fileName = input?.files?.[0]?.name || "";
}
</script>

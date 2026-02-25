<template>
  <section class="editor-section">
    <div class="editor-section-title">
      <span>Iframe-настройки</span>
    </div>

    <div class="editor-grid">
      <section class="editor-field editor-field--wide">
        <span>Sandbox</span>
        <div class="editor-switch-list">
          <BaseSwitch
            :model-value="sandboxUseDefault"
            :disabled="itemEditor.submitting"
            label="Use default sandbox"
            @update:model-value="setSandboxUseDefault"
          />
          <BaseSwitch
            :model-value="sandboxEnabled"
            :disabled="itemEditor.submitting || sandboxUseDefault"
            label="Sandbox enabled"
            @update:model-value="setSandboxEnabled"
          />
          <BaseSwitch
            :model-value="sandboxAllowScripts"
            :disabled="itemEditor.submitting || sandboxUseDefault || !sandboxEnabled"
            label="allow-scripts"
            @update:model-value="setSandboxAllowScripts"
          />
          <BaseSwitch
            :model-value="sandboxAllowSameOrigin"
            :disabled="itemEditor.submitting || sandboxUseDefault || !sandboxEnabled"
            label="allow-same-origin"
            @update:model-value="setSandboxAllowSameOrigin"
          />
          <BaseSwitch
            :model-value="sandboxAllowForms"
            :disabled="itemEditor.submitting || sandboxUseDefault || !sandboxEnabled"
            label="allow-forms"
            @update:model-value="setSandboxAllowForms"
          />
          <BaseSwitch
            :model-value="sandboxAllowPopups"
            :disabled="itemEditor.submitting || sandboxUseDefault || !sandboxEnabled"
            label="allow-popups"
            @update:model-value="setSandboxAllowPopups"
          />
          <BaseSwitch
            :model-value="sandboxAllowModals"
            :disabled="itemEditor.submitting || sandboxUseDefault || !sandboxEnabled"
            label="allow-modals"
            @update:model-value="setSandboxAllowModals"
          />
        </div>
      </section>

      <label class="editor-field">
        <span>Allow</span>
        <HeroMultiSelect
          v-model="itemEditor.form.iframeAllow"
          aria-label="Allow policy"
          placeholder="Выберите разрешения"
          :options="allowOptions"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Referrer policy</span>
        <HeroDropdown
          v-model="itemEditor.form.iframeReferrerPolicy"
          aria-label="Referrer policy"
          :options="referrerPolicyOptions"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Auth profile</span>
        <HeroDropdown
          v-model="itemEditor.form.authProfile"
          aria-label="Auth profile"
          :options="authProfileDropdownOptions"
          :disabled="itemEditor.submitting"
        />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import HeroDropdown from "@/primitives/selection/HeroDropdown.vue";
import HeroMultiSelect from "@/primitives/selection/HeroMultiSelect.vue";
import BaseSwitch from "@/ui/forms/BaseSwitch.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const { itemEditor, authProfileOptions } = dashboard;

type SandboxMode =
  | "default"
  | "enabled"
  | "enabled_same_origin"
  | "enabled_scripts"
  | "enabled_scripts_same_origin"
  | "disabled";

function currentSandboxMode(): SandboxMode {
  const mode = String(itemEditor.form.iframeSandboxMode || "default") as SandboxMode;
  if (
    [
      "default",
      "enabled",
      "enabled_same_origin",
      "enabled_scripts",
      "enabled_scripts_same_origin",
      "disabled",
    ].includes(mode)
  ) {
    return mode;
  }
  return "default";
}

function applySandboxFlags(payload: {
  useDefault: boolean;
  enabled: boolean;
  allowScripts: boolean;
  allowSameOrigin: boolean;
}): void {
  if (payload.useDefault) {
    itemEditor.form.iframeSandboxMode = "default";
    return;
  }

  if (!payload.enabled) {
    itemEditor.form.iframeSandboxMode = "disabled";
    return;
  }

  if (payload.allowScripts && payload.allowSameOrigin) {
    itemEditor.form.iframeSandboxMode = "enabled_scripts_same_origin";
    return;
  }
  if (payload.allowScripts) {
    itemEditor.form.iframeSandboxMode = "enabled_scripts";
    return;
  }
  if (payload.allowSameOrigin) {
    itemEditor.form.iframeSandboxMode = "enabled_same_origin";
    return;
  }
  itemEditor.form.iframeSandboxMode = "enabled";
}

const sandboxUseDefault = computed<boolean>(() => currentSandboxMode() === "default");
const sandboxEnabled = computed<boolean>(() =>
  ["enabled", "enabled_same_origin", "enabled_scripts", "enabled_scripts_same_origin"].includes(
    currentSandboxMode(),
  ),
);
const sandboxAllowScripts = computed<boolean>(() =>
  ["enabled_scripts", "enabled_scripts_same_origin"].includes(currentSandboxMode()),
);
const sandboxAllowSameOrigin = computed<boolean>(() =>
  ["enabled_same_origin", "enabled_scripts_same_origin"].includes(
    currentSandboxMode(),
  ),
);

function setSandboxUseDefault(value: boolean): void {
  applySandboxFlags({
    useDefault: value,
    enabled: value ? false : true,
    allowScripts: sandboxAllowScripts.value,
    allowSameOrigin: sandboxAllowSameOrigin.value,
  });
}

function setSandboxEnabled(value: boolean): void {
  applySandboxFlags({
    useDefault: false,
    enabled: value,
    allowScripts: value ? sandboxAllowScripts.value : false,
    allowSameOrigin: value ? sandboxAllowSameOrigin.value : false,
  });
}

function setSandboxAllowScripts(value: boolean): void {
  applySandboxFlags({
    useDefault: false,
    enabled: true,
    allowScripts: value,
    allowSameOrigin: sandboxAllowSameOrigin.value,
  });
}

function setSandboxAllowSameOrigin(value: boolean): void {
  applySandboxFlags({
    useDefault: false,
    enabled: true,
    allowScripts: sandboxAllowScripts.value,
    allowSameOrigin: value,
  });
}

function hasSandboxExtraToken(token: string): boolean {
  return (itemEditor.form.iframeSandboxExtraTokens || []).includes(token);
}

function setSandboxExtraToken(token: string, value: boolean): void {
  const current = new Set(
    (itemEditor.form.iframeSandboxExtraTokens || [])
      .map((entry: any) => String(entry || "").trim())
      .filter(Boolean),
  );
  if (value) {
    current.add(token);
  } else {
    current.delete(token);
  }
  itemEditor.form.iframeSandboxExtraTokens = Array.from(current);
}

const sandboxAllowForms = computed<boolean>(() =>
  hasSandboxExtraToken("allow-forms"),
);
const sandboxAllowPopups = computed<boolean>(() =>
  hasSandboxExtraToken("allow-popups"),
);
const sandboxAllowModals = computed<boolean>(() =>
  hasSandboxExtraToken("allow-modals"),
);

function setSandboxAllowForms(value: boolean): void {
  setSandboxExtraToken("allow-forms", value);
}

function setSandboxAllowPopups(value: boolean): void {
  setSandboxExtraToken("allow-popups", value);
}

function setSandboxAllowModals(value: boolean): void {
  setSandboxExtraToken("allow-modals", value);
}

const baseAllowOptions = [
  "autoplay",
  "camera",
  "clipboard-read",
  "clipboard-write",
  "display-capture",
  "encrypted-media",
  "fullscreen",
  "geolocation",
  "microphone",
  "payment",
  "picture-in-picture",
  "screen-wake-lock",
  "serial",
  "usb",
  "web-share",
  "xr-spatial-tracking",
];

const allowOptions = computed(() => {
  const values = new Set<string>([
    ...baseAllowOptions,
    ...(itemEditor.form.iframeAllow || []),
  ]);
  return Array.from(values).map((value) => ({ value, label: value }));
});

const baseReferrerPolicyOptions = [
  { value: "", label: "default" },
  { value: "no-referrer", label: "no-referrer" },
  {
    value: "no-referrer-when-downgrade",
    label: "no-referrer-when-downgrade",
  },
  { value: "origin", label: "origin" },
  { value: "origin-when-cross-origin", label: "origin-when-cross-origin" },
  { value: "same-origin", label: "same-origin" },
  { value: "strict-origin", label: "strict-origin" },
  {
    value: "strict-origin-when-cross-origin",
    label: "strict-origin-when-cross-origin",
  },
  { value: "unsafe-url", label: "unsafe-url" },
];

const referrerPolicyOptions = computed(() => {
  const selected = String(itemEditor.form.iframeReferrerPolicy || "").trim();
  if (!selected) return baseReferrerPolicyOptions;
  if (baseReferrerPolicyOptions.some((option) => option.value === selected)) {
    return baseReferrerPolicyOptions;
  }
  return [...baseReferrerPolicyOptions, { value: selected, label: selected }];
});

const authProfileDropdownOptions = computed(() => [
  { value: "", label: "none" },
  ...authProfileOptions.value.map((profile: any) => ({
    value: String(profile.id || ""),
    label: `${String(profile.id || "")} (${String(profile.type || "n/a")})`,
  })),
]);
</script>

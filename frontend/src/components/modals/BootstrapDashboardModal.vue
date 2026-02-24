<template>
  <BaseModal
    :open="open"
    backdrop-class="bootstrap-modal-backdrop"
    modal-class="bootstrap-modal"
  >
    <header class="bootstrap-modal-header">
      <h3>Панель еще не настроена</h3>
      <p>
        Выберите способ старта: создать панель с базовой структурой или
        импортировать готовый <code>dashboard.yaml</code>.
      </p>
    </header>

    <div class="bootstrap-modal-grid">
      <section class="bootstrap-panel bootstrap-panel-create">
        <p class="bootstrap-panel-eyebrow">Новый старт</p>
        <h4>Создать новую панель</h4>
        <p>
          Будет создана стартовая страница с базовой группой сервисов, после
          чего можно сразу редактировать структуру.
        </p>
        <button
          class="bootstrap-modal-primary"
          type="button"
          :disabled="busy"
          @click="$emit('create')"
        >
          {{ creating ? "Создаем панель..." : "Создать панель" }}
        </button>
      </section>

      <section class="bootstrap-panel bootstrap-panel-import">
        <p class="bootstrap-panel-eyebrow">Импорт</p>
        <h4>Импортировать dashboard.yaml</h4>
        <div
          class="bootstrap-dropzone"
          :class="{ 'is-over': dragOver && !busy, disabled: busy }"
          role="button"
          tabindex="0"
          aria-label="Зона загрузки dashboard.yaml"
          @dragenter="handleDragEnter"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
          @click="openFilePicker"
          @keydown.enter.prevent="openFilePicker"
          @keydown.space.prevent="openFilePicker"
        >
          <p class="bootstrap-dropzone-main">
            {{
              importing
                ? "Импортируем файл..."
                : "Перетащите сюда dashboard.yaml"
            }}
          </p>
          <p class="bootstrap-dropzone-sub">или нажмите, чтобы выбрать файл</p>
          <input
            ref="fileInputRef"
            type="file"
            accept=".yaml,.yml,text/yaml"
            :disabled="busy"
            @change="handleImportFile"
          />
        </div>
      </section>
    </div>

    <p class="bootstrap-modal-hint">
      Поддерживаются файлы с расширением <code>.yaml</code> и <code>.yml</code>.
    </p>
    <p v-if="error" class="bootstrap-modal-error">{{ error }}</p>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import BaseModal from "@/components/primitives/BaseModal.vue";

const props = defineProps<{
  open: boolean;
  creating: boolean;
  importing: boolean;
  error: string;
}>();

const emit = defineEmits<{
  create: [];
  importYaml: [{ name: string; yaml: string }];
}>();

const busy = computed(() => props.creating || props.importing);
const dragOver = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

async function handleImportFile(event: Event): Promise<void> {
  if (!(event.target instanceof HTMLInputElement)) return;
  const input = event.target;
  const file = input.files?.[0];
  await importYamlFile(file);
  input.value = "";
}

function isYamlFile(file: File | null | undefined): file is File {
  if (!file) return false;
  const name = String(file.name || "").toLowerCase();
  return name.endsWith(".yaml") || name.endsWith(".yml");
}

async function importYamlFile(file: File | null | undefined): Promise<void> {
  if (!isYamlFile(file) || busy.value) {
    return;
  }
  const yaml = await file.text();
  emit("importYaml", { name: file.name, yaml });
}

function openFilePicker(): void {
  if (busy.value) return;
  fileInputRef.value?.click();
}

function handleDragEnter(event: DragEvent): void {
  if (busy.value) return;
  event.preventDefault();
  dragOver.value = true;
}

function handleDragOver(event: DragEvent): void {
  if (busy.value) return;
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "copy";
  }
  dragOver.value = true;
}

function handleDragLeave(event: DragEvent): void {
  if (busy.value) return;
  event.preventDefault();
  const currentTarget = event.currentTarget;
  const relatedTarget = event.relatedTarget;
  if (
    currentTarget instanceof HTMLElement &&
    relatedTarget instanceof Node &&
    currentTarget.contains(relatedTarget)
  ) {
    return;
  }
  dragOver.value = false;
}

async function handleDrop(event: DragEvent): Promise<void> {
  event.preventDefault();
  dragOver.value = false;
  if (busy.value) return;
  const files = event.dataTransfer?.files;
  const file = files && files.length > 0 ? files[0] : null;
  await importYamlFile(file);
}

watch(
  () => props.open,
  (open) => {
    if (open) return;
    dragOver.value = false;
    if (fileInputRef.value) {
      fileInputRef.value.value = "";
    }
  },
);

watch(
  () => busy.value,
  (isBusy) => {
    if (isBusy) {
      dragOver.value = false;
    }
  },
);
</script>

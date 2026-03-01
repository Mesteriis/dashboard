<template>
  <div ref="rootRef" class="ui-menu" :class="[`align-${align}`, { open }]">
    <button
      class="ui-menu__trigger"
      :class="triggerClass"
      type="button"
      :aria-label="ariaLabel || label"
      aria-haspopup="menu"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <span class="ui-menu__trigger-content">
        <slot name="trigger">{{ label }}</slot>
      </span>
      <span
        v-if="showCaret"
        class="ui-icon ui-menu__caret"
        :class="{ open }"
        aria-hidden="true"
      >
        <slot name="caret" :open="open">▾</slot>
      </span>
    </button>

    <Transition name="ui-menu-transition">
      <ul
        v-if="open"
        class="ui-menu__list"
        role="menu"
        :aria-label="ariaLabel || label"
      >
        <template v-for="item in items" :key="item.id">
          <!-- Divider -->
          <li v-if="item.divider" class="ui-menu__divider" role="separator" />

          <!-- Group with nested items -->
          <li v-else-if="item.children && item.children.length" role="none">
            <button
              class="ui-menu__item ui-menu__item--group"
              :class="itemClass"
              type="button"
              role="menuitem"
              :aria-expanded="isExpanded(item.id)"
              @click="toggleGroup(item.id)"
            >
              <span class="ui-menu__item-content">
                <slot name="item-icon" :item="item">
                  <component
                    :is="item.icon"
                    v-if="isComponentIcon(item.icon)"
                    class="ui-icon ui-menu__item-icon"
                    aria-hidden="true"
                  />
                  <span
                    v-else-if="
                      typeof item.icon === 'string' && item.icon.trim()
                    "
                    class="ui-icon ui-menu__item-icon"
                    aria-hidden="true"
                  >
                    {{ item.icon }}
                  </span>
                </slot>
                <span>{{ item.label }}</span>
              </span>
              <span
                class="ui-menu__group-caret"
                :class="{ 'ui-menu__group-caret--open': isExpanded(item.id) }"
                aria-hidden="true"
                >▸</span
              >
            </button>

            <Transition name="ui-menu-slide">
              <ul
                v-show="isExpanded(item.id)"
                class="ui-menu__nested-list"
                role="menu"
                :aria-label="item.label"
              >
                <template v-for="child in item.children" :key="child.id">
                  <li
                    v-if="child.divider"
                    class="ui-menu__divider ui-menu__divider--nested"
                    role="separator"
                  />
                  <li
                    v-else-if="child.children && child.children.length"
                    role="none"
                  >
                    <button
                      class="ui-menu__item ui-menu__item--nested ui-menu__item--group"
                      :class="itemClass"
                      type="button"
                      role="menuitem"
                      :aria-expanded="isExpanded(child.id)"
                      @click="toggleGroup(child.id)"
                    >
                      <span class="ui-menu__item-content">
                        <slot name="item-icon" :item="child">
                          <component
                            :is="child.icon"
                            v-if="isComponentIcon(child.icon)"
                            class="ui-icon ui-menu__item-icon"
                            aria-hidden="true"
                          />
                          <span
                            v-else-if="
                              typeof child.icon === 'string' &&
                              child.icon.trim()
                            "
                            class="ui-icon ui-menu__item-icon"
                            aria-hidden="true"
                          >
                            {{ child.icon }}
                          </span>
                        </slot>
                        <span>{{ child.label }}</span>
                      </span>
                      <span
                        class="ui-menu__group-caret"
                        :class="{
                          'ui-menu__group-caret--open': isExpanded(child.id),
                        }"
                        aria-hidden="true"
                        >▸</span
                      >
                    </button>

                    <Transition name="ui-menu-slide">
                      <ul
                        v-show="isExpanded(child.id)"
                        class="ui-menu__nested-list ui-menu__nested-list--deep"
                        role="menu"
                        :aria-label="child.label"
                      >
                        <li
                          v-for="grandchild in child.children"
                          :key="grandchild.id"
                          role="none"
                        >
                          <button
                            class="ui-menu__item ui-menu__item--nested ui-menu__item--deep"
                            :class="[itemClass, { 'is-danger': grandchild.danger }]"
                            type="button"
                            role="menuitem"
                            :disabled="Boolean(grandchild.disabled)"
                            @click="selectItem(grandchild)"
                          >
                            <span class="ui-menu__item-content">
                              <slot name="item-icon" :item="grandchild">
                                <component
                                  :is="grandchild.icon"
                                  v-if="isComponentIcon(grandchild.icon)"
                                  class="ui-icon ui-menu__item-icon"
                                  aria-hidden="true"
                                />
                                <span
                                  v-else-if="
                                    typeof grandchild.icon === 'string' &&
                                    grandchild.icon.trim()
                                  "
                                  class="ui-icon ui-menu__item-icon"
                                  aria-hidden="true"
                                >
                                  {{ grandchild.icon }}
                                </span>
                              </slot>
                              <span>{{ grandchild.label }}</span>
                            </span>
                          </button>
                        </li>
                      </ul>
                    </Transition>
                  </li>
                  <li v-else role="none">
                    <button
                      class="ui-menu__item ui-menu__item--nested"
                      :class="[itemClass, { 'is-danger': child.danger }]"
                      type="button"
                      role="menuitem"
                      :disabled="Boolean(child.disabled)"
                      @click="selectItem(child)"
                    >
                      <span class="ui-menu__item-content">
                        <slot name="item-icon" :item="child">
                          <component
                            :is="child.icon"
                            v-if="isComponentIcon(child.icon)"
                            class="ui-icon ui-menu__item-icon"
                            aria-hidden="true"
                          />
                          <span
                            v-else-if="
                              typeof child.icon === 'string' &&
                              child.icon.trim()
                            "
                            class="ui-icon ui-menu__item-icon"
                            aria-hidden="true"
                          >
                            {{ child.icon }}
                          </span>
                        </slot>
                        <span>{{ child.label }}</span>
                      </span>
                    </button>
                  </li>
                </template>
              </ul>
            </Transition>
          </li>

          <!-- Menu Item -->
          <li v-else role="none">
            <button
              class="ui-menu__item"
              :class="[itemClass, { 'is-danger': item.danger }]"
              type="button"
              role="menuitem"
              :disabled="Boolean(item.disabled)"
              @click="selectItem(item)"
            >
              <span class="ui-menu__item-content">
                <slot name="item-icon" :item="item">
                  <component
                    :is="item.icon"
                    v-if="isComponentIcon(item.icon)"
                    class="ui-icon ui-menu__item-icon"
                    aria-hidden="true"
                  />
                  <span
                    v-else-if="
                      typeof item.icon === 'string' && item.icon.trim()
                    "
                    class="ui-icon ui-menu__item-icon"
                    aria-hidden="true"
                  >
                    {{ item.icon }}
                  </span>
                </slot>
                <span>{{ item.label }}</span>
              </span>
            </button>
          </li>
        </template>
      </ul>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, type Component } from "vue";

interface DropdownMenuItem {
  id: string;
  label: string;
  icon?: Component | string;
  danger?: boolean;
  disabled?: boolean;
  divider?: boolean;
  children?: DropdownMenuItem[];
  route?: string;
  action?: () => void | Promise<void>;
}

const props = withDefaults(
  defineProps<{
    items: DropdownMenuItem[];
    label?: string;
    ariaLabel?: string;
    align?: "left" | "right";
    disabled?: boolean;
    closeOnSelect?: boolean;
    showCaret?: boolean;
    triggerClass?: string;
    itemClass?: string;
  }>(),
  {
    label: "Menu",
    ariaLabel: "",
    align: "right",
    disabled: false,
    closeOnSelect: true,
    showCaret: true,
    triggerClass: "",
    itemClass: "",
  },
);

const emit = defineEmits<{
  action: [item: DropdownMenuItem];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);
const expandedGroups = ref<string[]>([]);

function isComponentIcon(icon: DropdownMenuItem["icon"]): icon is Component {
  return typeof icon === "object" || typeof icon === "function";
}

function toggleOpen(): void {
  if (props.disabled) return;
  open.value = !open.value;
}

function closeMenu(): void {
  open.value = false;
  expandedGroups.value = [];
}

function selectItem(item: DropdownMenuItem): void {
  emit("action", item);
  if (props.closeOnSelect) {
    closeMenu();
  }
}

function isExpanded(itemId: string): boolean {
  return expandedGroups.value.includes(itemId);
}

function toggleGroup(itemId: string): void {
  if (isExpanded(itemId)) {
    expandedGroups.value = expandedGroups.value.filter((id) => id !== itemId);
    return;
  }
  expandedGroups.value = [...expandedGroups.value, itemId];
}

function handleOutsidePointer(event: PointerEvent): void {
  if (!open.value) return;
  const targetNode = event.target as Node | null;
  if (rootRef.value && targetNode && !rootRef.value.contains(targetNode)) {
    closeMenu();
  }
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  closeMenu();
}

onMounted(() => {
  if (typeof window === "undefined") return;
  window.addEventListener("pointerdown", handleOutsidePointer);
  window.addEventListener("keydown", handleEscape);
});

onBeforeUnmount(() => {
  if (typeof window === "undefined") return;
  window.removeEventListener("pointerdown", handleOutsidePointer);
  window.removeEventListener("keydown", handleEscape);
});
</script>

<style scoped>
.ui-menu__divider {
  height: 1px;
  margin: 8px 0;
  background-color: rgba(120, 183, 218, 0.2);
}

.ui-menu__item--group {
  justify-content: space-between;
}

.ui-menu__group-caret {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  opacity: 0.65;
  transition: transform 170ms ease;
}

.ui-menu__group-caret--open {
  transform: rotate(90deg);
}

.ui-menu__nested-list {
  list-style: none;
  margin: 2px 0 8px;
  padding: 0;
}

.ui-menu__item--nested {
  padding-left: 22px;
}

.ui-menu__nested-list--deep {
  margin-top: 0;
}

.ui-menu__item--deep {
  padding-left: 34px;
}

.ui-menu__divider--nested {
  margin-left: 18px;
}

.ui-menu-slide-enter-active,
.ui-menu-slide-leave-active {
  transition: all 170ms ease;
}

.ui-menu-slide-enter-from,
.ui-menu-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

# Frontend UI Architecture

## Layers

The `frontend/src` UI is organized as strict layers:

1. `ui/` - low-level UI atoms and base controls (`UiButton`, `UiInputGroup`, `UiIconButton`, `UiSelect`, `UiBaseModal`).
2. `components/` - reusable layout/building blocks without domain logic (`UiBlankLayout`, `UiHeroPanel`, `UiSidebarListItem`).
3. `primitives/` - domain-agnostic interaction patterns (`UiDataTable`, `UiTabs`, `UiModal`, `UiDropdownMenu`, `UiTree`).
4. `views/` - domain/feature views (dashboard, plugins, showcase, overlays) that compose `ui + components + primitives + features`.
5. `pages/` - route-level entry pages only; pages should delegate complex UI to `views/`.

Business/data logic:

- `features/` - stores, composables, service clients, plugin manifest loading.
- `shared/` - constants/contracts/types/utilities with no UI/domain side effects.

## Semantic Groups

`ui/`:

- `ui/actions/` - click actions (`UiButton`, `UiIconButton`).
- `ui/forms/` - field-level controls (`UiSelect`, `UiCheckbox`, `UiInputGroup`, `UiToggleButton`, `UiLabel`).
- `ui/surfaces/` - neutral visual wrappers (`UiCard`, `UiFieldset`, `UiDivider`).
- `ui/overlays/` - low-level modal shells (`BaseModal`, `UiBaseModal`).

`primitives/`:

- `primitives/selection/` - reusable selection patterns (`UiMultiSelect`, `UiSearchSelect`, `UiIconPicker`, `HeroDropdown`).
- `primitives/navigation/` - local navigation patterns (`UiTabs`, `UiAccordion`, `UiStepper`, `UiToolbar`).
- `primitives/data/` - data rendering/interaction (`UiDataTable`, `UiTree`, `UiPickList`, `UiPagination`).
- `primitives/overlays/` - higher-order overlays/actions (`UiModal`, `UiDropdownMenu`, `UiSpeedDial`).

## Dependency Rules

- `ui/**` -> can import only `ui/**` and `shared/**`.
- `components/**` -> can import only `ui/**` and `shared/**`.
- `primitives/**` -> can import only `ui/**` and `shared/**`.
- `views/**` -> can import `ui/**`, `components/**`, `primitives/**`, `features/**`, `shared/**`.
- `pages/**` -> can import `views/**`, `features/**`, `components/**`, `shared/**`.

Additional constraints:

- No network calls/side effects inside `ui/`, `components/`, `primitives/`.
- API/network access belongs to `features/` (or explicit page loaders).
- No parent-relative imports inside `src` (`../`, `../../`): use only `@/...` aliases.
- `ui/components/primitives` are configured by `props + slots + emits`; no direct imports of app stores/router/services.
- Visual markers (caret/check/item icon) in primitives are slot-driven with text fallback, so UI shell is not tied to icon libraries.

## Placement Guide

- New base input/button/icon/modal shell -> `src/ui/`
- New reusable shell/card/frame (no domain state) -> `src/components/`
- New reusable widget pattern (table/tabs/picker/toast) -> `src/primitives/`
- New dashboard/plugin/showcase composition -> `src/views/<domain>/`
- New route screen -> `src/pages/<route>/<Name>Page.vue`
- New API client/composable/store -> `src/features/`
- Pure constants/types/contracts -> `src/shared/`

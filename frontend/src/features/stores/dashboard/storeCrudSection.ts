import { createDashboardCrudDashboard } from "@/features/stores/dashboard/crud/dashboardCrud";
import { createDashboardCrudDragAndDrop } from "@/features/stores/dashboard/crud/dragAndDropCrud";
import { createDashboardCrudEntityManage } from "@/features/stores/dashboard/crud/entityManageCrud";
import { createDashboardCrudGroups } from "@/features/stores/dashboard/crud/groupCrud";
import { createDashboardCrudItemEditor } from "@/features/stores/dashboard/crud/itemEditorCrud";
import { createDashboardCrudItemEditorUtils } from "@/features/stores/dashboard/crud/itemEditorUtils";
import { createDashboardCrudItemSubmit } from "@/features/stores/dashboard/crud/itemSubmitCrud";

export function createDashboardCrudSection(ctx: any) {
  const section = {
    ...createDashboardCrudItemEditorUtils(),
    ...createDashboardCrudDashboard(ctx),
  };

  Object.assign(ctx, section);

  const modules = {
    ...createDashboardCrudGroups(ctx),
    ...createDashboardCrudItemEditor(ctx),
    ...createDashboardCrudItemSubmit(ctx),
    ...createDashboardCrudEntityManage(ctx),
    ...createDashboardCrudDragAndDrop(ctx),
  };

  return {
    ...section,
    ...modules,
  };
}

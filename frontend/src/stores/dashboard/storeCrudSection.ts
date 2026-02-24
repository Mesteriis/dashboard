import { createDashboardCrudDashboard } from "@/stores/dashboard/crud/dashboardCrud";
import { createDashboardCrudDragAndDrop } from "@/stores/dashboard/crud/dragAndDropCrud";
import { createDashboardCrudEntityManage } from "@/stores/dashboard/crud/entityManageCrud";
import { createDashboardCrudGroups } from "@/stores/dashboard/crud/groupCrud";
import { createDashboardCrudItemEditor } from "@/stores/dashboard/crud/itemEditorCrud";
import { createDashboardCrudItemEditorUtils } from "@/stores/dashboard/crud/itemEditorUtils";
import { createDashboardCrudItemSubmit } from "@/stores/dashboard/crud/itemSubmitCrud";

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

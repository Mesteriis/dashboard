import { createDashboardStore } from "@/stores/dashboard/createDashboardStore";

let dashboardStore: ReturnType<typeof createDashboardStore> | null = null;

export function useDashboardStore() {
  if (dashboardStore) {
    return dashboardStore;
  }
  dashboardStore = createDashboardStore({
    onDispose: () => {
      dashboardStore = null;
    },
  });
  return dashboardStore;
}

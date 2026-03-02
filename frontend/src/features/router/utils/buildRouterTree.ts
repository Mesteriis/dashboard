import type { RouteRecordRaw } from "vue-router";

export interface RouterTreeNode {
  name: string;
  label: string;
  path: string;
  icon?: string;
  children?: RouterTreeNode[];
  hidden?: boolean;
  meta?: {
    title?: string;
    icon?: string;
    hidden?: boolean;
  };
}

/**
 * Строит иерархическое дерево роутов из конфигурации Vue Router
 */
export function buildRouterTree(routes: RouteRecordRaw[]): RouterTreeNode[] {
  const result: RouterTreeNode[] = [];

  for (const route of routes) {
    const meta = route.meta as Record<string, unknown> | undefined;
    const title =
      typeof meta?.title === "string" && meta.title.trim()
        ? meta.title
        : undefined;
    const icon =
      typeof meta?.icon === "string" && meta.icon.trim()
        ? meta.icon
        : undefined;
    const hidden = typeof meta?.hidden === "boolean" ? meta.hidden : undefined;

    // Пропускаем скрытые роуты
    if (hidden) continue;

    // Пропускаем роуты без имени (технические роуты)
    if (!route.name) continue;

    const node: RouterTreeNode = {
      name: String(route.name),
      label: title || String(route.name),
      path: route.path,
      icon,
      hidden,
      meta: {
        title,
        icon,
        hidden,
      },
    };

    // Рекурсивно обрабатываем дочерние роуты
    if (route.children && route.children.length > 0) {
      const children = buildRouterTree(route.children);
      if (children.length > 0) {
        node.children = children;
      }
    }

    result.push(node);
  }

  return result;
}

/**
 * Преобразует дерево роутов в формат для dropdown меню
 */
export function routerTreeToMenuItems(
  tree: RouterTreeNode[],
  parentId = "",
): Array<{
  id: string;
  label: string;
  route?: string;
  children?: Array<{ id: string; label: string; route?: string }>;
  divider?: boolean;
}> {
  return tree.map((node) => {
    const id = parentId ? `${parentId}-${node.name}` : node.name;

    if (node.children && node.children.length > 0) {
      return {
        id,
        label: node.label,
        children: routerTreeToMenuItems(node.children, id),
      };
    }

    return {
      id,
      label: node.label,
      route: node.path.startsWith("/") ? node.path : `/${node.path}`,
    };
  });
}

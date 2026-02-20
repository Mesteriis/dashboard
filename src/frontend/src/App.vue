<template>
  <div class="shell">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell" :class="{ 'sidebar-compact': isSidebarIconOnly }">
      <aside class="sidebar" :class="{ compact: isSidebarIconOnly }">
        <div id="sidebar-particles" class="sidebar-particles" aria-hidden="true"></div>
        <div class="sidebar-content" :class="{ compact: isSidebarIconOnly }">
          <div class="brand" :class="{ compact: isSidebarIconOnly }">
            <img :src="EMBLEM_SRC" alt="Oko" />
            <div v-if="!isSidebarIconOnly">
              <p class="brand-title">{{ appTitle }}</p>
              <p class="brand-subtitle">{{ appTagline }}</p>
            </div>
          </div>

          <nav class="tab-list" :class="{ compact: isSidebarIconOnly }" role="tablist" aria-label="Разделы">
            <button
              v-for="page in pages"
              :key="page.id"
              class="tab-btn"
              :class="{ active: activePage?.id === page.id, compact: isSidebarIconOnly }"
              type="button"
              role="tab"
              :title="page.title"
              :aria-label="page.title"
              :aria-selected="activePage?.id === page.id"
              @click="activePageId = page.id"
            >
              <component :is="resolvePageIcon(page)" class="ui-icon tab-tile-icon" />
              <span class="tab-tile-label">{{ page.title }}</span>
            </button>
          </nav>

          <section v-if="treeGroups.length && !isSidebarIconOnly" class="sidebar-tree" aria-label="Дерево сервисов">
            <div class="tree-topline">
              <p class="sidebar-tree-title">Навигация</p>
              <span class="tree-page-chip">{{ activePage?.title }}</span>
            </div>

            <label class="tree-search">
              <input
                v-model="treeFilter"
                type="search"
                placeholder="Поиск сервиса..."
                autocomplete="off"
                spellcheck="false"
              />
            </label>

            <div class="tree-root-page">
              <div class="tree-root-main">
                <component :is="resolvePageIcon(activePage)" class="ui-icon root-icon" />
                <div>
                <p class="tree-root-title">{{ activePage?.title }}</p>
                <p class="tree-root-subtitle">{{ activePage?.id }}</p>
                </div>
              </div>
              <span class="tree-root-meta">{{ pageHealthSummary.online }}/{{ pageHealthSummary.total }}</span>
            </div>

            <ul v-if="filteredTreeGroups.length" class="tree-root">
              <li
                v-for="group in filteredTreeGroups"
                :key="group.key"
                class="tree-group-item"
                :class="{ dragging: dragState.type === 'group' && dragState.groupId === group.id && isDirectGroupNode(group) }"
                :draggable="editMode && isDirectGroupNode(group)"
                @dragstart.stop="onGroupDragStart($event, group)"
                @dragend.stop="clearDragState"
                @dragover.stop="onGroupDragOver($event, group)"
                @drop.stop="onGroupDrop($event, group)"
              >
                <div class="tree-node-row">
                  <button
                    class="tree-node tree-group"
                    :class="{ active: isGroupSelected(group.key) }"
                    type="button"
                    @click="toggleGroupNode(group.key)"
                  >
                    <span class="tree-caret" :class="{ open: isGroupExpanded(group.key) }">▾</span>
                    <component :is="resolveGroupIcon(group)" class="ui-icon tree-icon" />
                    <span class="tree-text">{{ group.title }}</span>
                    <span class="tree-meta">{{ groupOnlineItems(group) }}/{{ groupTotalItems(group) }}</span>
                  </button>
                  <div v-if="editMode && isDirectGroupNode(group)" class="tree-inline-actions">
                    <GripVertical class="ui-icon tree-grip" />
                    <button class="tree-mini-btn" type="button" title="Редактировать группу" @click.stop="editGroup(group.id)">
                      <Pencil class="ui-icon" />
                    </button>
                    <button class="tree-mini-btn" type="button" title="Добавить подгруппу" @click.stop="addSubgroup(group.id)">
                      <Plus class="ui-icon" />
                    </button>
                    <button class="tree-mini-btn danger" type="button" title="Удалить группу" @click.stop="removeGroup(group.id)">
                      <Trash2 class="ui-icon" />
                    </button>
                  </div>
                </div>

                <ul v-show="isGroupExpanded(group.key)" class="tree-subgroups">
                  <li
                    v-for="subgroup in group.subgroups"
                    :key="subgroup.id"
                    class="tree-subgroup-item"
                    :class="{ dragging: dragState.type === 'subgroup' && dragState.subgroupId === subgroup.id }"
                    :draggable="editMode"
                    @dragstart.stop="onSubgroupDragStart($event, group.id, subgroup.id)"
                    @dragend.stop="clearDragState"
                    @dragover.stop="onSubgroupDragOver($event, group.id, subgroup.id)"
                    @drop.stop="onSubgroupDrop($event, group.id, subgroup.id)"
                  >
                    <div class="tree-node-row">
                      <button
                        class="tree-node tree-subgroup"
                        :class="{ active: isSubgroupSelected(group.key, subgroup.id) }"
                        type="button"
                        @click="selectSubgroupNode(group.key, subgroup.id)"
                      >
                        <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon tree-icon tree-sub-icon" />
                        <span class="tree-text">{{ subgroup.title }}</span>
                      </button>
                      <div v-if="editMode" class="tree-inline-actions">
                        <GripVertical class="ui-icon tree-grip" />
                        <button
                          class="tree-mini-btn"
                          type="button"
                          title="Редактировать подгруппу"
                          @click.stop="editSubgroup(group.id, subgroup.id)"
                        >
                          <Pencil class="ui-icon" />
                        </button>
                        <button
                          class="tree-mini-btn"
                          type="button"
                          title="Добавить элемент"
                          @click.stop="addItem(group.id, subgroup.id)"
                        >
                          <Plus class="ui-icon" />
                        </button>
                        <button
                          class="tree-mini-btn danger"
                          type="button"
                          title="Удалить подгруппу"
                          @click.stop="removeSubgroup(group.id, subgroup.id)"
                        >
                          <Trash2 class="ui-icon" />
                        </button>
                      </div>
                    </div>

                    <ul class="tree-items">
                      <li
                        v-for="item in subgroup.items"
                        :key="item.id"
                        class="tree-item-row"
                        :class="{ dragging: dragState.type === 'item' && dragState.itemId === item.id }"
                        :draggable="editMode"
                        @dragstart.stop="onItemDragStart($event, group.id, subgroup.id, item.id)"
                        @dragend.stop="clearDragState"
                        @dragover.stop="onItemDragOver($event, group.id, subgroup.id, item.id)"
                        @drop.stop="onItemDrop($event, group.id, subgroup.id, item.id)"
                      >
                        <div class="tree-node-row">
                          <button
                            class="tree-node tree-item"
                            :class="{ active: isItemSelected(item.id) }"
                            type="button"
                            @click="selectItemNode(group.key, subgroup.id, item.id)"
                          >
                            <span class="health-dot" :class="healthClass(item.id)"></span>
                            <img
                              v-if="itemFaviconSrc(item)"
                              :src="itemFaviconSrc(item)"
                              class="service-favicon tree-item-favicon"
                              alt=""
                              loading="lazy"
                              referrerpolicy="no-referrer"
                              @error="markItemFaviconFailed(item)"
                            />
                            <component v-else :is="resolveItemIcon(item)" class="ui-icon tree-icon tree-item-icon" />
                            <span class="tree-text">{{ item.title }}</span>
                          </button>
                          <div v-if="editMode" class="tree-inline-actions">
                            <GripVertical class="ui-icon tree-grip" />
                            <button
                              class="tree-mini-btn"
                              type="button"
                              title="Редактировать элемент"
                              @click.stop="editItem(group.id, subgroup.id, item.id)"
                            >
                              <Pencil class="ui-icon" />
                            </button>
                            <button
                              class="tree-mini-btn danger"
                              type="button"
                              title="Удалить элемент"
                              @click.stop="removeItem(group.id, subgroup.id, item.id)"
                            >
                              <Trash2 class="ui-icon" />
                            </button>
                          </div>
                        </div>
                      </li>
                    </ul>
                  </li>
                </ul>
              </li>
            </ul>

            <p v-else class="tree-empty">По вашему запросу ничего не найдено.</p>
          </section>

          <section v-else-if="treeGroups.length && isSidebarIconOnly" class="sidebar-icon-rail" aria-label="Иконки навигации">
            <button
              v-for="node in sidebarIconNodes"
              :key="node.key"
              class="sidebar-icon-btn"
              :class="{
                active: isSidebarIconActive(node),
                group: node.type === 'group',
                subgroup: node.type === 'subgroup',
                item: node.type === 'item',
              }"
              type="button"
              :title="sidebarIconNodeTitle(node)"
              :aria-label="sidebarIconNodeTitle(node)"
              @click="selectSidebarIconNode(node)"
            >
              <img
                v-if="node.type === 'item' && itemFaviconSrc(node.item)"
                :src="itemFaviconSrc(node.item)"
                class="service-favicon sidebar-nav-favicon"
                alt=""
                loading="lazy"
                referrerpolicy="no-referrer"
                @error="markItemFaviconFailed(node.item)"
              />
              <component
                v-else
                :is="
                  node.type === 'group'
                    ? resolveGroupIcon(node.group)
                    : node.type === 'subgroup'
                      ? resolveSubgroupIcon(node.subgroup)
                      : resolveItemIcon(node.item)
                "
                class="ui-icon sidebar-nav-icon"
              />
              <span v-if="node.type === 'item'" class="health-dot sidebar-icon-health" :class="healthClass(node.itemId)"></span>
            </button>
          </section>

          <div v-if="!isSidebarIconOnly" class="sidebar-stats-accordion" aria-label="Индикаторы">
            <button
              class="sidebar-stats-toggle"
              type="button"
              aria-controls="sidebar-stats-panel"
              :aria-expanded="statsExpanded"
              @click="statsExpanded = !statsExpanded"
            >
              <span class="sidebar-stats-toggle-text">Индикаторы</span>
              <span class="sidebar-stats-toggle-values">{{ sidebarIndicatorSummary }}</span>
              <span class="sidebar-stats-toggle-caret" :class="{ open: statsExpanded }">▴</span>
            </button>

            <div id="sidebar-stats-panel" class="sidebar-stats-panel" :class="{ open: statsExpanded }">
              <div v-if="sidebarIndicators.length" class="sidebar-indicators">
                <article
                  v-for="widget in sidebarIndicators"
                  :key="widget.id"
                  class="sidebar-indicator"
                  :class="{
                    interactive: isLargeIndicator(widget),
                    active: activeIndicatorWidget?.id === widget.id,
                  }"
                  @click="selectSidebarIndicator(widget)"
                >
                  <header class="widget-head sidebar-indicator-head">
                    <div class="widget-title">
                      <component :is="resolveWidgetIcon(widget)" class="ui-icon widget-icon" />
                      <h3>{{ widget.title }}</h3>
                    </div>
                    <span class="item-type">{{ widget.type }}</span>
                  </header>

                  <p v-if="widgetState(widget.id)?.error" class="widget-error">{{ widgetState(widget.id)?.error }}</p>
                  <p v-else-if="widgetState(widget.id)?.loading" class="widget-loading">Обновление...</p>

                  <template v-else-if="widget.type === 'stat_card'">
                    <p class="widget-value sidebar-indicator-value">{{ statCardValue(widget) }}</p>
                    <p class="widget-subtitle">{{ statCardSubtitle(widget) }}</p>
                    <p v-if="statCardTrend(widget)" class="widget-trend">{{ statCardTrend(widget) }}</p>
                  </template>

                  <template v-else-if="widget.type === 'stat_list'">
                    <ul v-if="indicatorPreviewEntries(widget).length" class="widget-list sidebar-list-preview">
                      <li v-for="entry in indicatorPreviewEntries(widget)" :key="entry.title + entry.value">
                        <span>{{ entry.title }}</span>
                        <strong>{{ entry.value }}</strong>
                      </li>
                    </ul>
                    <p v-else class="widget-empty">Нет данных</p>
                    <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
                  </template>

                  <template v-else-if="widget.type === 'table'">
                    <p class="widget-subtitle">Строк: {{ tableRows(widget).length }}</p>
                    <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
                  </template>

                  <p v-else class="widget-empty">Неподдерживаемый тип виджета</p>

                  <div v-if="widget.data.actions?.length || isLargeIndicator(widget)" class="widget-actions sidebar-indicator-actions">
                    <button
                      v-if="isLargeIndicator(widget)"
                      class="ghost"
                      type="button"
                      @click.stop="openIndicatorView(widget.id)"
                    >
                      Открыть вкладку
                    </button>
                    <button
                      v-for="action in widget.data.actions || []"
                      :key="action.id"
                      class="ghost"
                      type="button"
                      :disabled="isActionBusy(widget.id, action.id)"
                      @click.stop="runWidgetAction(widget.id, action)"
                    >
                      {{ action.title }}
                    </button>
                  </div>
                </article>
              </div>
              <p v-else class="widget-empty">Для выбранной страницы индикаторы не настроены.</p>
            </div>
          </div>
        </div>
      </aside>

      <main :key="activePage?.id || 'empty'" class="page" :class="{ 'indicator-open': Boolean(activeIndicatorWidget) }">
        <section v-if="loadingConfig" class="panel status-panel">
          <h2>Загрузка конфигурации...</h2>
          <p class="subtitle">Получаем dashboard-модель из backend.</p>
        </section>

        <section v-else-if="configError" class="panel status-panel error-state">
          <h2>Ошибка загрузки конфигурации</h2>
          <p class="subtitle">{{ configError }}</p>
          <button class="ghost" type="button" @click="loadConfig">Повторить</button>
        </section>

        <template v-else-if="activePage">
          <section v-if="activeIndicatorWidget" class="panel indicator-tab-panel">
            <header class="indicator-tab-head">
              <div class="indicator-tab-title">
                <component :is="resolveWidgetIcon(activeIndicatorWidget)" class="ui-icon widget-icon" />
                <h2>{{ activeIndicatorWidget.title }}</h2>
              </div>
              <div class="indicator-tab-controls">
                <span class="item-type">{{ activeIndicatorWidget.type }}</span>
                <button class="ghost" type="button" @click="refreshWidget(activeIndicatorWidget.id)">Обновить</button>
                <button class="ghost" type="button" @click="activeIndicatorViewId = ''">Закрыть вкладку</button>
              </div>
            </header>

            <div class="indicator-tab-content">
              <p v-if="widgetState(activeIndicatorWidget.id)?.error" class="widget-error">
                {{ widgetState(activeIndicatorWidget.id)?.error }}
              </p>
              <p v-else-if="widgetState(activeIndicatorWidget.id)?.loading" class="widget-loading">Обновление...</p>

              <template v-else-if="activeIndicatorWidget.type === 'stat_list'">
                <ul v-if="statListEntries(activeIndicatorWidget).length" class="widget-list">
                  <li v-for="entry in statListEntries(activeIndicatorWidget)" :key="entry.title + entry.value">
                    <span>{{ entry.title }}</span>
                    <strong>{{ entry.value }}</strong>
                  </li>
                </ul>
                <p v-else class="widget-empty">Нет данных</p>
              </template>

              <template v-else-if="activeIndicatorWidget.type === 'table'">
                <div v-if="tableRows(activeIndicatorWidget).length" class="widget-table-wrap">
                  <table class="widget-table">
                    <thead>
                      <tr>
                        <th v-for="column in activeIndicatorWidget.data.columns" :key="column.key">{{ column.title }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, rowIndex) in tableRows(activeIndicatorWidget)" :key="rowIndex">
                        <td v-for="column in activeIndicatorWidget.data.columns" :key="column.key">{{ row?.[column.key] ?? '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="widget-empty">Нет данных</p>
              </template>
            </div>

            <div v-if="activeIndicatorWidget.data.actions?.length" class="widget-actions">
              <button
                v-for="action in activeIndicatorWidget.data.actions"
                :key="action.id"
                class="ghost"
                type="button"
                :disabled="isActionBusy(activeIndicatorWidget.id, action.id)"
                @click="runWidgetAction(activeIndicatorWidget.id, action)"
              >
                {{ action.title }}
              </button>
            </div>
          </section>

          <template v-else>
            <template v-if="isLanPage">
              <section class="hero-layout">
                <header class="hero panel hero-title-panel">
                  <div id="hero-title-particles" class="hero-panel-particles" aria-hidden="true"></div>
                  <div class="hero-title-content">
                    <h1>Локальная сеть</h1>
                  </div>
                </header>

                <aside class="panel hero-control-panel">
                  <div id="hero-controls-particles" class="hero-panel-particles" aria-hidden="true"></div>
                  <div class="hero-controls-content">
                    <button
                      class="ghost"
                      type="button"
                      :disabled="lanScanActionBusy || Boolean(lanScanState?.running)"
                      @click="runLanScanNow"
                    >
                      {{
                        lanScanState?.running
                          ? 'Сканирование...'
                          : lanScanActionBusy
                            ? 'Запуск...'
                            : 'Сканировать сейчас'
                      }}
                    </button>
                  </div>
                </aside>
              </section>

              <section class="panel lan-scan-panel">
                <p v-if="lanScanError" class="widget-error">{{ lanScanError }}</p>
                <p v-else-if="lanScanLoading && !lanScanState" class="widget-loading">Загрузка состояния сканера...</p>

                <template v-else>
                  <section class="lan-summary-grid">
                    <article class="lan-summary-card">
                      <p>Статус</p>
                      <strong>{{
                        lanScanState?.running
                          ? 'Сканирование'
                          : lanScanState?.queued
                            ? 'В очереди'
                            : 'Ожидание'
                      }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Хостов найдено</p>
                      <strong>{{ lanHosts.length }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Проверено IP</p>
                      <strong>{{ lanScanState?.result?.scanned_hosts ?? 0 }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Проверено портов</p>
                      <strong>{{ lanScanState?.result?.scanned_ports ?? 0 }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Длительность</p>
                      <strong>{{ formatLanDuration(lanScanState?.result?.duration_ms) }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Последний старт</p>
                      <strong>{{ formatLanMoment(lanScanState?.last_started_at) }}</strong>
                    </article>
                    <article class="lan-summary-card">
                      <p>Следующий запуск</p>
                      <strong>{{ formatLanMoment(lanScanState?.next_run_at) }}</strong>
                    </article>
                  </section>

                  <p class="subtitle lan-meta-line">
                    Подсети: {{ lanCidrsLabel }}
                  </p>
                  <p class="subtitle lan-meta-line">
                    Планировщик: {{ lanScanState?.scheduler || 'asyncio' }} · интервал {{ lanScanState?.interval_sec || 1020 }} сек
                  </p>
                  <p class="subtitle lan-meta-line">
                    Файл результата: {{ lanScanState?.result?.source_file || 'не создан' }}
                  </p>

                  <div class="lan-table-wrap">
                    <table class="lan-table">
                      <thead>
                        <tr>
                          <th>IP</th>
                          <th>Имя</th>
                          <th>MAC</th>
                          <th>Вендор</th>
                          <th>Тип устройства</th>
                          <th>Открытые порты</th>
                          <th>Сервисы dashboard</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="host in lanHosts"
                          :key="host.ip"
                          class="lan-host-row"
                          @click="openLanHostModal(host)"
                        >
                          <td>{{ host.ip }}</td>
                          <td>{{ host.hostname || '—' }}</td>
                          <td>{{ host.mac_address || '—' }}</td>
                          <td>{{ host.mac_vendor || '—' }}</td>
                          <td>{{ host.device_type || '—' }}</td>
                          <td>{{ lanPortsLabel(host) }}</td>
                          <td>
                            <div v-if="host.dashboard_items?.length" class="lan-service-links">
                              <a
                                v-for="service in host.dashboard_items"
                                :key="service.id"
                                class="lan-service-link"
                                :href="service.url"
                                target="_blank"
                                rel="noopener noreferrer"
                                @click.stop
                              >
                                {{ service.title }}
                              </a>
                            </div>
                            <span v-else>—</span>
                          </td>
                        </tr>
                        <tr v-if="!lanHosts.length">
                          <td colspan="7" class="lan-empty">Хосты не обнаружены. Запустите сканирование вручную.</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </template>
              </section>
            </template>

            <template v-else>
              <section class="hero-layout">
                <header class="hero panel hero-title-panel">
                  <div id="hero-title-particles" class="hero-panel-particles" aria-hidden="true"></div>
                  <div class="hero-title-content">
                    <h1>{{ activePage.title }}</h1>
                  </div>
                </header>

                <aside class="panel hero-control-panel" :class="{ active: editMode }">
                  <div id="hero-controls-particles" class="hero-panel-particles" aria-hidden="true"></div>
                  <div class="hero-controls-content">
                    <button
                      class="ghost icon-btn hero-icon-btn editor-toggle"
                      :class="{ active: editMode }"
                      type="button"
                      :title="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
                      :aria-label="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
                      @click="toggleEditMode"
                    >
                      <Pencil class="ui-icon hero-action-icon" />
                    </button>

                    <button
                      v-if="editMode"
                      class="ghost icon-btn hero-icon-btn"
                      type="button"
                      title="Добавить группу"
                      aria-label="Добавить группу"
                      @click="addGroup"
                    >
                      <Plus class="ui-icon hero-action-icon" />
                    </button>

                    <button
                      class="ghost icon-btn hero-icon-btn"
                      :class="{ active: isIconCardView }"
                      type="button"
                      :title="isIconCardView ? 'Переключить на карточки' : 'Переключить на иконки'"
                      :aria-label="isIconCardView ? 'Переключить на карточки' : 'Переключить на иконки'"
                      @click="toggleServiceCardView"
                    >
                      <Layers class="ui-icon hero-action-icon" />
                    </button>

                    <button
                      class="ghost icon-btn hero-icon-btn"
                      :class="{ active: isSidebarIconOnly }"
                      type="button"
                      :title="isSidebarIconOnly ? 'Показать полную боковую панель' : 'Показать только иконки в боковой панели'"
                      :aria-label="isSidebarIconOnly ? 'Показать полную боковую панель' : 'Показать только иконки в боковой панели'"
                      @click="toggleSidebarView"
                    >
                      <FolderTree class="ui-icon hero-action-icon" />
                    </button>

                    <span
                      v-if="editMode"
                      class="hero-save-indicator"
                      :class="saveStatus"
                      role="status"
                      :title="saveStatusLabel"
                      :aria-label="saveStatusLabel"
                    >
                      <Circle class="ui-icon hero-save-icon" />
                    </span>

                    <p v-if="editMode && saveError" class="editor-error hero-editor-error">{{ saveError }}</p>
                  </div>
                </aside>
              </section>

              <section class="page-stack">
              <section
                v-for="(block, index) in activePageGroupBlocks"
                :key="`${activePage.id}:${index}:groups`"
                class="block-wrap"
              >
                <section class="groups-grid">
                  <article
                    v-for="group in filteredBlockGroups(block.group_ids)"
                    :key="group.key"
                    class="panel group-panel"
                    :class="{ 'group-panel-inline': isInlineGroupLayout(group) }"
                  >
                    <header class="group-header">
                      <div class="group-title-row">
                        <component :is="resolveGroupIcon(group)" class="ui-icon group-icon" />
                        <h2>{{ group.title }}</h2>
                      </div>
                      <p v-if="group.description" class="subtitle">{{ group.description }}</p>
                    </header>

                    <section v-for="subgroup in group.subgroups" :key="subgroup.id" class="subgroup">
                      <h3 class="subgroup-title">
                        <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon subgroup-icon" />
                        <span>{{ subgroup.title }}</span>
                      </h3>
                      <div class="item-grid" :class="{ 'icon-card-grid': isIconCardView }">
                        <article
                          v-for="item in subgroup.items"
                          :key="item.id"
                          class="item-card"
                          :class="{
                            selected: !isIconCardView && isItemSelected(item.id),
                            compact: isIconCardView,
                          }"
                          :title="isIconCardView ? item.title : undefined"
                          @click="onItemCardClick(group.key, subgroup.id, item)"
                        >
                          <template v-if="isIconCardView">
                            <div class="item-compact-body">
                              <img
                                v-if="itemFaviconSrc(item)"
                                :src="itemFaviconSrc(item)"
                                class="service-favicon compact-item-favicon"
                                alt=""
                                loading="lazy"
                                referrerpolicy="no-referrer"
                                @error="markItemFaviconFailed(item)"
                              />
                              <component v-else :is="resolveItemIcon(item)" class="ui-icon item-icon compact-item-icon" />
                              <span class="health-dot compact-health-dot" :class="healthClass(item.id)"></span>
                            </div>
                          </template>

                          <template v-else>
                            <div class="item-head">
                              <div class="item-title-row">
                                <img
                                  v-if="itemFaviconSrc(item)"
                                  :src="itemFaviconSrc(item)"
                                  class="service-favicon item-favicon"
                                  alt=""
                                  loading="lazy"
                                  referrerpolicy="no-referrer"
                                  @error="markItemFaviconFailed(item)"
                                />
                                <component v-else :is="resolveItemIcon(item)" class="ui-icon item-icon" />
                                <h4>{{ item.title }}</h4>
                              </div>
                              <span class="item-type">{{ item.type }}</span>
                            </div>

                            <p class="item-url">{{ item.url }}</p>

                            <div class="item-health">
                              <span class="health-dot" :class="healthClass(item.id)"></span>
                              <span class="health-text">{{ healthLabel(item.id) }}</span>
                            </div>

                            <div v-if="item.tags?.length" class="item-tags">
                              <span v-for="tag in item.tags" :key="tag" class="tag-pill">{{ tag }}</span>
                            </div>

                            <div class="item-actions">
                              <button
                                class="ghost icon-btn"
                                type="button"
                                :title="item.type === 'iframe' ? 'Открыть iframe' : 'Открыть'"
                                :aria-label="item.type === 'iframe' ? 'Открыть iframe' : 'Открыть'"
                                @click.stop="openItem(item)"
                              >
                                <component :is="item.type === 'iframe' ? Globe : Link2" class="ui-icon item-action-icon" />
                              </button>
                              <button
                                class="ghost icon-btn"
                                type="button"
                                title="Копировать URL"
                                aria-label="Копировать URL"
                                @click.stop="copyUrl(item.url)"
                              >
                                <Copy class="ui-icon item-action-icon" />
                              </button>
                            </div>
                          </template>
                        </article>
                      </div>
                    </section>
                  </article>

                  <article
                    v-if="!filteredBlockGroups(block.group_ids).length"
                    class="panel group-panel group-empty"
                  >
                    <h2>Нет данных для выбранного узла</h2>
                    <p class="subtitle">Выберите другую ветку в боковом дереве.</p>
                  </article>
                </section>
              </section>

              <article
                v-if="!activePageGroupBlocks.length"
                class="panel group-panel group-empty"
              >
                <h2>Для этой страницы нет групп</h2>
                <p class="subtitle">Откройте нужный индикатор в аккордеоне слева.</p>
              </article>
              </section>
            </template>
          </template>
        </template>

        <section v-else class="panel status-panel">
          <h2>Нет доступных страниц</h2>
          <p class="subtitle">Проверьте `layout.pages` в `dashboard.yaml`.</p>
        </section>
      </main>
    </div>

    <div v-if="lanHostModal.open" class="lan-host-modal-backdrop" @click.self="closeLanHostModal">
      <div class="lan-host-modal">
        <header class="lan-host-modal-header">
          <h3>{{ lanHostModal.host?.hostname || lanHostModal.host?.ip || 'Устройство LAN' }}</h3>
          <button class="ghost" type="button" @click="closeLanHostModal">Закрыть</button>
        </header>

        <div v-if="lanHostModal.host" class="lan-host-modal-body">
          <section class="lan-host-overview">
            <article class="lan-host-meta-card">
              <p>IP</p>
              <strong>{{ lanHostModal.host.ip }}</strong>
            </article>
            <article class="lan-host-meta-card">
              <p>Hostname</p>
              <strong>{{ lanHostModal.host.hostname || '—' }}</strong>
            </article>
            <article class="lan-host-meta-card">
              <p>MAC</p>
              <strong>{{ lanHostModal.host.mac_address || '—' }}</strong>
            </article>
            <article class="lan-host-meta-card">
              <p>Вендор</p>
              <strong>{{ lanHostModal.host.mac_vendor || '—' }}</strong>
            </article>
            <article class="lan-host-meta-card">
              <p>Тип устройства</p>
              <strong>{{ lanHostModal.host.device_type || '—' }}</strong>
            </article>
          </section>

          <section class="lan-host-section">
            <h4>Открытые порты</h4>
            <div v-if="lanHostModal.host.open_ports?.length" class="lan-port-chips">
              <span v-for="port in lanHostModal.host.open_ports" :key="port.port" class="lan-port-chip">
                {{ port.port }}
                <small v-if="port.service">{{ port.service }}</small>
              </span>
            </div>
            <p v-else class="widget-empty">Открытые порты не обнаружены.</p>
          </section>

          <section class="lan-host-section">
            <h4>HTTP/HTTPS профили</h4>
            <div v-if="lanHostModal.host.http_services?.length" class="lan-http-grid">
              <article
                v-for="endpoint in lanHostModal.host.http_services"
                :key="`${endpoint.scheme}:${endpoint.port}:${endpoint.url}`"
                class="lan-http-card"
                :class="{ error: Boolean(endpoint.error) }"
              >
                <header class="lan-http-head">
                  <strong>{{ endpoint.scheme.toUpperCase() }}:{{ endpoint.port }}</strong>
                  <span>{{ formatLanHttpStatus(endpoint) }}</span>
                </header>
                <a
                  class="lan-http-url"
                  :href="endpoint.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  @click.stop
                >
                  {{ endpoint.url }}
                </a>
                <p class="lan-http-title">{{ endpoint.title || 'Title не найден' }}</p>
                <p class="lan-http-description">{{ endpoint.description || 'Описание не найдено' }}</p>
                <p v-if="endpoint.server" class="lan-http-server">Server: {{ endpoint.server }}</p>
                <p v-if="endpoint.error" class="widget-error">{{ endpoint.error }}</p>
              </article>
            </div>
            <p v-else class="widget-empty">HTTP/HTTPS endpoint не обнаружен.</p>
          </section>

          <section class="lan-host-section">
            <h4>Сервисы из dashboard</h4>
            <div v-if="lanHostModal.host.dashboard_items?.length" class="lan-service-links">
              <a
                v-for="service in lanHostModal.host.dashboard_items"
                :key="service.id"
                class="lan-service-link"
                :href="service.url"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >
                {{ service.title }}
              </a>
            </div>
            <p v-else class="widget-empty">Связанные сервисы не найдены.</p>
          </section>
        </div>
      </div>
    </div>

    <div v-if="iframeModal.open" class="iframe-modal-backdrop" @click.self="closeIframeModal">
      <div class="iframe-modal">
        <header class="iframe-modal-header">
          <h3>{{ iframeModal.title }}</h3>
          <button class="ghost" type="button" @click="closeIframeModal">Закрыть</button>
        </header>

        <p v-if="iframeModal.loading" class="subtitle iframe-modal-status">Подготовка iframe...</p>
        <p v-else-if="iframeModal.error" class="widget-error iframe-modal-status">{{ iframeModal.error }}</p>
        <iframe
          v-else
          class="iframe-view"
          :src="iframeModal.src"
          :allow="iframeModal.allow || undefined"
          :sandbox="iframeModal.sandbox ? '' : undefined"
          :referrerpolicy="iframeModal.referrerPolicy || undefined"
        ></iframe>
      </div>
    </div>

    <div v-if="itemEditor.open" class="editor-modal-backdrop" @click.self="closeItemEditor">
      <div class="editor-modal">
        <header class="editor-modal-header">
          <h3>{{ itemEditor.mode === 'create' ? 'Новый сервис' : 'Редактирование сервиса' }}</h3>
          <button class="ghost" type="button" :disabled="itemEditor.submitting" @click="closeItemEditor">Закрыть</button>
        </header>

        <form class="editor-modal-form" @submit.prevent="submitItemEditor">
          <p v-if="itemEditor.error" class="widget-error">{{ itemEditor.error }}</p>

          <div class="editor-grid">
            <label class="editor-field">
              <span>ID</span>
              <input
                v-model.trim="itemEditor.form.id"
                type="text"
                placeholder="auto (из названия)"
                autocomplete="off"
                :disabled="itemEditor.submitting"
              />
            </label>

            <label class="editor-field">
              <span>Название</span>
              <input
                v-model.trim="itemEditor.form.title"
                type="text"
                placeholder="Например: Grafana"
                autocomplete="off"
                :disabled="itemEditor.submitting"
                required
              />
            </label>

            <label class="editor-field">
              <span>Тип</span>
              <select v-model="itemEditor.form.type" :disabled="itemEditor.submitting">
                <option value="link">link</option>
                <option value="iframe">iframe</option>
              </select>
            </label>

            <label class="editor-field">
              <span>URL</span>
              <input
                v-model.trim="itemEditor.form.url"
                type="url"
                placeholder="https://service.example.com"
                autocomplete="off"
                :disabled="itemEditor.submitting"
                required
              />
            </label>

            <label class="editor-field">
              <span>Иконка</span>
              <input
                v-model.trim="itemEditor.form.icon"
                type="text"
                placeholder="proxmox, grafana..."
                autocomplete="off"
                :disabled="itemEditor.submitting"
              />
            </label>

            <label class="editor-field">
              <span>Открытие</span>
              <select v-model="itemEditor.form.open" :disabled="itemEditor.submitting">
                <option value="new_tab">new_tab</option>
                <option value="same_tab">same_tab</option>
              </select>
            </label>
          </div>

          <label class="editor-field">
            <span>Теги (через запятую)</span>
            <input
              v-model.trim="itemEditor.form.tagsInput"
              type="text"
              placeholder="infra, monitoring"
              autocomplete="off"
              :disabled="itemEditor.submitting"
            />
          </label>

          <section v-if="itemEditor.form.type === 'link'" class="editor-section">
            <div class="editor-section-title">
              <label class="editor-check">
                <input v-model="itemEditor.form.healthcheckEnabled" type="checkbox" :disabled="itemEditor.submitting" />
                <span>Healthcheck</span>
              </label>
            </div>

            <div v-if="itemEditor.form.healthcheckEnabled" class="editor-grid">
              <label class="editor-field">
                <span>Healthcheck URL</span>
                <input
                  v-model.trim="itemEditor.form.healthcheckUrl"
                  type="url"
                  placeholder="https://service.example.com/health"
                  autocomplete="off"
                  :disabled="itemEditor.submitting"
                />
              </label>
              <label class="editor-field">
                <span>Интервал (sec)</span>
                <input v-model.number="itemEditor.form.healthcheckIntervalSec" type="number" min="1" max="3600" :disabled="itemEditor.submitting" />
              </label>
              <label class="editor-field">
                <span>Timeout (ms)</span>
                <input v-model.number="itemEditor.form.healthcheckTimeoutMs" type="number" min="100" max="120000" :disabled="itemEditor.submitting" />
              </label>
            </div>
          </section>

          <section v-else class="editor-section">
            <div class="editor-section-title">
              <span>Iframe-настройки</span>
            </div>
            <div class="editor-grid">
              <label class="editor-field">
                <span>Sandbox</span>
                <select v-model="itemEditor.form.iframeSandboxMode" :disabled="itemEditor.submitting">
                  <option value="default">default</option>
                  <option value="enabled">enabled</option>
                  <option value="disabled">disabled</option>
                </select>
              </label>
              <label class="editor-field">
                <span>Allow (через запятую)</span>
                <input
                  v-model.trim="itemEditor.form.iframeAllowInput"
                  type="text"
                  placeholder="fullscreen, clipboard-read"
                  autocomplete="off"
                  :disabled="itemEditor.submitting"
                />
              </label>
              <label class="editor-field">
                <span>Referrer policy</span>
                <input
                  v-model.trim="itemEditor.form.iframeReferrerPolicy"
                  type="text"
                  placeholder="no-referrer"
                  autocomplete="off"
                  :disabled="itemEditor.submitting"
                />
              </label>
              <label class="editor-field">
                <span>Auth profile</span>
                <select v-model="itemEditor.form.authProfile" :disabled="itemEditor.submitting">
                  <option value="">none</option>
                  <option v-for="profile in authProfileOptions" :key="profile.id" :value="profile.id">
                    {{ profile.id }} ({{ profile.type }})
                  </option>
                </select>
              </label>
            </div>
          </section>

          <div class="editor-actions">
            <button class="ghost" type="button" :disabled="itemEditor.submitting" @click="closeItemEditor">Отмена</button>
            <button class="ghost" type="submit" :disabled="itemEditor.submitting">
              {{ itemEditor.submitting ? 'Сохранение...' : itemEditor.mode === 'create' ? 'Создать' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  Activity,
  Camera,
  ChartColumn,
  Circle,
  Cloud,
  Copy,
  Cpu,
  Database,
  Eye,
  Film,
  Folder,
  FolderTree,
  Gauge,
  GitBranch,
  Globe,
  GripVertical,
  HardDrive,
  HeartPulse,
  House,
  KeyRound,
  Layers,
  LayoutDashboard,
  Link2,
  Lock,
  Monitor,
  MonitorSmartphone,
  Music,
  Network,
  Pencil,
  Package,
  Plus,
  Radar,
  Route,
  Server,
  Settings,
  Shield,
  Sparkles,
  Terminal,
  TriangleAlert,
  Trash2,
  Tv,
  Wifi,
  Workflow,
  Wrench,
  Boxes,
} from 'lucide-vue-next'
import {
  siAdguard,
  siCockpit,
  siDocker,
  siGitea,
  siGrafana,
  siHomeassistant,
  siJellyfin,
  siNginx,
  siNginxproxymanager,
  siNpm,
  siOpenaigym,
  siOpenwrt,
  siPostgresql,
  siPortainer,
  siProxmox,
  siQbittorrent,
  siRadarr,
  siSonarr,
  siTermius,
  siYoutube,
  siYoutubeshorts,
} from 'simple-icons'
import {
  fetchDashboardConfig,
  fetchDashboardHealth,
  fetchIframeSource,
  fetchLanScanState,
  requestJson,
  triggerLanScan,
  updateDashboardConfig,
} from './services/dashboardApi.js'

const EMBLEM_SRC = '/static/img/emblem-mark.png'
const HEALTH_REFRESH_MS = 30000
const LAN_SCAN_POLL_MS = 10000
const LAN_PAGE_ID = 'lan'
const LARGE_INDICATOR_TYPES = new Set(['stat_list', 'table'])
const DEFAULT_ITEM_URL = 'https://example.com'
const SIDEBAR_PARTICLES_ID = 'sidebar-particles'
const HERO_TITLE_PARTICLES_ID = 'hero-title-particles'
const HERO_CONTROLS_PARTICLES_ID = 'hero-controls-particles'
const SIDEBAR_PARTICLES_CONFIG = {
  particles: {
    number: { value: 88, density: { enable: true, value_area: 700 } },
    color: { value: '#6df6e2' },
    shape: { type: 'circle' },
    opacity: { value: 0.36, random: true },
    size: { value: 2.4, random: true },
    line_linked: {
      enable: true,
      distance: 120,
      color: '#2dd4bf',
      opacity: 0.24,
      width: 1.2,
    },
    move: { enable: true, speed: 1.2 },
  },
  interactivity: {
    events: { onhover: { enable: false }, onclick: { enable: false }, resize: true },
  },
  retina_detect: true,
}
const HERO_PARTICLES_CONFIG = {
  particles: {
    number: { value: 92, density: { enable: true, value_area: 720 } },
    color: { value: '#6df6e2' },
    shape: { type: 'circle' },
    opacity: { value: 0.4, random: true },
    size: { value: 2.4, random: true },
    line_linked: {
      enable: true,
      distance: 132,
      color: '#2dd4bf',
      opacity: 0.26,
      width: 1.2,
    },
    move: { enable: true, speed: 1.2 },
  },
  interactivity: {
    events: { onhover: { enable: false }, onclick: { enable: false }, resize: true },
  },
  retina_detect: true,
}

function defaultItemEditorForm() {
  return {
    id: '',
    title: '',
    type: 'link',
    url: DEFAULT_ITEM_URL,
    icon: '',
    tagsInput: '',
    open: 'new_tab',
    healthcheckEnabled: false,
    healthcheckUrl: '',
    healthcheckIntervalSec: 30,
    healthcheckTimeoutMs: 1500,
    iframeSandboxMode: 'default',
    iframeAllowInput: '',
    iframeReferrerPolicy: '',
    authProfile: '',
  }
}

function createBrandIcon(icon) {
  const brandColor = `#${icon.hex}`
  return (_props, { attrs }) =>
    h(
      'svg',
      {
        ...attrs,
        xmlns: 'http://www.w3.org/2000/svg',
        viewBox: '0 0 24 24',
        fill: 'currentColor',
        role: 'img',
        'aria-hidden': 'true',
        style: attrs.style ? [attrs.style, { color: brandColor }] : { color: brandColor },
      },
      [h('path', { d: icon.path })]
    )
}

const BRAND_ICON_BY_KEY = {
  homeassistant: createBrandIcon(siHomeassistant),
  'home-assistant': createBrandIcon(siHomeassistant),
  ha: createBrandIcon(siHomeassistant),
  openwrt: createBrandIcon(siOpenwrt),
  adguard: createBrandIcon(siAdguard),
  proxmox: createBrandIcon(siProxmox),
  pve: createBrandIcon(siProxmox),
  grafana: createBrandIcon(siGrafana),
  gitea: createBrandIcon(siGitea),
  jellyfin: createBrandIcon(siJellyfin),
  jellyseerr: createBrandIcon(siJellyfin),
  sonarr: createBrandIcon(siSonarr),
  radarr: createBrandIcon(siRadarr),
  lidarr: createBrandIcon(siSonarr),
  readarr: createBrandIcon(siSonarr),
  bazarr: createBrandIcon(siSonarr),
  prowlarr: createBrandIcon(siSonarr),
  qbittorrent: createBrandIcon(siQbittorrent),
  qb: createBrandIcon(siQbittorrent),
  postgres: createBrandIcon(siPostgresql),
  postgresql: createBrandIcon(siPostgresql),
  docker: createBrandIcon(siDocker),
  dockge: createBrandIcon(siDocker),
  cockpit: createBrandIcon(siCockpit),
  npm: createBrandIcon(siNginxproxymanager),
  nginxproxymanager: createBrandIcon(siNginxproxymanager),
  'nginx-proxy-manager': createBrandIcon(siNginxproxymanager),
  nginx: createBrandIcon(siNginx),
  openai: createBrandIcon(siOpenaigym),
  ai: createBrandIcon(siOpenaigym),
  portainer: createBrandIcon(siPortainer),
  ytsync: createBrandIcon(siYoutubeshorts),
  youtube: createBrandIcon(siYoutube),
  youtubeshorts: createBrandIcon(siYoutubeshorts),
  termius: createBrandIcon(siTermius),
  termix: createBrandIcon(siTermius),
}

const ICON_BY_KEY = {
  home: House,
  house: House,
  дом: House,
  dom: House,
  route: Route,
  net: Network,
  network: Network,
  сеть: Network,
  dashboard: LayoutDashboard,
  infra: Server,
  infrastructure: Server,
  инфраструктура: Server,
  server: Server,
  core: Boxes,
  ops: Wrench,
  media: Tv,
  медиа: Tv,
  tv: Tv,
  iot: Cpu,
  cloud: Cloud,
  wifi: Wifi,
  monitor: Monitor,
  cockpit: MonitorSmartphone,
  proxmox: Server,
  grafana: ChartColumn,
  gitea: GitBranch,
  git: GitBranch,
  jellyfin: Film,
  navidrome: Music,
  tunnel: Radar,
  tunnels: Radar,
  stats: Gauge,
  services: Layers,
  service: Layers,
  health: HeartPulse,
  alerts: TriangleAlert,
  alert: TriangleAlert,
  security: Shield,
  auth: Lock,
  key: KeyRound,
  db: Database,
  database: Database,
  storage: HardDrive,
  link: Link2,
  iframe: Globe,
  terminal: Terminal,
  package: Package,
  music: Music,
  camera: Camera,
  eye: Eye,
  observability: Activity,
  workflow: Workflow,
  settings: Settings,
  spark: Sparkles,
}

const ICON_RULES = [
  { re: /\b(home|house|dom|дом)\b/, icon: House },
  { re: /\b(net|network|route|vpn|edge|сеть|маршрут|туннел)\b/, icon: Network },
  { re: /\b(infra|server|cluster|pve|проксмокс|инфраструктур)\b/, icon: Server },
  { re: /\b(media|tv|video|stream|jellyfin|медиа)\b/, icon: Film },
  { re: /\b(iot|sensor|home-assistant|умн|дом)\b/, icon: Cpu },
  { re: /\b(stat|metric|chart|grafana|аналит|monitor)\b/, icon: ChartColumn },
  { re: /\b(alert|error|warn|critical|ошиб|авар)\b/, icon: TriangleAlert },
  { re: /\b(health|status|pulse|heart|состояни)\b/, icon: HeartPulse },
  { re: /\b(auth|token|secret|lock|ключ|безопас)\b/, icon: Shield },
  { re: /\b(db|database|postgres|mysql|redis)\b/, icon: Database },
]

function normalizeIconToken(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9а-яё._-]+/gi, ' ')
    .split(/[\\s._-]+/)
    .filter(Boolean)
}

function fromToken(token) {
  if (BRAND_ICON_BY_KEY[token]) return BRAND_ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(BRAND_ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }

  if (ICON_BY_KEY[token]) return ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }
  return null
}

function pickSemanticIcon(sources, fallback) {
  for (const source of sources) {
    for (const token of normalizeIconToken(source)) {
      const icon = fromToken(token)
      if (icon) return icon
    }
  }

  const fullText = sources
    .map((source) => String(source || '').toLowerCase())
    .filter(Boolean)
    .join(' ')

  for (const rule of ICON_RULES) {
    if (rule.re.test(fullText)) return rule.icon
  }

  return fallback
}

const config = ref(null)
const loadingConfig = ref(true)
const configError = ref('')
const activePageId = ref('')
const treeFilter = ref('')
const statsExpanded = ref(false)
const activeIndicatorViewId = ref('')
const editMode = ref(false)
const serviceCardView = ref('detailed')
const sidebarView = ref('detailed')
const saveStatus = ref('idle')
const saveError = ref('')
const lanScanState = ref(null)
const lanScanLoading = ref(false)
const lanScanActionBusy = ref(false)
const lanScanError = ref('')
const lanHostModal = reactive({
  open: false,
  host: null,
})

const widgetStates = reactive({})
const actionBusy = reactive({})
const widgetIntervals = new Map()
let healthPollTimer = 0
let saveStatusTimer = 0
let lanScanPollTimer = 0
let lanScanRefreshInFlight = false

const selectedNode = reactive({
  groupKey: '',
  subgroupId: '',
  itemId: '',
})

const expandedGroups = reactive({})
const healthStates = reactive({})
const dragState = reactive({
  type: '',
  groupId: '',
  subgroupId: '',
  itemId: '',
})
const itemFaviconFailures = reactive({})

const iframeModal = reactive({
  open: false,
  title: '',
  src: '',
  allow: '',
  sandbox: false,
  referrerPolicy: '',
  loading: false,
  error: '',
})

const itemEditor = reactive({
  open: false,
  mode: 'create',
  groupId: '',
  subgroupId: '',
  originalItemId: '',
  submitting: false,
  error: '',
  form: defaultItemEditorForm(),
})

const pages = computed(() => {
  if (!config.value) return []
  const configured = config.value?.layout?.pages || []
  if (configured.some((page) => page.id === LAN_PAGE_ID)) {
    return configured
  }

  return [
    ...configured,
    {
      id: LAN_PAGE_ID,
      title: 'LAN',
      icon: 'network',
      blocks: [],
    },
  ]
})
const widgets = computed(() => config.value?.widgets || [])
const authProfileOptions = computed(() => config.value?.security?.auth_profiles || [])

const appTitle = computed(() => config.value?.app?.title || 'Oko')
const appTagline = computed(() => config.value?.app?.tagline || 'Your Infrastructure in Sight')
const isIconCardView = computed(() => serviceCardView.value === 'icon')
const isSidebarIconOnly = computed(() => sidebarView.value === 'icons')
const lanHosts = computed(() => lanScanState.value?.result?.hosts || [])
const lanCidrsLabel = computed(() => {
  const cidrs = lanScanState.value?.result?.scanned_cidrs || []
  return cidrs.length ? cidrs.join(', ') : 'нет данных'
})
const saveStatusLabel = computed(() => {
  if (saveStatus.value === 'saving') return 'Сохранение...'
  if (saveStatus.value === 'saved') return 'Сохранено'
  if (saveStatus.value === 'error') return 'Ошибка сохранения'
  return editMode.value ? 'Готово' : 'Сохранение выключено'
})

const widgetById = computed(() => {
  const map = new Map()
  for (const widget of widgets.value) {
    map.set(widget.id, widget)
  }
  return map
})

const groupById = computed(() => {
  const map = new Map()
  for (const group of config.value?.groups || []) {
    map.set(group.id, group)
  }
  return map
})

const subgroupById = computed(() => {
  const map = new Map()
  for (const group of config.value?.groups || []) {
    for (const subgroup of group.subgroups || []) {
      map.set(subgroup.id, { group, subgroup })
    }
  }
  return map
})

const activePage = computed(() => pages.value.find((page) => page.id === activePageId.value) || pages.value[0] || null)
const isLanPage = computed(() => activePage.value?.id === LAN_PAGE_ID)

const treeGroups = computed(() => {
  if (!activePage.value) return []

  const groupIds = []
  for (const block of activePage.value.blocks || []) {
    if (block?.type === 'groups') {
      groupIds.push(...(block.group_ids || []))
    }
  }

  return resolveBlockGroups(groupIds)
})

const filteredTreeGroups = computed(() => {
  const query = treeFilter.value.trim().toLowerCase()
  if (!query) return treeGroups.value

  return treeGroups.value
    .map((group) => {
      const groupMatches =
        String(group.title || '').toLowerCase().includes(query) ||
        String(group.description || '').toLowerCase().includes(query)

      if (groupMatches) {
        return {
          ...group,
          subgroups: group.subgroups || [],
        }
      }

      const matchedSubgroups = (group.subgroups || [])
        .map((subgroup) => {
          const subgroupMatches = String(subgroup.title || '').toLowerCase().includes(query)
          if (subgroupMatches) {
            return {
              ...subgroup,
              items: subgroup.items || [],
            }
          }

          const matchedItems = (subgroup.items || []).filter((item) => {
            const inTitle = String(item.title || '').toLowerCase().includes(query)
            const inUrl = String(item.url || '').toLowerCase().includes(query)
            const inTags = (item.tags || []).some((tag) => String(tag).toLowerCase().includes(query))
            return inTitle || inUrl || inTags
          })

          if (!matchedItems.length) return null
          return {
            ...subgroup,
            items: matchedItems,
          }
        })
        .filter(Boolean)

      if (!matchedSubgroups.length) return null
      return {
        ...group,
        subgroups: matchedSubgroups,
      }
    })
    .filter(Boolean)
})

const sidebarIconNodes = computed(() => {
  const nodes = []

  for (const group of filteredTreeGroups.value) {
    nodes.push({
      key: `group:${group.key}`,
      type: 'group',
      groupKey: group.key,
      group,
    })

    for (const subgroup of group.subgroups || []) {
      nodes.push({
        key: `subgroup:${group.key}:${subgroup.id}`,
        type: 'subgroup',
        groupKey: group.key,
        subgroupId: subgroup.id,
        subgroup,
      })

      for (const item of subgroup.items || []) {
        nodes.push({
          key: `item:${group.key}:${subgroup.id}:${item.id}`,
          type: 'item',
          groupKey: group.key,
          subgroupId: subgroup.id,
          itemId: item.id,
          item,
        })
      }
    }
  }

  return nodes
})

const visibleTreeItemIds = computed(() => {
  const ids = []
  for (const group of treeGroups.value) {
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        ids.push(item.id)
      }
    }
  }
  return ids
})

const pageHealthSummary = computed(() => {
  const ids = visibleTreeItemIds.value
  let online = 0

  for (const id of ids) {
    if (healthState(id)?.ok) {
      online += 1
    }
  }

  return {
    online,
    total: ids.length,
  }
})

const activePageWidgetIds = computed(() => {
  if (!activePage.value) return []

  const ids = []
  for (const block of activePage.value.blocks || []) {
    if (!isWidgetBlock(block)) continue
    ids.push(...(block.widgets || []))
  }

  return Array.from(new Set(ids))
})

const sidebarIndicators = computed(() => resolveWidgets(activePageWidgetIds.value))

const sidebarIndicatorSummary = computed(() => {
  const total = sidebarIndicators.value.length
  if (!total) return 'нет данных'
  const largeCount = sidebarIndicators.value.filter((widget) => isLargeIndicator(widget)).length
  return `${total} · больших ${largeCount}`
})

const activePageGroupBlocks = computed(() => (activePage.value?.blocks || []).filter((block) => block?.type === 'groups'))

const activeIndicatorWidget = computed(() => {
  const widget = widgetById.value.get(activeIndicatorViewId.value)
  if (!widget || !isLargeIndicator(widget)) return null
  return activePageWidgetIds.value.includes(widget.id) ? widget : null
})

function applyTheme(theme) {
  if (!theme) return
  const root = document.documentElement

  if (theme.accent) {
    root.style.setProperty('--accent', theme.accent)
    root.style.setProperty('--accent-soft', theme.accent)
  }
  if (theme.background) {
    root.style.setProperty('--bg', theme.background)
  }
  if (theme.border) {
    root.style.setProperty('--border', theme.border)
  }
  if (theme.card) {
    root.style.setProperty('--surface', theme.card)
    root.style.setProperty('--surface-strong', theme.card)
  }

  root.style.setProperty('--glow-enabled', theme.glow === false ? '0' : '1')
}

function applyGrid(grid) {
  if (!grid) return
  const root = document.documentElement

  if (grid.gap != null) {
    root.style.setProperty('--grid-gap', `${Number(grid.gap)}px`)
  }
  if (grid.card_radius != null) {
    root.style.setProperty('--card-radius', `${Number(grid.card_radius)}px`)
  }
  if (grid.columns != null) {
    root.style.setProperty('--layout-columns', String(Number(grid.columns)))
  }
}

function toggleEditMode() {
  editMode.value = !editMode.value
  saveError.value = ''
  if (!editMode.value) {
    clearDragState()
  }
}

function toggleServiceCardView() {
  serviceCardView.value = isIconCardView.value ? 'detailed' : 'icon'
}

function toggleSidebarView() {
  sidebarView.value = isSidebarIconOnly.value ? 'detailed' : 'icons'
  if (!isSidebarIconOnly.value) {
    treeFilter.value = ''
  }
}

function isSidebarIconActive(node) {
  if (!node) return false
  if (node.type === 'group') return isGroupSelected(node.groupKey)
  if (node.type === 'subgroup') return isSubgroupSelected(node.groupKey, node.subgroupId)
  if (node.type === 'item') return isItemSelected(node.itemId)
  return false
}

function sidebarIconNodeTitle(node) {
  if (!node) return ''
  if (node.type === 'group') {
    return `Группа: ${node.group?.title || ''}`
  }
  if (node.type === 'subgroup') {
    return `Подгруппа: ${node.subgroup?.title || ''}`
  }
  return `Сервис: ${node.item?.title || ''}`
}

function selectSidebarIconNode(node) {
  if (!node) return

  if (node.type === 'group') {
    expandedGroups[node.groupKey] = true
    selectedNode.groupKey = node.groupKey
    selectedNode.subgroupId = ''
    selectedNode.itemId = ''
    return
  }

  if (node.type === 'subgroup') {
    selectSubgroupNode(node.groupKey, node.subgroupId)
    return
  }

  if (node.type === 'item') {
    selectItemNode(node.groupKey, node.subgroupId, node.itemId)
  }
}

function onItemCardClick(groupKey, subgroupId, item) {
  if (!isIconCardView.value) return
  selectItemNode(groupKey, subgroupId, item.id)
  openItem(item)
}

function cloneConfig(value) {
  return JSON.parse(JSON.stringify(value))
}

function normalizeId(value, fallback = 'node') {
  const normalized = String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
  return normalized || fallback
}

function makeUniqueId(base, existingIds) {
  const normalizedBase = normalizeId(base, 'node')
  let candidate = normalizedBase
  let index = 2

  while (existingIds.has(candidate)) {
    candidate = `${normalizedBase}-${index}`
    index += 1
  }

  return candidate
}

function ensureAbsoluteUrl(rawValue) {
  const trimmed = String(rawValue || '').trim()
  if (!trimmed) {
    throw new Error('URL не может быть пустым')
  }

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
  let parsed
  try {
    parsed = new URL(withProtocol)
  } catch {
    throw new Error(`Некорректный URL: ${trimmed}`)
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`Разрешены только http/https URL: ${trimmed}`)
  }

  return parsed.toString()
}

function allSubgroupIds(cfg) {
  const ids = new Set()
  for (const group of cfg.groups || []) {
    for (const subgroup of group.subgroups || []) {
      ids.add(subgroup.id)
    }
  }
  return ids
}

function allItemIds(cfg) {
  const ids = new Set()
  for (const group of cfg.groups || []) {
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        ids.add(item.id)
      }
    }
  }
  return ids
}

function findGroup(cfg, groupId) {
  return (cfg.groups || []).find((group) => group.id === groupId) || null
}

function findSubgroup(cfg, groupId, subgroupId) {
  const group = findGroup(cfg, groupId)
  if (!group) return null
  return (group.subgroups || []).find((subgroup) => subgroup.id === subgroupId) || null
}

function isDirectGroupNode(group) {
  return String(group?.key || '').startsWith('group:')
}

function normalizeLayoutBlocks(cfg) {
  const validGroupIds = new Set((cfg.groups || []).map((group) => group.id))
  const validSubgroupIds = allSubgroupIds(cfg)
  const validGroupRefs = new Set([...validGroupIds, ...validSubgroupIds])

  for (const page of cfg.layout?.pages || []) {
    const nextBlocks = []

    for (const block of page.blocks || []) {
      if (block.type === 'groups') {
        block.group_ids = (block.group_ids || []).filter((groupId) => validGroupRefs.has(groupId))
        if (block.group_ids.length) {
          nextBlocks.push(block)
        }
        continue
      }

      if ((block.widgets || []).length) {
        nextBlocks.push(block)
      }
    }

    if (!nextBlocks.length && cfg.groups?.length) {
      nextBlocks.push({
        type: 'groups',
        group_ids: [cfg.groups[0].id],
      })
    }

    page.blocks = nextBlocks
  }
}

function ensurePageGroupsReference(cfg, pageId, groupId) {
  const pagesList = cfg.layout?.pages || []
  if (!pagesList.length) return

  const page = pagesList.find((entry) => entry.id === pageId) || pagesList[0]
  let groupsBlock = page.blocks.find((block) => block.type === 'groups')

  if (!groupsBlock) {
    groupsBlock = {
      type: 'groups',
      group_ids: [groupId],
    }
    page.blocks.push(groupsBlock)
    return
  }

  if (!groupsBlock.group_ids.includes(groupId)) {
    groupsBlock.group_ids.push(groupId)
  }
}

async function persistConfig() {
  if (!config.value) return

  saveStatus.value = 'saving'
  saveError.value = ''

  try {
    const response = await updateDashboardConfig(config.value)
    config.value = response.config

    if (!activePageId.value || !pages.value.some((page) => page.id === activePageId.value)) {
      activePageId.value = pages.value[0]?.id || ''
    }

    saveStatus.value = 'saved'
    if (saveStatusTimer) {
      clearTimeout(saveStatusTimer)
    }

    saveStatusTimer = window.setTimeout(() => {
      if (saveStatus.value === 'saved') {
        saveStatus.value = 'idle'
      }
    }, 1400)
  } catch (error) {
    saveStatus.value = 'error'
    saveError.value = error?.message || 'Ошибка сохранения YAML'
    throw error
  }
}

async function applyConfigMutation(mutator) {
  if (!config.value) return false

  const snapshot = cloneConfig(config.value)

  try {
    const result = mutator(config.value)
    if (result === false) return false

    normalizeLayoutBlocks(config.value)
    syncTreeGroupsState()
    await persistConfig()
    return true
  } catch (error) {
    config.value = snapshot
    saveStatus.value = 'error'
    saveError.value = error?.message || 'Не удалось применить изменения'
    return false
  }
}

function buildDefaultItem(itemId, title) {
  return {
    id: itemId,
    type: 'link',
    title,
    url: DEFAULT_ITEM_URL,
    icon: null,
    tags: [],
    open: 'new_tab',
  }
}

async function addGroup() {
  if (!editMode.value || !config.value) return

  const title = window.prompt('Название новой группы', 'Новая группа')
  if (title == null) return
  const normalizedTitle = title.trim()
  if (!normalizedTitle) return

  await applyConfigMutation((cfg) => {
    const groupIds = new Set((cfg.groups || []).map((group) => group.id))
    const subgroupIds = allSubgroupIds(cfg)
    const itemIds = allItemIds(cfg)

    const groupId = makeUniqueId(normalizedTitle, groupIds)
    const subgroupId = makeUniqueId(`${groupId}-core`, subgroupIds)
    const itemId = makeUniqueId(`${groupId}-service`, itemIds)

    cfg.groups.push({
      id: groupId,
      title: normalizedTitle,
      icon: 'folder',
      description: '',
      layout: 'auto',
      subgroups: [
        {
          id: subgroupId,
          title: 'Core',
          items: [buildDefaultItem(itemId, 'Новый сервис')],
        },
      ],
    })

    ensurePageGroupsReference(cfg, activePageId.value, groupId)
    expandedGroups[`group:${groupId}`] = true
    selectedNode.groupKey = `group:${groupId}`
    selectedNode.subgroupId = subgroupId
    selectedNode.itemId = itemId
  })
}

async function addSubgroup(groupId) {
  if (!editMode.value || !config.value) return

  const title = window.prompt('Название подгруппы', 'Новая подгруппа')
  if (title == null) return
  const normalizedTitle = title.trim()
  if (!normalizedTitle) return

  await applyConfigMutation((cfg) => {
    const group = findGroup(cfg, groupId)
    if (!group) throw new Error(`Группа '${groupId}' не найдена`)

    const subgroupIds = allSubgroupIds(cfg)
    const itemIds = allItemIds(cfg)
    const subgroupId = makeUniqueId(`${groupId}-${normalizedTitle}`, subgroupIds)
    const itemId = makeUniqueId(`${subgroupId}-service`, itemIds)

    group.subgroups.push({
      id: subgroupId,
      title: normalizedTitle,
      items: [buildDefaultItem(itemId, 'Новый сервис')],
    })

    expandedGroups[`group:${groupId}`] = true
    selectedNode.groupKey = `group:${groupId}`
    selectedNode.subgroupId = subgroupId
    selectedNode.itemId = itemId
  })
}

async function addItem(groupId, subgroupId) {
  if (!editMode.value || !config.value) return
  openCreateItemEditor(groupId, subgroupId)
}

function normalizeStringList(rawValue) {
  return String(rawValue || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
}

function clampNumber(value, fallback, min, max) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  const integerValue = Math.trunc(numeric)
  return Math.min(max, Math.max(min, integerValue))
}

function closeItemEditor(force = false) {
  if (itemEditor.submitting && !force) return

  itemEditor.open = false
  itemEditor.mode = 'create'
  itemEditor.groupId = ''
  itemEditor.subgroupId = ''
  itemEditor.originalItemId = ''
  itemEditor.error = ''
  itemEditor.submitting = false
  itemEditor.form = defaultItemEditorForm()
}

function openCreateItemEditor(groupId, subgroupId) {
  const subgroup = findSubgroup(config.value, groupId, subgroupId)
  if (!subgroup) {
    saveStatus.value = 'error'
    saveError.value = `Подгруппа '${subgroupId}' не найдена`
    return
  }

  itemEditor.open = true
  itemEditor.mode = 'create'
  itemEditor.groupId = groupId
  itemEditor.subgroupId = subgroupId
  itemEditor.originalItemId = ''
  itemEditor.error = ''
  itemEditor.submitting = false
  itemEditor.form = defaultItemEditorForm()
}

function openEditItemEditor(groupId, subgroupId, itemId) {
  const subgroup = findSubgroup(config.value, groupId, subgroupId)
  const item = (subgroup?.items || []).find((entry) => entry.id === itemId)
  if (!subgroup || !item) {
    saveStatus.value = 'error'
    saveError.value = `Элемент '${itemId}' не найден`
    return
  }

  itemEditor.open = true
  itemEditor.mode = 'edit'
  itemEditor.groupId = groupId
  itemEditor.subgroupId = subgroupId
  itemEditor.originalItemId = itemId
  itemEditor.error = ''
  itemEditor.submitting = false
  itemEditor.form = {
    id: item.id,
    title: item.title,
    type: item.type,
    url: String(item.url || DEFAULT_ITEM_URL),
    icon: item.icon || '',
    tagsInput: (item.tags || []).join(', '),
    open: item.open || 'new_tab',
    healthcheckEnabled: Boolean(item.type === 'link' && item.healthcheck),
    healthcheckUrl: item.type === 'link' && item.healthcheck ? String(item.healthcheck.url) : String(item.url || DEFAULT_ITEM_URL),
    healthcheckIntervalSec: item.type === 'link' && item.healthcheck ? Number(item.healthcheck.interval_sec || 30) : 30,
    healthcheckTimeoutMs: item.type === 'link' && item.healthcheck ? Number(item.healthcheck.timeout_ms || 1500) : 1500,
    iframeSandboxMode:
      item.type === 'iframe'
        ? item.iframe?.sandbox == null
          ? 'default'
          : item.iframe.sandbox
            ? 'enabled'
            : 'disabled'
        : 'default',
    iframeAllowInput: item.type === 'iframe' ? (item.iframe?.allow || []).join(', ') : '',
    iframeReferrerPolicy: item.type === 'iframe' ? item.iframe?.referrer_policy || '' : '',
    authProfile: item.type === 'iframe' ? item.auth_profile || '' : '',
  }
}

function buildItemFromEditorForm(cfg) {
  const form = itemEditor.form
  const title = String(form.title || '').trim()
  if (!title) {
    throw new Error('Название сервиса обязательно')
  }

  const normalizedType = String(form.type || '').trim().toLowerCase()
  if (!['link', 'iframe'].includes(normalizedType)) {
    throw new Error("Тип сервиса должен быть 'link' или 'iframe'")
  }

  const openMode = String(form.open || 'new_tab')
  if (!['new_tab', 'same_tab'].includes(openMode)) {
    throw new Error("Параметр open должен быть 'new_tab' или 'same_tab'")
  }

  const url = ensureAbsoluteUrl(form.url || DEFAULT_ITEM_URL)
  const itemIds = allItemIds(cfg)
  if (itemEditor.mode === 'edit') {
    itemIds.delete(itemEditor.originalItemId)
  }

  const rawId = String(form.id || '').trim()
  const generatedBase = `${itemEditor.subgroupId}-${title}`
  const normalizedId = normalizeId(rawId || generatedBase, 'service')
  const nextId = rawId ? normalizedId : makeUniqueId(normalizedId, itemIds)

  if (rawId && itemIds.has(nextId)) {
    throw new Error(`ID '${nextId}' уже существует`)
  }

  const baseItem = {
    id: nextId,
    type: normalizedType,
    title,
    url,
    icon: String(form.icon || '').trim() || null,
    tags: normalizeStringList(form.tagsInput),
    open: openMode,
  }

  if (normalizedType === 'link') {
    const linkItem = { ...baseItem }

    if (form.healthcheckEnabled) {
      const healthcheckUrl = ensureAbsoluteUrl(form.healthcheckUrl || url)
      linkItem.healthcheck = {
        type: 'http',
        url: healthcheckUrl,
        interval_sec: clampNumber(form.healthcheckIntervalSec, 30, 1, 3600),
        timeout_ms: clampNumber(form.healthcheckTimeoutMs, 1500, 100, 120000),
      }
    }

    return linkItem
  }

  const sandboxMode = String(form.iframeSandboxMode || 'default')
  let sandboxValue = null
  if (sandboxMode === 'enabled') sandboxValue = true
  if (sandboxMode === 'disabled') sandboxValue = false

  const authProfile = String(form.authProfile || '').trim()
  if (authProfile && !authProfileOptions.value.some((profile) => profile.id === authProfile)) {
    throw new Error(`Auth profile '${authProfile}' не найден`)
  }

  const iframeItem = {
    ...baseItem,
    iframe: {
      sandbox: sandboxValue,
      allow: normalizeStringList(form.iframeAllowInput),
      referrer_policy: String(form.iframeReferrerPolicy || '').trim() || null,
    },
  }

  if (authProfile) {
    iframeItem.auth_profile = authProfile
  }

  return iframeItem
}

async function submitItemEditor() {
  if (!itemEditor.open || itemEditor.submitting || !config.value) return

  itemEditor.submitting = true
  itemEditor.error = ''

  const success = await applyConfigMutation((cfg) => {
    const subgroup = findSubgroup(cfg, itemEditor.groupId, itemEditor.subgroupId)
    if (!subgroup) {
      throw new Error(`Подгруппа '${itemEditor.subgroupId}' не найдена`)
    }

    const nextItem = buildItemFromEditorForm(cfg)

    if (itemEditor.mode === 'create') {
      subgroup.items.push(nextItem)
      selectedNode.groupKey = `group:${itemEditor.groupId}`
      selectedNode.subgroupId = itemEditor.subgroupId
      selectedNode.itemId = nextItem.id
      return true
    }

    const index = (subgroup.items || []).findIndex((entry) => entry.id === itemEditor.originalItemId)
    if (index < 0) {
      throw new Error(`Элемент '${itemEditor.originalItemId}' не найден`)
    }

    subgroup.items.splice(index, 1, nextItem)
    selectedNode.groupKey = `group:${itemEditor.groupId}`
    selectedNode.subgroupId = itemEditor.subgroupId
    if (selectedNode.itemId === itemEditor.originalItemId || !selectedNode.itemId) {
      selectedNode.itemId = nextItem.id
    }
    return true
  })

  itemEditor.submitting = false
  if (success) {
    closeItemEditor(true)
  } else {
    itemEditor.error = saveError.value || 'Не удалось сохранить сервис'
  }
}

async function editGroup(groupId) {
  if (!editMode.value || !config.value) return

  const group = findGroup(config.value, groupId)
  if (!group) return

  const nextTitle = window.prompt('Название группы', group.title)
  if (nextTitle == null) return

  const nextDescription = window.prompt('Описание группы', group.description || '')
  if (nextDescription == null) return

  const nextLayout = window.prompt('Режим группы (auto | full | inline)', group.layout || 'auto')
  if (nextLayout == null) return

  await applyConfigMutation((cfg) => {
    const target = findGroup(cfg, groupId)
    if (!target) throw new Error(`Группа '${groupId}' не найдена`)

    const normalizedLayout = String(nextLayout || '').trim().toLowerCase() || 'auto'
    if (!['auto', 'full', 'inline'].includes(normalizedLayout)) {
      throw new Error("Режим группы должен быть 'auto', 'full' или 'inline'")
    }

    target.title = nextTitle.trim() || target.title
    target.description = nextDescription.trim()
    target.layout = normalizedLayout
  })
}

async function editSubgroup(groupId, subgroupId) {
  if (!editMode.value || !config.value) return

  const subgroup = findSubgroup(config.value, groupId, subgroupId)
  if (!subgroup) return

  const nextTitle = window.prompt('Название подгруппы', subgroup.title)
  if (nextTitle == null) return

  await applyConfigMutation((cfg) => {
    const target = findSubgroup(cfg, groupId, subgroupId)
    if (!target) throw new Error(`Подгруппа '${subgroupId}' не найдена`)

    target.title = nextTitle.trim() || target.title
  })
}

async function editItem(groupId, subgroupId, itemId) {
  if (!editMode.value || !config.value) return
  openEditItemEditor(groupId, subgroupId, itemId)
}

async function removeGroup(groupId) {
  if (!editMode.value || !config.value) return

  const group = findGroup(config.value, groupId)
  if (!group) return

  if (config.value.groups.length <= 1) {
    saveStatus.value = 'error'
    saveError.value = 'Нельзя удалить последнюю группу.'
    return
  }

  if (!window.confirm(`Удалить группу "${group.title}"?`)) return

  await applyConfigMutation((cfg) => {
    const index = (cfg.groups || []).findIndex((entry) => entry.id === groupId)
    if (index < 0) return false
    cfg.groups.splice(index, 1)

    selectedNode.groupKey = ''
    selectedNode.subgroupId = ''
    selectedNode.itemId = ''
  })
}

async function removeSubgroup(groupId, subgroupId) {
  if (!editMode.value || !config.value) return

  const group = findGroup(config.value, groupId)
  const subgroup = (group?.subgroups || []).find((entry) => entry.id === subgroupId)
  if (!group || !subgroup) return

  if (group.subgroups.length <= 1) {
    saveStatus.value = 'error'
    saveError.value = 'В группе должна остаться хотя бы одна подгруппа.'
    return
  }

  if (!window.confirm(`Удалить подгруппу "${subgroup.title}"?`)) return

  await applyConfigMutation((cfg) => {
    const targetGroup = findGroup(cfg, groupId)
    if (!targetGroup) return false

    const index = (targetGroup.subgroups || []).findIndex((entry) => entry.id === subgroupId)
    if (index < 0) return false
    targetGroup.subgroups.splice(index, 1)

    selectedNode.subgroupId = ''
    selectedNode.itemId = ''
  })
}

async function removeItem(groupId, subgroupId, itemId) {
  if (!editMode.value || !config.value) return

  const subgroup = findSubgroup(config.value, groupId, subgroupId)
  const item = (subgroup?.items || []).find((entry) => entry.id === itemId)
  if (!subgroup || !item) return

  if (subgroup.items.length <= 1) {
    saveStatus.value = 'error'
    saveError.value = 'В подгруппе должен остаться хотя бы один элемент.'
    return
  }

  if (!window.confirm(`Удалить сервис "${item.title}"?`)) return

  await applyConfigMutation((cfg) => {
    const targetSubgroup = findSubgroup(cfg, groupId, subgroupId)
    if (!targetSubgroup) return false

    const index = (targetSubgroup.items || []).findIndex((entry) => entry.id === itemId)
    if (index < 0) return false
    targetSubgroup.items.splice(index, 1)

    if (selectedNode.itemId === itemId) {
      selectedNode.itemId = ''
    }
  })
}

function clearDragState() {
  dragState.type = ''
  dragState.groupId = ''
  dragState.subgroupId = ''
  dragState.itemId = ''
}

function onGroupDragStart(event, group) {
  if (!editMode.value) return
  if (!isDirectGroupNode(group)) return
  const groupId = group.id
  dragState.type = 'group'
  dragState.groupId = groupId
  dragState.subgroupId = ''
  dragState.itemId = ''
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', `group:${groupId}`)
  }
}

function onSubgroupDragStart(event, groupId, subgroupId) {
  if (!editMode.value) return
  dragState.type = 'subgroup'
  dragState.groupId = groupId
  dragState.subgroupId = subgroupId
  dragState.itemId = ''
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', `subgroup:${subgroupId}`)
  }
}

function onItemDragStart(event, groupId, subgroupId, itemId) {
  if (!editMode.value) return
  dragState.type = 'item'
  dragState.groupId = groupId
  dragState.subgroupId = subgroupId
  dragState.itemId = itemId
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', `item:${itemId}`)
  }
}

function onGroupDragOver(event, targetGroup) {
  if (!editMode.value) return
  if (!isDirectGroupNode(targetGroup)) return
  const targetGroupId = targetGroup.id
  if (dragState.type !== 'group') return
  if (dragState.groupId === targetGroupId) return
  event.preventDefault()
}

async function onGroupDrop(event, targetGroup) {
  if (!editMode.value) return
  if (!isDirectGroupNode(targetGroup)) return
  const targetGroupId = targetGroup.id
  if (dragState.type !== 'group') return
  if (!dragState.groupId || dragState.groupId === targetGroupId) return
  event.preventDefault()

  const sourceGroupId = dragState.groupId
  clearDragState()

  await applyConfigMutation((cfg) => moveGroup(cfg, sourceGroupId, targetGroupId))
}

function onSubgroupDragOver(event, targetGroupId, targetSubgroupId) {
  if (!editMode.value) return
  if (dragState.type === 'subgroup') {
    if (dragState.subgroupId === targetSubgroupId) return
    event.preventDefault()
    return
  }

  if (dragState.type === 'item') {
    event.preventDefault()
  }
}

async function onSubgroupDrop(event, targetGroupId, targetSubgroupId) {
  if (!editMode.value) return

  if (dragState.type === 'subgroup') {
    event.preventDefault()
    const sourceGroupId = dragState.groupId
    const sourceSubgroupId = dragState.subgroupId
    clearDragState()

    await applyConfigMutation((cfg) => moveSubgroup(cfg, sourceGroupId, sourceSubgroupId, targetGroupId, targetSubgroupId))
    return
  }

  if (dragState.type === 'item') {
    event.preventDefault()
    const sourceGroupId = dragState.groupId
    const sourceSubgroupId = dragState.subgroupId
    const sourceItemId = dragState.itemId
    clearDragState()

    await applyConfigMutation((cfg) =>
      moveItemToSubgroupEnd(cfg, sourceGroupId, sourceSubgroupId, sourceItemId, targetGroupId, targetSubgroupId)
    )
  }
}

function onItemDragOver(event, _targetGroupId, _targetSubgroupId, targetItemId) {
  if (!editMode.value) return
  if (dragState.type !== 'item') return
  if (dragState.itemId === targetItemId) return
  event.preventDefault()
}

async function onItemDrop(event, targetGroupId, targetSubgroupId, targetItemId) {
  if (!editMode.value) return
  if (dragState.type !== 'item') return
  if (!dragState.itemId || dragState.itemId === targetItemId) return
  event.preventDefault()

  const sourceGroupId = dragState.groupId
  const sourceSubgroupId = dragState.subgroupId
  const sourceItemId = dragState.itemId
  clearDragState()

  await applyConfigMutation((cfg) =>
    moveItemBefore(cfg, sourceGroupId, sourceSubgroupId, sourceItemId, targetGroupId, targetSubgroupId, targetItemId)
  )
}

function moveGroup(cfg, sourceGroupId, targetGroupId) {
  const groupsList = cfg.groups || []
  const sourceIndex = groupsList.findIndex((group) => group.id === sourceGroupId)
  const targetIndex = groupsList.findIndex((group) => group.id === targetGroupId)

  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return false

  const [moved] = groupsList.splice(sourceIndex, 1)
  const insertIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex
  groupsList.splice(insertIndex, 0, moved)
  return true
}

function moveSubgroup(cfg, sourceGroupId, sourceSubgroupId, targetGroupId, targetSubgroupId) {
  const sourceGroup = findGroup(cfg, sourceGroupId)
  const targetGroup = findGroup(cfg, targetGroupId)
  if (!sourceGroup || !targetGroup) return false

  const sourceIndex = (sourceGroup.subgroups || []).findIndex((subgroup) => subgroup.id === sourceSubgroupId)
  const targetIndex = (targetGroup.subgroups || []).findIndex((subgroup) => subgroup.id === targetSubgroupId)
  if (sourceIndex < 0 || targetIndex < 0) return false

  if (sourceGroupId !== targetGroupId && sourceGroup.subgroups.length <= 1) {
    throw new Error('В исходной группе должна остаться минимум одна подгруппа.')
  }

  const [moved] = sourceGroup.subgroups.splice(sourceIndex, 1)

  if (sourceGroupId === targetGroupId) {
    const insertIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex
    sourceGroup.subgroups.splice(insertIndex, 0, moved)
    return true
  }

  targetGroup.subgroups.splice(targetIndex, 0, moved)
  return true
}

function moveItemBefore(cfg, sourceGroupId, sourceSubgroupId, sourceItemId, targetGroupId, targetSubgroupId, targetItemId) {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId)
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId)
  if (!sourceSubgroup || !targetSubgroup) return false

  const sourceIndex = (sourceSubgroup.items || []).findIndex((item) => item.id === sourceItemId)
  const targetIndex = (targetSubgroup.items || []).findIndex((item) => item.id === targetItemId)
  if (sourceIndex < 0 || targetIndex < 0) return false

  if (sourceSubgroupId !== targetSubgroupId && sourceSubgroup.items.length <= 1) {
    throw new Error('В исходной подгруппе должен остаться минимум один элемент.')
  }

  const [moved] = sourceSubgroup.items.splice(sourceIndex, 1)

  if (sourceSubgroupId === targetSubgroupId) {
    const insertIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex
    sourceSubgroup.items.splice(insertIndex, 0, moved)
    return true
  }

  targetSubgroup.items.splice(targetIndex, 0, moved)
  return true
}

function moveItemToSubgroupEnd(cfg, sourceGroupId, sourceSubgroupId, sourceItemId, targetGroupId, targetSubgroupId) {
  const sourceSubgroup = findSubgroup(cfg, sourceGroupId, sourceSubgroupId)
  const targetSubgroup = findSubgroup(cfg, targetGroupId, targetSubgroupId)
  if (!sourceSubgroup || !targetSubgroup) return false

  const sourceIndex = (sourceSubgroup.items || []).findIndex((item) => item.id === sourceItemId)
  if (sourceIndex < 0) return false

  if (sourceSubgroupId !== targetSubgroupId && sourceSubgroup.items.length <= 1) {
    throw new Error('В исходной подгруппе должен остаться минимум один элемент.')
  }

  const [moved] = sourceSubgroup.items.splice(sourceIndex, 1)
  targetSubgroup.items.push(moved)
  return true
}

function isWidgetBlock(block) {
  return block?.type === 'widget_row' || block?.type === 'widget_grid'
}

function resolveWidgets(widgetIds = []) {
  return widgetIds
    .map((widgetId) => widgetById.value.get(widgetId))
    .filter(Boolean)
}

function isLargeIndicator(widget) {
  return LARGE_INDICATOR_TYPES.has(String(widget?.type || ''))
}

function indicatorPreviewEntries(widget) {
  return statListEntries(widget).slice(0, 2)
}

function openIndicatorView(widgetId) {
  const widget = sidebarIndicators.value.find((entry) => entry.id === widgetId)
  if (!widget || !isLargeIndicator(widget)) return
  activeIndicatorViewId.value = widget.id
}

function selectSidebarIndicator(widget) {
  if (isLargeIndicator(widget)) {
    openIndicatorView(widget.id)
  }
}

function resolveBlockGroups(groupIds = []) {
  const resolved = []

  for (const id of groupIds) {
    const group = groupById.value.get(id)
    if (group) {
      resolved.push({
        key: `group:${group.id}`,
        id: group.id,
        title: group.title,
        icon: group.icon || null,
        description: group.description || '',
        layout: group.layout || 'auto',
        subgroups: group.subgroups || [],
      })
      continue
    }

    const subgroupRef = subgroupById.value.get(id)
    if (subgroupRef) {
      resolved.push({
        key: `subgroup:${subgroupRef.subgroup.id}`,
        id: subgroupRef.group.id,
        title: subgroupRef.group.title,
        icon: subgroupRef.group.icon || null,
        description: subgroupRef.group.description || '',
        layout: subgroupRef.group.layout || 'auto',
        subgroups: [subgroupRef.subgroup],
      })
    }
  }

  return resolved
}

function syncTreeGroupsState() {
  const activeKeys = new Set(treeGroups.value.map((group) => group.key))

  for (const key of Object.keys(expandedGroups)) {
    if (!activeKeys.has(key)) {
      delete expandedGroups[key]
    }
  }

  for (const group of treeGroups.value) {
    if (expandedGroups[group.key] == null) {
      expandedGroups[group.key] = true
    }
  }

  if (selectedNode.groupKey && !activeKeys.has(selectedNode.groupKey)) {
    clearSelectedNode()
  }
}

function clearSelectedNode() {
  selectedNode.groupKey = ''
  selectedNode.subgroupId = ''
  selectedNode.itemId = ''
}

function toggleGroupNode(groupKey) {
  expandedGroups[groupKey] = !isGroupExpanded(groupKey)
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = ''
  selectedNode.itemId = ''
}

function selectSubgroupNode(groupKey, subgroupId) {
  expandedGroups[groupKey] = true
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = subgroupId
  selectedNode.itemId = ''
}

function selectItemNode(groupKey, subgroupId, itemId) {
  expandedGroups[groupKey] = true
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = subgroupId
  selectedNode.itemId = itemId
}

function isGroupExpanded(groupKey) {
  return Boolean(expandedGroups[groupKey])
}

function isGroupSelected(groupKey) {
  return selectedNode.groupKey === groupKey && !selectedNode.subgroupId && !selectedNode.itemId
}

function isSubgroupSelected(groupKey, subgroupId) {
  return selectedNode.groupKey === groupKey && selectedNode.subgroupId === subgroupId && !selectedNode.itemId
}

function isItemSelected(itemId) {
  return selectedNode.itemId === itemId
}

function filteredBlockGroups(groupIds = []) {
  const groups = resolveBlockGroups(groupIds)

  if (!selectedNode.groupKey && !selectedNode.subgroupId && !selectedNode.itemId) {
    const visibleCount = groups.length
    return groups.map((group) => ({ ...group, __visibleCount: visibleCount }))
  }

  const filtered = groups
    .map((group) => {
      if (selectedNode.groupKey && group.key !== selectedNode.groupKey) {
        return null
      }

      let nextSubgroups = group.subgroups || []

      if (selectedNode.subgroupId) {
        nextSubgroups = nextSubgroups.filter((subgroup) => subgroup.id === selectedNode.subgroupId)
      }

      if (selectedNode.itemId) {
        nextSubgroups = nextSubgroups
          .map((subgroup) => ({
            ...subgroup,
            items: (subgroup.items || []).filter((item) => item.id === selectedNode.itemId),
          }))
          .filter((subgroup) => subgroup.items.length > 0)
      }

      if (!nextSubgroups.length) {
        return null
      }

      return {
        ...group,
        subgroups: nextSubgroups,
      }
    })
    .filter(Boolean)

  const visibleCount = filtered.length
  return filtered.map((group) => ({ ...group, __visibleCount: visibleCount }))
}

function isInlineGroupLayout(group) {
  const mode = String(group?.layout || 'auto').toLowerCase()
  if (mode === 'inline') return true
  if (mode === 'full') return false
  return Number(group?.__visibleCount || 0) > 1
}

function groupTotalItems(group) {
  return (group.subgroups || []).reduce((acc, subgroup) => acc + (subgroup.items || []).length, 0)
}

function groupOnlineItems(group) {
  let online = 0
  for (const subgroup of group.subgroups || []) {
    for (const item of subgroup.items || []) {
      if (healthState(item.id)?.ok) {
        online += 1
      }
    }
  }
  return online
}

function clearItemFaviconFailures() {
  for (const key of Object.keys(itemFaviconFailures)) {
    delete itemFaviconFailures[key]
  }
}

function faviconOriginFromUrl(rawValue) {
  const trimmed = String(rawValue || '').trim()
  if (!trimmed) return ''

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
  try {
    const parsed = new URL(withProtocol)
    if (!['http:', 'https:'].includes(parsed.protocol)) return ''
    return parsed.origin
  } catch {
    return ''
  }
}

function itemFaviconKey(item) {
  const origin = faviconOriginFromUrl(item?.url)
  if (!origin) return ''
  const itemId = String(item?.id || '')
  return `${itemId}|${origin}`
}

function itemFaviconSrc(item) {
  const origin = faviconOriginFromUrl(item?.url)
  if (!origin) return ''

  const key = itemFaviconKey(item)
  if (key && itemFaviconFailures[key]) return ''
  return `${origin}/favicon.ico`
}

function markItemFaviconFailed(item) {
  const key = itemFaviconKey(item)
  if (!key) return
  itemFaviconFailures[key] = true
}

function resolvePageIcon(page) {
  return pickSemanticIcon([page?.icon, page?.title, page?.id], LayoutDashboard)
}

function resolveGroupIcon(group) {
  return pickSemanticIcon([group?.icon, group?.title, group?.id, group?.description], FolderTree)
}

function resolveSubgroupIcon(subgroup) {
  return pickSemanticIcon([subgroup?.icon, subgroup?.title, subgroup?.id], Folder)
}

function resolveItemIcon(item) {
  return pickSemanticIcon(
    [item?.icon, item?.title, item?.id, item?.type, item?.url, ...(item?.tags || [])],
    item?.type === 'iframe' ? Globe : Link2
  )
}

function resolveWidgetIcon(widget) {
  return pickSemanticIcon([widget?.icon, widget?.title, widget?.id, widget?.type, widget?.data?.endpoint], Gauge)
}

function widgetState(widgetId) {
  return widgetStates[widgetId] || null
}

function actionKey(widgetId, actionId) {
  return `${widgetId}:${actionId}`
}

function isActionBusy(widgetId, actionId) {
  return Boolean(actionBusy[actionKey(widgetId, actionId)])
}

function resolveExpression(payload, expression) {
  if (!expression || typeof expression !== 'string') return null
  if (expression === '$') return payload
  if (!expression.startsWith('$.')) return null

  let current = payload
  const parts = expression.slice(2).split('.')

  for (const part of parts) {
    if (current == null) return null

    const arrayMatch = part.match(/^(.*)\[\*\]$/)
    if (arrayMatch) {
      const key = arrayMatch[1]
      const value = key ? current?.[key] : current
      return Array.isArray(value) ? value : []
    }

    current = current?.[part]
  }

  return current
}

function statCardValue(widget) {
  const payload = widgetState(widget.id)?.payload
  const value = resolveExpression(payload, widget.data?.mapping?.value)
  return value ?? '—'
}

function statCardSubtitle(widget) {
  const payload = widgetState(widget.id)?.payload
  const subtitle = resolveExpression(payload, widget.data?.mapping?.subtitle)
  return subtitle ?? ''
}

function statCardTrend(widget) {
  const payload = widgetState(widget.id)?.payload
  const trend = resolveExpression(payload, widget.data?.mapping?.trend)
  return trend ?? ''
}

function statListEntries(widget) {
  const payload = widgetState(widget.id)?.payload
  const mapping = widget.data?.mapping || {}
  const items = resolveExpression(payload, mapping.items)

  if (!Array.isArray(items)) return []

  return items.map((entry) => {
    const title = resolveExpression(entry, mapping.item_title) ?? '-'
    const value = resolveExpression(entry, mapping.item_value) ?? '-'
    return { title, value }
  })
}

function tableRows(widget) {
  const payload = widgetState(widget.id)?.payload
  const rowsExpression = widget.data?.mapping?.rows
  const fromExpression = resolveExpression(payload, rowsExpression)

  if (Array.isArray(fromExpression)) return fromExpression
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

function normalizeEndpoint(endpoint) {
  if (!endpoint) return ''
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) return endpoint
  if (endpoint.startsWith('/')) return endpoint
  return `/${endpoint}`
}

function resetWidgetPolling() {
  for (const timer of widgetIntervals.values()) {
    clearInterval(timer)
  }
  widgetIntervals.clear()
}

function stopHealthPolling() {
  if (healthPollTimer) {
    clearInterval(healthPollTimer)
    healthPollTimer = 0
  }
}

function healthState(itemId) {
  return healthStates[itemId] || null
}

function healthClass(itemId) {
  const state = healthState(itemId)
  if (!state) return 'unknown'
  return state.ok ? 'ok' : 'down'
}

function healthLabel(itemId) {
  const state = healthState(itemId)
  if (!state) return 'Проверка...'

  if (state.ok) {
    if (state.latency_ms != null) {
      return `Online • ${state.latency_ms} ms`
    }
    return 'Online'
  }

  if (state.error) {
    return `Offline • ${state.error}`
  }

  if (state.status_code != null) {
    return `Offline • HTTP ${state.status_code}`
  }

  return 'Offline'
}

async function refreshHealth() {
  const ids = visibleTreeItemIds.value
  if (!ids.length) return

  try {
    const payload = await fetchDashboardHealth(ids)
    for (const itemStatus of payload.items || []) {
      healthStates[itemStatus.item_id] = itemStatus
    }
  } catch {
    for (const id of ids) {
      if (!healthStates[id]) {
        healthStates[id] = {
          item_id: id,
          ok: false,
          checked_url: '',
          status_code: null,
          latency_ms: null,
          error: 'healthcheck unavailable',
        }
      }
    }
  }
}

async function startHealthPolling() {
  stopHealthPolling()
  await refreshHealth()

  healthPollTimer = window.setInterval(() => {
    refreshHealth()
  }, HEALTH_REFRESH_MS)
}

async function refreshWidget(widgetId) {
  const widget = widgetById.value.get(widgetId)
  if (!widget) return

  const endpoint = normalizeEndpoint(widget.data?.endpoint)
  if (!endpoint) return

  if (!widgetStates[widgetId]) {
    widgetStates[widgetId] = {
      loading: false,
      error: '',
      payload: null,
      lastUpdated: 0,
    }
  }

  const state = widgetStates[widgetId]
  state.loading = true
  state.error = ''

  try {
    state.payload = await requestJson(endpoint)
    state.lastUpdated = Date.now()
  } catch (error) {
    state.error = error?.message || 'Ошибка загрузки виджета'
  } finally {
    state.loading = false
  }
}

async function initWidgetPolling() {
  resetWidgetPolling()

  const initialLoads = []

  for (const widget of widgets.value) {
    initialLoads.push(refreshWidget(widget.id))

    if (!normalizeEndpoint(widget.data?.endpoint)) continue
    const intervalMs = Math.max(1, Number(widget.data?.refresh_sec || 0)) * 1000

    const timer = window.setInterval(() => {
      refreshWidget(widget.id)
    }, intervalMs)

    widgetIntervals.set(widget.id, timer)
  }

  await Promise.all(initialLoads)
}

async function runWidgetAction(widgetId, action) {
  const key = actionKey(widgetId, action.id)
  const endpoint = normalizeEndpoint(action.endpoint)
  if (!endpoint) return

  actionBusy[key] = true

  try {
    await requestJson(endpoint, {
      method: String(action.method || 'GET').toUpperCase(),
    })
    await refreshWidget(widgetId)
  } catch (error) {
    if (!widgetStates[widgetId]) {
      widgetStates[widgetId] = { loading: false, error: '', payload: null, lastUpdated: 0 }
    }
    widgetStates[widgetId].error = error?.message || 'Не удалось выполнить действие'
  } finally {
    actionBusy[key] = false
  }
}

async function loadConfig() {
  loadingConfig.value = true
  configError.value = ''
  saveStatus.value = 'idle'
  saveError.value = ''
  clearItemFaviconFailures()

  try {
    const data = await fetchDashboardConfig()
    config.value = data

    if (!activePageId.value || !pages.value.some((page) => page.id === activePageId.value)) {
      activePageId.value = pages.value[0]?.id || ''
    }

    clearSelectedNode()
    syncTreeGroupsState()
    applyTheme(data?.ui?.theme)
    applyGrid(data?.ui?.grid)
    await initWidgetPolling()
    await startHealthPolling()
  } catch (error) {
    configError.value = error?.message || 'Не удалось загрузить dashboard-конфигурацию'
    config.value = null
    resetWidgetPolling()
    stopHealthPolling()
  } finally {
    loadingConfig.value = false
  }
}

async function openIframeItem(item) {
  const defaultSandbox = Boolean(config.value?.security?.iframe?.default_sandbox ?? true)
  const sandboxValue = item?.iframe?.sandbox

  iframeModal.open = true
  iframeModal.title = item.title
  iframeModal.src = ''
  iframeModal.error = ''
  iframeModal.loading = true
  iframeModal.sandbox = sandboxValue == null ? defaultSandbox : Boolean(sandboxValue)
  iframeModal.allow = Array.isArray(item?.iframe?.allow) ? item.iframe.allow.join('; ') : ''
  iframeModal.referrerPolicy = item?.iframe?.referrer_policy || ''

  try {
    const source = await fetchIframeSource(item.id)
    iframeModal.src = source.src
  } catch (error) {
    iframeModal.error = error?.message || 'Не удалось подготовить iframe'
  } finally {
    iframeModal.loading = false
  }
}

function closeIframeModal() {
  iframeModal.open = false
  iframeModal.title = ''
  iframeModal.src = ''
  iframeModal.error = ''
  iframeModal.loading = false
  iframeModal.sandbox = false
  iframeModal.allow = ''
  iframeModal.referrerPolicy = ''
}

function openLinkItem(item) {
  if (item.open === 'same_tab') {
    window.location.assign(item.url)
    return
  }
  window.open(item.url, '_blank', 'noopener,noreferrer')
}

function openItem(item) {
  if (item.type === 'iframe') {
    openIframeItem(item)
    return
  }

  openLinkItem(item)
}

async function copyUrl(url) {
  if (!navigator.clipboard?.writeText) return

  try {
    await navigator.clipboard.writeText(url)
  } catch {
    // ignore clipboard errors
  }
}

function formatLanMoment(value) {
  if (!value) return '—'
  const timestamp = new Date(value)
  if (Number.isNaN(timestamp.getTime())) return '—'
  return timestamp.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatLanDuration(durationMs) {
  const value = Number(durationMs || 0)
  if (!Number.isFinite(value) || value <= 0) return '—'
  if (value < 1000) return `${Math.round(value)} ms`
  return `${(value / 1000).toFixed(2)} s`
}

function openLanHostModal(host) {
  if (!host) return
  lanHostModal.host = host
  lanHostModal.open = true
}

function closeLanHostModal() {
  lanHostModal.open = false
  lanHostModal.host = null
}

function lanPortsLabel(host) {
  const ports = host?.open_ports || []
  if (!ports.length) return '—'
  return ports
    .map((entry) => (entry?.service ? `${entry.port} (${entry.service})` : `${entry.port}`))
    .join(', ')
}

function formatLanHttpStatus(endpoint) {
  if (!endpoint) return '—'
  if (endpoint.error) return endpoint.error
  if (endpoint.status_code == null) return '—'
  return `HTTP ${endpoint.status_code}`
}

async function refreshLanScanState({ silent = false } = {}) {
  if (lanScanRefreshInFlight) return
  lanScanRefreshInFlight = true

  if (!silent) {
    lanScanLoading.value = true
  }

  try {
    lanScanState.value = await fetchLanScanState()
    lanScanError.value = ''
  } catch (error) {
    lanScanError.value = error?.message || 'Не удалось загрузить состояние сканера LAN'
  } finally {
    lanScanRefreshInFlight = false
    if (!silent) {
      lanScanLoading.value = false
    }
  }
}

function stopLanScanPolling() {
  if (!lanScanPollTimer) return
  window.clearInterval(lanScanPollTimer)
  lanScanPollTimer = 0
}

function startLanScanPolling() {
  stopLanScanPolling()
  lanScanPollTimer = window.setInterval(() => {
    refreshLanScanState({ silent: true })
  }, LAN_SCAN_POLL_MS)
}

async function runLanScanNow() {
  if (lanScanActionBusy.value) return
  lanScanActionBusy.value = true

  try {
    const payload = await triggerLanScan()
    lanScanState.value = payload?.state || lanScanState.value
    lanScanError.value = payload?.accepted || payload?.state?.queued ? '' : payload?.message || ''
  } catch (error) {
    lanScanError.value = error?.message || 'Не удалось запустить сканирование LAN'
  } finally {
    lanScanActionBusy.value = false
    refreshLanScanState({ silent: true })
  }
}

function initParticles(containerId, config) {
  if (!window.particlesJS) return
  const container = document.getElementById(containerId)
  if (!container) return
  container.innerHTML = ''
  window.particlesJS(containerId, config)
}

function initSidebarParticles() {
  initParticles(SIDEBAR_PARTICLES_ID, SIDEBAR_PARTICLES_CONFIG)
}

function initHeroParticles() {
  initParticles(HERO_TITLE_PARTICLES_ID, HERO_PARTICLES_CONFIG)
  initParticles(HERO_CONTROLS_PARTICLES_ID, HERO_PARTICLES_CONFIG)
}

watch(
  () => activePage.value?.id,
  async () => {
    activeIndicatorViewId.value = ''
    treeFilter.value = ''
    clearSelectedNode()
    syncTreeGroupsState()
    refreshHealth()
    await nextTick()
    initHeroParticles()
  }
)

watch(
  () => activeIndicatorWidget.value?.id,
  async () => {
    await nextTick()
    initHeroParticles()
  }
)

watch(
  () => activePageWidgetIds.value,
  (widgetIds) => {
    if (activeIndicatorViewId.value && !widgetIds.includes(activeIndicatorViewId.value)) {
      activeIndicatorViewId.value = ''
    }
  },
  { deep: true }
)

watch(
  () => treeGroups.value,
  () => {
    syncTreeGroupsState()
    refreshHealth()
  },
  { deep: true }
)

watch(
  () => isLanPage.value,
  (active) => {
    if (active) {
      refreshLanScanState()
      startLanScanPolling()
      return
    }
    closeLanHostModal()
    stopLanScanPolling()
  }
)

onMounted(async () => {
  initSidebarParticles()
  await loadConfig()
  await nextTick()
  initHeroParticles()
})

onBeforeUnmount(() => {
  resetWidgetPolling()
  stopHealthPolling()
  stopLanScanPolling()
  closeLanHostModal()
  if (saveStatusTimer) {
    clearTimeout(saveStatusTimer)
    saveStatusTimer = 0
  }
})
</script>

import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  fetchDashboardConfig,
  fetchDashboardHealth,
  fetchIframeSource,
  fetchLanScanState,
  requestJson,
  triggerLanScan,
  updateDashboardConfig,
} from '../services/dashboardApi.js'
import { BRAND_ICON_BY_KEY, createBrandIcon } from './dashboard/icons/brandIcons.js'
import { ICON_BY_KEY, ICON_RULES } from './dashboard/icons/keywordIcons.js'
import {
  fromToken,
  normalizeIconToken,
  pickSemanticIcon,
  resolveGroupIcon as resolveGroupIconSemantic,
  resolveItemIcon as resolveItemIconSemantic,
  resolvePageIcon as resolvePageIconSemantic,
  resolveSubgroupIcon as resolveSubgroupIconSemantic,
  resolveWidgetIcon as resolveWidgetIconSemantic,
} from './dashboard/icons/semanticResolver.js'

let dashboardStore = null

export function useDashboardStore() {
  if (dashboardStore) {
    return dashboardStore
  }
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
    return resolvePageIconSemantic(page)
  }
  
  function resolveGroupIcon(group) {
    return resolveGroupIconSemantic(group)
  }
  
  function resolveSubgroupIcon(subgroup) {
    return resolveSubgroupIconSemantic(subgroup)
  }
  
  function resolveItemIcon(item) {
    return resolveItemIconSemantic(item)
  }
  
  function resolveWidgetIcon(widget) {
    return resolveWidgetIconSemantic(widget)
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

    dashboardStore = null
  })

  dashboardStore = {
    BRAND_ICON_BY_KEY,
    DEFAULT_ITEM_URL,
    EMBLEM_SRC,
    HEALTH_REFRESH_MS,
    HERO_CONTROLS_PARTICLES_ID,
    HERO_PARTICLES_CONFIG,
    HERO_TITLE_PARTICLES_ID,
    ICON_BY_KEY,
    ICON_RULES,
    LAN_PAGE_ID,
    LAN_SCAN_POLL_MS,
    LARGE_INDICATOR_TYPES,
    SIDEBAR_PARTICLES_CONFIG,
    SIDEBAR_PARTICLES_ID,
    actionBusy,
    actionKey,
    activeIndicatorViewId,
    activeIndicatorWidget,
    activePage,
    activePageGroupBlocks,
    activePageId,
    activePageWidgetIds,
    addGroup,
    addItem,
    addSubgroup,
    allItemIds,
    allSubgroupIds,
    appTagline,
    appTitle,
    applyConfigMutation,
    applyGrid,
    applyTheme,
    authProfileOptions,
    buildDefaultItem,
    buildItemFromEditorForm,
    clampNumber,
    clearDragState,
    clearItemFaviconFailures,
    clearSelectedNode,
    cloneConfig,
    closeIframeModal,
    closeItemEditor,
    closeLanHostModal,
    config,
    configError,
    copyUrl,
    createBrandIcon,
    defaultItemEditorForm,
    dragState,
    editGroup,
    editItem,
    editMode,
    editSubgroup,
    ensureAbsoluteUrl,
    ensurePageGroupsReference,
    expandedGroups,
    faviconOriginFromUrl,
    filteredBlockGroups,
    filteredTreeGroups,
    findGroup,
    findSubgroup,
    formatLanDuration,
    formatLanHttpStatus,
    formatLanMoment,
    fromToken,
    groupById,
    groupOnlineItems,
    groupTotalItems,
    healthClass,
    healthLabel,
    healthPollTimer,
    healthState,
    healthStates,
    iframeModal,
    indicatorPreviewEntries,
    initHeroParticles,
    initParticles,
    initSidebarParticles,
    initWidgetPolling,
    isActionBusy,
    isDirectGroupNode,
    isGroupExpanded,
    isGroupSelected,
    isIconCardView,
    isInlineGroupLayout,
    isItemSelected,
    isLanPage,
    isLargeIndicator,
    isSidebarIconActive,
    isSidebarIconOnly,
    isSubgroupSelected,
    isWidgetBlock,
    itemEditor,
    itemFaviconFailures,
    itemFaviconKey,
    itemFaviconSrc,
    lanCidrsLabel,
    lanHostModal,
    lanHosts,
    lanPortsLabel,
    lanScanActionBusy,
    lanScanError,
    lanScanLoading,
    lanScanPollTimer,
    lanScanRefreshInFlight,
    lanScanState,
    loadConfig,
    loadingConfig,
    makeUniqueId,
    markItemFaviconFailed,
    moveGroup,
    moveItemBefore,
    moveItemToSubgroupEnd,
    moveSubgroup,
    normalizeEndpoint,
    normalizeIconToken,
    normalizeId,
    normalizeLayoutBlocks,
    normalizeStringList,
    onGroupDragOver,
    onGroupDragStart,
    onGroupDrop,
    onItemCardClick,
    onItemDragOver,
    onItemDragStart,
    onItemDrop,
    onSubgroupDragOver,
    onSubgroupDragStart,
    onSubgroupDrop,
    openCreateItemEditor,
    openEditItemEditor,
    openIframeItem,
    openIndicatorView,
    openItem,
    openLanHostModal,
    openLinkItem,
    pageHealthSummary,
    pages,
    persistConfig,
    pickSemanticIcon,
    refreshHealth,
    refreshLanScanState,
    refreshWidget,
    removeGroup,
    removeItem,
    removeSubgroup,
    resetWidgetPolling,
    resolveBlockGroups,
    resolveExpression,
    resolveGroupIcon,
    resolveItemIcon,
    resolvePageIcon,
    resolveSubgroupIcon,
    resolveWidgetIcon,
    resolveWidgets,
    runLanScanNow,
    runWidgetAction,
    saveError,
    saveStatus,
    saveStatusLabel,
    saveStatusTimer,
    selectItemNode,
    selectSidebarIconNode,
    selectSidebarIndicator,
    selectSubgroupNode,
    selectedNode,
    serviceCardView,
    sidebarIconNodeTitle,
    sidebarIconNodes,
    sidebarIndicatorSummary,
    sidebarIndicators,
    sidebarView,
    startHealthPolling,
    startLanScanPolling,
    statCardSubtitle,
    statCardTrend,
    statCardValue,
    statListEntries,
    statsExpanded,
    stopHealthPolling,
    stopLanScanPolling,
    subgroupById,
    submitItemEditor,
    syncTreeGroupsState,
    tableRows,
    toggleEditMode,
    toggleGroupNode,
    toggleServiceCardView,
    toggleSidebarView,
    treeFilter,
    treeGroups,
    visibleTreeItemIds,
    widgetById,
    widgetIntervals,
    widgetState,
    widgetStates,
    widgets,
  }

  return dashboardStore
}

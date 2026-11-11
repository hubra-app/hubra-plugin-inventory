import { colorText } from '@hubra/plugin-sdk'
import { useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Chip, TextInput, Select, Badge, Paper, Text, Group } from '@mantine/core'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useT } from '@hubra/plugin-sdk'
import { IconPlus, IconSearch } from '@tabler/icons-react'
import { useToast, useAuth, useNav } from '@hubra/plugin-sdk'
import {
  PageHead,
  usePagination,
  ConfirmModal,
  ErrorBanner,
  DataTable,
  ActionButtons,
  Seg,
  CardGrid,
  CardItem,
  LoadingSpinner,
  EmptyState,
} from '@hubra/plugin-sdk'
import type { InventoryItem, InventoryCategory, InventoryStatus } from './types'
import {
  listInventory,
  createInventoryItem,
  updateInventoryItem,
  deleteInventoryItem,
  type InventoryItemCreate,
} from './api'
import { QK } from './api'
import {
  CATEGORIES,
  categoryLabel,
  useCategories,
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  STATUSES,
  STATUS_CONFIG,
} from './constants'
import { ItemFormModal } from './ItemFormModal'
import { useItemAccess } from './access'

export function InventoryScreen() {
  const { t } = useT()
  const { notify } = useToast()
  const { currentUser, hasPermission } = useAuth()
  const queryClient = useQueryClient()
  // Without the club-wide right, members may still add their own items.
  const canCreateAny = hasPermission('inventory.items.create')
  const canCreate = canCreateAny || hasPermission('inventory.items.create_own')
  const accessTo = useItemAccess()
  const {
    data: items = [],
    isLoading: loading,
    error: fetchError,
    refetch,
  } = useQuery({
    queryKey: QK,
    queryFn: () => listInventory(),
  })
  const categories = useCategories(items)
  // ?type=Key opens the list on one type (the Keys add-on links here).
  const [params] = useSearchParams()
  const [catFilter, setCatFilter] = useState<InventoryCategory | 'All'>(() => {
    const type = params.get('type') as InventoryCategory | null
    return type && CATEGORIES.includes(type) ? type : 'All'
  })
  const [statusFilter, setStatusFilter] = useState<InventoryStatus | 'All'>(
    'All',
  )
  // Who it belongs to: the club, or a member who lends it to the club.
  const [ownerFilter, setOwnerFilter] = useState<'all' | 'shared' | 'private'>('all')
  const [search, setSearch] = useState('')
  // "types": one section per type, like a shelf per kind of thing.
  const [view, setView] = useState<'table' | 'cards' | 'types'>(() =>
    params.get('type') === 'Key' ? 'table' : 'cards',
  )
  const keysOnly = catFilter === 'Key'
  // ?low=1: only counted items at or below their reorder level.
  const [lowOnly, setLowOnly] = useState(() => params.get('low') === '1')
  const anyLow = items.some((i) => i.lowStock)
  const anyCounted = items.some((i) => i.stock !== null)

  const [deleteTarget, setDeleteTarget] = useState<InventoryItem | null>(null)
  const { go } = useNav()
  const openItem = (item: InventoryItem) => go(`/app/inventory/${item.id}`)

  // Form state
  // 'new' opens the form for a new item, an item opens it for that item.
  // ?lend=1 (linked from elsewhere) opens the form for something the
  // member lends to the club.
  const [formTarget, setFormTarget] = useState<InventoryItem | 'new' | null>(() =>
    canCreate && params.get('lend') ? 'new' : null,
  )

  const filtered = items.filter((item) => {
    if (catFilter !== 'All' && item.category !== catFilter) return false
    if (statusFilter !== 'All' && item.status !== statusFilter) return false
    if (ownerFilter !== 'all' && item.visibility !== ownerFilter) return false
    if (lowOnly && !item.lowStock) return false
    if (search && !item.name.toLowerCase().includes(search.toLowerCase()))
      return false
    return true
  })

  const pg = usePagination(filtered, 12)
  // Who has it, for items an add-on hands out (keys); always in the key view.
  const showHolder = keysOnly || filtered.some((i) => i.holderName)
  const viewOptions = [
    { value: 'table', label: '\u2261 ' + t('members.tableView') },
    { value: 'cards', label: '\u229e ' + t('members.cardsView') },
    { value: 'types', label: '\u2637 ' + t('inventory.byType', 'Nach Typ') },
  ]
  // The "types" view shows every match, one section per type.
  const groups = categories
    .map((c) => ({ type: c, items: filtered.filter((i) => i.category === c) }))
    .filter((g) => g.items.length > 0)

  const saveItem = async (target: InventoryItem | null, input: InventoryItemCreate) => {
    try {
      if (target) {
        await updateInventoryItem(target.id, input)
      } else {
        await createInventoryItem(input)
      }
      queryClient.invalidateQueries({ queryKey: QK })
      setFormTarget(null)
      notify(
        'success',
        target ? t('inventory.item.updated', 'Gegenstand gespeichert') : t('inventory.item.added', 'Gegenstand hinzugefügt'),
        target
          ? t('inventory.item.updatedMsg', '{{name}} wurde gespeichert.', { name: input.name })
          : t('inventory.item.addedMsg', '{{name}} wurde zum Inventar hinzugefügt.', { name: input.name }),
      )
    } catch (err: unknown) {
      notify(
        'error',
        target ? t('common.updateFailed', 'Speichern fehlgeschlagen') : t('common.createFailed', 'Erstellen fehlgeschlagen'),
        err instanceof Error ? err.message : t('common.unknownError', 'Unbekannter Fehler'),
      )
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteInventoryItem(deleteTarget.id)
      queryClient.invalidateQueries({ queryKey: QK })
      notify(
        'info',
        t('inventory.item.removed', 'Gegenstand gelöscht'),
        t('inventory.item.removedMsg', '{{name}} wurde gelöscht.', {
          name: deleteTarget.name,
        }),
      )
    } catch (err: unknown) {
      notify(
        'error',
        t('common.deleteFailed', 'Löschen fehlgeschlagen'),
        err instanceof Error
          ? err.message
          : t('common.unknownError', 'Unbekannter Fehler'),
      )
    } finally {
      setDeleteTarget(null)
    }
  }

  const currentUserId = currentUser ? Number(currentUser.id) : null

  const ownerSelect = (
    <Select
      size="sm"
      aria-label={t('inventory.visibility', 'Eigentum')}
      data={[
        { value: 'all', label: t('inventory.allOwners', 'Verein und ausgeliehen') },
        { value: 'shared', label: t('inventory.clubOwned', 'Gehört dem Verein') },
        { value: 'private', label: t('inventory.lentByMembers', 'Von Mitgliedern ausgeliehen') },
      ]}
      value={ownerFilter}
      onChange={(v) => setOwnerFilter((v ?? 'all') as 'all' | 'shared' | 'private')}
      style={{ width: 260 }}
    />
  )
  // "Lent by Anna" for a member's own thing, otherwise the owner's name.
  const ownerLabel = (item: InventoryItem) =>
    item.visibility === 'private' && item.ownerName
      ? t('inventory.lentBy', 'Ausgeliehen von {{name}}', { name: item.ownerName })
      : (item.ownerName ?? t('inventory.noOwner', 'Ohne Eigentümer/in'))

  // "12 Flaschen", red when it's time to reorder.
  const stockBadge = (item: InventoryItem): ReactNode =>
    item.stock === null ? null : (
      <Badge
        variant="light"
        size="sm"
        color={item.lowStock ? 'red' : 'gray'}
        title={item.lowStock ? t('inventory.stock.low', 'Knapp') : undefined}
      >
        {[item.stock, item.unit].filter((x) => x !== '').join(' ')}
        {item.lowStock ? ` · ${t('inventory.stock.low', 'Knapp')}` : ''}
      </Badge>
    )

  const renderCard = (item: InventoryItem): ReactNode => {
    const sc = STATUS_CONFIG[item.status]
    const cc = CATEGORY_COLORS[item.category]
    return (
      <CardItem
        key={item.id}
        colorBar={cc}
        icon={
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: `color-mix(in srgb, ${cc} 13%, transparent)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: colorText(cc),
            }}
          >
            {CATEGORY_ICONS[item.category]}
          </div>
        }
        title={item.name}
        subtitle={
          item.category === 'Key'
            ? item.holderName
              ? t('inventory.heldBy', 'Bei {{name}}', { name: item.holderName })
              : item.serialNumber || t('inventory.notHandedOut', 'Nicht ausgegeben')
            : ownerLabel(item)
        }
        onClick={() => openItem(item)}
        footer={
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Badge
              variant="light"
              size="sm"
              style={{
                borderColor: `color-mix(in srgb, ${sc.color} 27%, transparent)`,
                color: sc.color,
                background: `color-mix(in srgb, ${sc.color} 7%, transparent)`,
              }}
            >
              {t(`inventory.status_${item.status}`, sc.label)}
            </Badge>
            {stockBadge(item)}
            <div onClick={(e) => e.stopPropagation()}>
              <ActionButtons
                onEdit={
                  accessTo(item).canEdit
                    ? () => setFormTarget(item)
                    : undefined
                }
                onDelete={
                  accessTo(item).canDelete
                    ? () => setDeleteTarget(item)
                    : undefined
                }
              />
            </div>
          </div>
        }
      >
        {item.description && (
          <Text
            size="sm"
            c="dimmed"
            style={{
              marginBottom: 8,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {item.description}
          </Text>
        )}
      </CardItem>
    )
  }

  return (
    <div>
      <PageHead
        title={t('inventory.title', 'Inventar')}
        desc={t('inventory.desc', 'Werkzeuge, Geräte und Material im Blick.')}
        actions={
          canCreate && (
            <Button variant="filled" onClick={() => setFormTarget('new')}>
              <IconPlus size={16} />
              {canCreateAny
                ? t('inventory.addItem', 'Gegenstand hinzufügen')
                : t('inventory.lendToClub', 'Dem Verein etwas ausleihen')}
            </Button>
          )
        }
      />

      {fetchError ? (
        <ErrorBanner
          message={
            fetchError instanceof Error
              ? fetchError.message
              : t(
                  'inventory.failedToLoadInventory',
                  'Inventar konnte nicht geladen werden',
                )
          }
          onRetry={() => refetch()}
        />
      ) : view !== 'types' ? (
        <DataTable
          // Cards and table share the search, the Filter panel and paging.
          renderCard={view === 'cards' ? renderCard : undefined}
          cardsOnly={view === 'cards'}
          breakpoint="wide"
          columns={[
            {
              key: 'name',
              header: t('common.name', 'Name'),
              render: (item) => (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <span
                    className="dot"
                    style={{ background: CATEGORY_COLORS[item.category] }}
                  />
                  <span style={{ color: colorText(CATEGORY_COLORS[item.category]) }}>
                    {CATEGORY_ICONS[item.category]}
                  </span>
                  <span style={{ fontWeight: 600, color: 'var(--hb-text)' }}>
                    {item.name}
                  </span>
                </div>
              ),
            },
            ...(keysOnly
              ? [
                  {
                    key: 'number',
                    header: t('inventory.number', 'Nummer'),
                    width: 110,
                    render: (item: InventoryItem) => (
                      <span className="num">{item.serialNumber || '—'}</span>
                    ),
                  },
                ]
              : []),
            ...(keysOnly
              ? []
              : [
                {
                  key: 'category',
                  header: t('inventory.category', 'Kategorie'),
                  width: 120,
                  render: (item: InventoryItem) => (
                    <Badge
                      variant="light"
                      style={{
                        fontSize: 'var(--mantine-font-size-xs)',
                        borderColor: `color-mix(in srgb, ${CATEGORY_COLORS[item.category]} 27%, transparent)`,
                        color: colorText(CATEGORY_COLORS[item.category]),
                        background: `color-mix(in srgb, ${CATEGORY_COLORS[item.category]} 7%, transparent)`,
                      }}
                    >
                      {categoryLabel(t, item.category)}
                    </Badge>
                  ),
                },
                ]),
            {
              key: 'status',
              header: t('common.status', 'Status'),
              width: 130,
              render: (item) => {
                const sc = STATUS_CONFIG[item.status]
                return (
                  <Badge
                    variant="light"
                    style={{
                      fontSize: 'var(--mantine-font-size-xs)',
                      borderColor: `color-mix(in srgb, ${sc.color} 27%, transparent)`,
                      color: sc.color,
                      background: `color-mix(in srgb, ${sc.color} 7%, transparent)`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                  >
                    {sc.icon}
                    {t(`inventory.status_${item.status}`, sc.label)}
                  </Badge>
                )
              },
            },
            ...(anyCounted
              ? [
                  {
                    key: 'stock',
                    header: t('inventory.stock.label', 'Bestand'),
                    width: 130,
                    render: (item: InventoryItem) => stockBadge(item) ?? '—',
                  },
                ]
              : []),
            ...(showHolder
              ? [
                  {
                    key: 'holder',
                    header: t('inventory.holder', 'Bei'),
                    render: (item: InventoryItem) => (
                      <span
                        style={{
                          color: item.holderName ? 'var(--hb-text)' : 'var(--hb-text-3)',
                          fontSize: 'var(--mantine-font-size-sm)',
                        }}
                      >
                        {item.holderName ?? '—'}
                      </span>
                    ),
                  },
                ]
              : []),
            ...(keysOnly
              ? []
              : [
                {
                  key: 'owner',
                  header: t('inventory.owner', 'Eigentümer/in'),
                  render: (item: InventoryItem) => (
                    <span
                      style={{
                        color: item.ownerName ? 'var(--hb-text)' : 'var(--hb-text-3)',
                        fontSize: 'var(--mantine-font-size-sm)',
                      }}
                    >
                      {ownerLabel(item)}
                    </span>
                  ),
                },
                ]),
            {
              key: 'actions',
              header: '',
              render: (item) => (
                <div onClick={(e) => e.stopPropagation()}>
                  <ActionButtons
                    onEdit={accessTo(item).canEdit ? () => setFormTarget(item) : undefined}
                    onDelete={
                      accessTo(item).canDelete ? () => setDeleteTarget(item) : undefined
                    }
                  />
                </div>
              ),
            },
          ]}
          data={pg.paged}
          loading={loading}
          emptyMessage={t('inventory.noItemsFound', 'Keine Gegenstände gefunden')}
          onRowClick={openItem}
          searchValue={search}
          onSearchChange={setSearch}
          searchPlaceholder={t('inventory.searchItems', 'Gegenstände suchen …')}
          filterGroups={[
            {
              key: 'category',
              label: t('inventory.category', 'Kategorie'),
              value: catFilter,
              defaultValue: 'All',
              options: [
                { value: 'All', label: t('inventory.allCategories', 'Alle Kategorien') },
                ...categories.map((c) => ({
                  value: c,
                  text: categoryLabel(t, c),
                  label: (
                    <>
                      <span className="dot" style={{ background: CATEGORY_COLORS[c] }} />
                      {categoryLabel(t, c)}
                    </>
                  ),
                })),
              ],
              onChange: (v) => setCatFilter(v as typeof catFilter),
            },
            {
              key: 'status',
              label: t('common.status', 'Status'),
              value: statusFilter,
              defaultValue: 'All',
              options: [
                { value: 'All', label: t('inventory.allStatuses', 'Alle Status') },
                ...STATUSES.map((st) => ({
                  value: st,
                  label: t(`inventory.status_${st}`, STATUS_CONFIG[st].label),
                })),
              ],
              onChange: (v) => setStatusFilter(v as InventoryStatus | 'All'),
            },
            {
              key: 'owner',
              label: t('inventory.visibility', 'Eigentum'),
              value: ownerFilter,
              defaultValue: 'all',
              options: [
                { value: 'all', label: t('inventory.allOwners', 'Verein und ausgeliehen') },
                { value: 'shared', label: t('inventory.clubOwned', 'Gehört dem Verein') },
                { value: 'private', label: t('inventory.lentByMembers', 'Von Mitgliedern ausgeliehen') },
              ],
              onChange: (v) => setOwnerFilter(v as 'all' | 'shared' | 'private'),
            },
            {
              key: 'stock',
              label: t('inventory.stock.label', 'Bestand'),
              value: lowOnly ? 'low' : 'all',
              defaultValue: 'all',
              hidden: !(anyLow || lowOnly),
              options: [
                { value: 'all', label: t('common.all', 'Alle') },
                { value: 'low', label: t('inventory.stock.lowFilter', 'Knapp') },
              ],
              onChange: (v) => setLowOnly(v === 'low'),
            },
          ]}
          toolbar={<Seg options={viewOptions} value={view} onChange={(v) => setView(v as typeof view)} />}
          page={pg.page}
          perPage={pg.perPage}
          total={pg.total}
          totalPages={pg.totalPages}
          onPageChange={pg.goPage}
          onPerPageChange={pg.setPerPage}
          getRowKey={(item) => item.id}
        />
      ) : (
        <Paper withBorder>
          <div
            style={{
              padding: '14px 16px',
              borderBottom: '1px solid var(--hb-border)',
              display: 'flex',
              gap: 10,
              flexWrap: 'wrap',
              alignItems: 'center',
            }}
          >
            <TextInput
              style={{ flex: '1 1 220px' }}
              leftSection={<IconSearch size={16} />}
              size="sm"
              placeholder={t('inventory.searchItems', 'Gegenstände suchen …')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {(anyLow || lowOnly) && (
              <Chip checked={lowOnly} onChange={setLowOnly} variant="outline">
                {t('inventory.stock.lowFilter', 'Knapp')}
              </Chip>
            )}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Select
                size="sm"
                aria-label={t('common.status', 'Status')}
                data={[
                  {
                    value: 'All',
                    label: t('inventory.allStatuses', 'Alle Status'),
                  },
                  ...STATUSES.map((s) => ({
                    value: s,
                    label: t(`inventory.status_${s}`, STATUS_CONFIG[s].label),
                  })),
                ]}
                value={statusFilter}
                onChange={(v) =>
                  setStatusFilter((v ?? 'All') as InventoryStatus | 'All')
                }
                style={{ width: 140 }}
              />
              {ownerSelect}
              <Seg options={viewOptions} value={view} onChange={(v) => setView(v as typeof view)} />
            </div>
          </div>
          {loading ? (
            <LoadingSpinner compact message={t('common.loading', 'Wird geladen …')} />
          ) : filtered.length === 0 ? (
            <EmptyState
              title={t('inventory.noItemsFound', 'Keine Gegenstände gefunden')}
            />
          ) : (
            groups.map((g) => (
              <section key={g.type} style={{ padding: 16, borderTop: '1px solid var(--hb-border)' }}>
                <Group gap={8} mb={12}>
                  <span style={{ color: colorText(CATEGORY_COLORS[g.type]) }}>
                    {CATEGORY_ICONS[g.type]}
                  </span>
                  <Text fw={700}>{categoryLabel(t, g.type)}</Text>
                  <Text fz="sm" className="num" style={{ color: 'var(--hb-text-3)' }}>
                    {g.items.length}
                  </Text>
                </Group>
                <CardGrid>{g.items.map(renderCard)}</CardGrid>
              </section>
            ))
          )}
        </Paper>
      )}

      <ItemFormModal
        key={formTarget === 'new' ? 'new' : (formTarget?.id ?? 'closed')}
        open={formTarget !== null}
        item={formTarget === 'new' ? null : formTarget}
        canHandOn={
          formTarget === 'new' ? canCreateAny : !!formTarget && accessTo(formTarget).canHandOn
        }
        canGiveAway={
          formTarget === 'new' ? canCreateAny : !!formTarget && accessTo(formTarget).canGiveAway
        }
        ownerIfFixed={currentUserId ?? undefined}
        onClose={() => setFormTarget(null)}
        onSubmit={(input) => saveItem(formTarget === 'new' ? null : formTarget, input)}
      />
      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title={t('inventory.deleteItemTitle', '«{{name}}» löschen?', {
          name: deleteTarget?.name ?? '',
        })}
        body={t(
          'inventory.deleteItemBody',
          'Der Gegenstand und alle Einweisungen dazu werden endgültig gelöscht.',
        )}
        onConfirm={confirmDelete}
      />
    </div>
  )
}

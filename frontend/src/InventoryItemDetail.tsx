import { useMemo, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Group,
  NumberInput,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  IconArrowLeft,
  IconCircleCheck,
  IconExternalLink,
  IconHistory,
  IconInfoCircle,
  IconLink,
  IconPackage,
  IconStack2,
  IconPencil,
  IconTrash,
  IconUserCheck,
  IconX,
} from '@tabler/icons-react'
import {
  ConfirmModal,
  LoadingSpinner,
  MemberAddSearch,
  PanelMemberRow,
  PanelSection,
  PluginSlot,
  colorText,
  useAuth,
  useMemberSearch,
  useNav,
  useT,
  useToast,
} from '@hubra/plugin-sdk'
import {
  QK,
  getItemHistory,
  addInstruction,
  addSelfInstruction,
  adjustStock,
  deleteInventoryItem,
  listInventory,
  removeInstruction,
  updateInventoryItem,
  type InventoryItemCreate,
} from './api'
import type { InventoryItem } from './types'
import { CATEGORY_COLORS, CATEGORY_ICONS, STATUS_CONFIG, categoryLabel } from './constants'
import { ItemFormModal } from './ItemFormModal'
import { useItemAccess } from './access'

/* One item as its own page, like a member's page in Hubra: a back link, a
 * header card with the item, its badges, actions and key figures, then a
 * card of facts beside the inductions. It uses Hubra's detail page classes
 * (detail-grid, member-facts, member-rows) so it looks like the core pages. */
export function InventoryItemDetailScreen() {
  const { t } = useT()
  const { id } = useParams<{ id: string }>()
  const { go } = useNav()
  const { notify } = useToast()
  const { currentUser } = useAuth()
  const queryClient = useQueryClient()
  const accessTo = useItemAccess()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [addSearch, setAddSearch] = useState('')

  const { data: items, isLoading } = useQuery({ queryKey: QK, queryFn: () => listInventory() })
  const item = items?.find((i) => i.id === id)
  const { data: searchData } = useMemberSearch(addSearch, { enabled: addSearch.trim().length >= 2 })
  const addResults = useMemo(() => {
    if (!item || addSearch.trim().length < 2 || !searchData) return []
    const instructed = new Set(item.instructedMemberIds.map(String))
    return searchData.members.filter((m) => !instructed.has(m.id)).slice(0, 6)
  }, [addSearch, searchData, item])

  const back = () => go('/app/inventory')
  const backLink = (
    <Button
      size="sm"
      variant="subtle"
      px={6}
      leftSection={<IconArrowLeft size={16} />}
      onClick={back}
      style={{ marginBottom: 12, marginLeft: -6 }}
      data-testid="detail-back"
    >
      {t('inventory.backToInventory', 'Zurück zum Inventar')}
    </Button>
  )

  if (isLoading) return <LoadingSpinner message={t('common.loading', 'Wird geladen …')} />
  if (!item) {
    return (
      <div>
        {backLink}
        <Paper withBorder p={40} ta="center" data-testid="detail-not-found">
          <Text size="sm" c="dimmed">
            {t('inventory.itemNotFound', 'Diesen Gegenstand gibt es nicht (mehr).')}
          </Text>
        </Paper>
      </div>
    )
  }

  const access = accessTo(item)
  const me = currentUser ? Number(currentUser.id) : null
  const isSelfInstructed = me !== null && item.instructedMemberIds.includes(me)
  const sc = STATUS_CONFIG[item.status]
  const cc = CATEGORY_COLORS[item.category]
  const typeLabel = categoryLabel(t, item.category)
  const refresh = () => queryClient.invalidateQueries({ queryKey: QK })
  const fail = (err: unknown) =>
    notify('error', t('inventory.failed', 'Fehler'), err instanceof Error ? err.message : t('common.unknownError', 'Unbekannter Fehler'))

  const run = async (action: () => Promise<unknown>, done: () => void) => {
    setBusy(true)
    try {
      await action()
      await refresh()
      done()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }
  const instruct = (memberId: number, memberName: string) =>
    run(
      () => addInstruction(item.id, memberId),
      () => {
        setAddSearch('')
        notify(
          'success',
          t('inventory.instruction.recorded', 'Einweisung erfasst'),
          t('inventory.memberMarkedInstructed', '{{member}} ist als eingewiesen markiert.', { member: memberName }),
        )
      },
    )
  const unInstruct = (memberId: number) =>
    run(
      () => removeInstruction(item.id, memberId),
      () => notify('info', t('inventory.instruction.removed', 'Einweisung entfernt'), t('inventory.recordCleared', 'Eintrag entfernt.')),
    )
  const instructSelf = () =>
    run(
      () => addSelfInstruction(item.id),
      () =>
        notify(
          'success',
          t('inventory.recorded', 'Erfasst'),
          t('inventory.selfInstructedMsg', 'Du bist jetzt für diesen Gegenstand als eingewiesen markiert.'),
        ),
    )
  const save = async (input: InventoryItemCreate) => {
    try {
      await updateInventoryItem(item.id, input)
      await refresh()
      setEditOpen(false)
      notify(
        'success',
        t('inventory.item.updated', 'Gegenstand gespeichert'),
        t('inventory.item.updatedMsg', '{{name}} wurde gespeichert.', { name: input.name }),
      )
    } catch (err) {
      notify(
        'error',
        t('common.updateFailed', 'Speichern fehlgeschlagen'),
        err instanceof Error ? err.message : t('common.unknownError', 'Unbekannter Fehler'),
      )
    }
  }
  const destroy = async () => {
    try {
      await deleteInventoryItem(item.id)
      await refresh()
      notify('info', t('inventory.item.removed', 'Gegenstand gelöscht'), t('inventory.item.removedMsg', '{{name}} wurde gelöscht.', { name: item.name }))
      back()
    } catch (err) {
      notify(
        'error',
        t('common.deleteFailed', 'Löschen fehlgeschlagen'),
        err instanceof Error ? err.message : t('common.unknownError', 'Unbekannter Fehler'),
      )
    }
  }

  return (
    <div>
      {backLink}

      {/* ── The item at a glance ── */}
      <Paper withBorder p={{ base: 16, sm: 20 }} mb={16} data-testid="detail-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
          <div
            aria-hidden
            style={{
              width: 64,
              height: 64,
              borderRadius: 14,
              flexShrink: 0,
              background: `color-mix(in srgb, ${cc} 13%, transparent)`,
              color: colorText(cc),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {CATEGORY_ICONS[item.category]}
          </div>
          <div style={{ flex: '1 1 260px', minWidth: 0 }}>
            <Title order={1} fz={{ base: 24, sm: 30 }} style={{ overflowWrap: 'anywhere' }}>
              {item.name}
            </Title>
            <Group gap={8} mt={8}>
              <Badge variant="light" style={{ color: colorText(cc), background: `color-mix(in srgb, ${cc} 9%, transparent)` }}>
                {typeLabel}
              </Badge>
              <Badge
                variant="light"
                leftSection={sc.icon}
                style={{ color: sc.color, background: `color-mix(in srgb, ${sc.color} 9%, transparent)` }}
              >
                {t(`inventory.status_${item.status}`, sc.label)}
              </Badge>
              {item.instructionRequired && (
                <Badge variant="light" color="orange">
                  {t('inventory.instructionRequired', 'Einweisung nötig')}
                </Badge>
              )}
            </Group>
          </div>
          {(access.canEdit || access.canDelete) && (
            <div className="page-actions" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {access.canEdit && (
                <Button variant="default" leftSection={<IconPencil size={16} />} onClick={() => setEditOpen(true)}>
                  {t('common.edit', 'Bearbeiten')}
                </Button>
              )}
              {access.canDelete && (
                <Button
                  variant="default"
                  leftSection={<IconTrash size={16} />}
                  style={{ color: 'var(--mantine-color-red-text)' }}
                  onClick={() => setDeleteOpen(true)}
                >
                  {t('common.delete', 'Löschen')}
                </Button>
              )}
            </div>
          )}
        </div>
        <div className="member-facts" data-testid="detail-facts">
          <Fact label={t('inventory.owner', 'Eigentümer/in')}>{item.ownerName ?? '—'}</Fact>
          <Fact label={t('inventory.responsible', 'Verantwortlich')}>{item.responsibleName ?? '—'}</Fact>
          <Fact label={t('inventory.visibility', 'Eigentum')}>
            {item.visibility === 'private' ? t('inventory.private', 'Privatperson') : t('inventory.shared', 'Verein')}
          </Fact>
          {item.stock !== null && (
            <Fact label={t('inventory.stock.label', 'Bestand')}>
              <span className="num" style={item.lowStock ? { color: 'var(--mantine-color-red-text)' } : undefined}>
                {[item.stock, item.unit].filter((x) => x !== '').join(' ')}
              </span>
            </Fact>
          )}
          {item.cost && (
            <Fact label={t('inventory.cost', 'Kosten')}>
              <span className="num">CHF {item.cost}</span>
            </Fact>
          )}
        </div>
      </Paper>

      <div className="detail-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card icon={<IconPackage size={16} />} title={t('inventory.itemLabel', 'Gegenstand')}>
            {item.description && (
              <Text fz="sm" lh={1.6} px={16} py={12} style={{ whiteSpace: 'pre-line', borderBottom: '1px solid var(--hb-border)' }}>
                {item.description}
              </Text>
            )}
            <Row label={t('inventory.category', 'Kategorie')}>{typeLabel}</Row>
            <Row label={t('inventory.statusLabel', 'Status')}>{t(`inventory.status_${item.status}`, sc.label)}</Row>
            <Row label={t('inventory.owner', 'Eigentümer/in')}>{item.ownerName ?? '—'}</Row>
            <Row label={t('inventory.responsible', 'Verantwortlich')}>{item.responsibleName ?? '—'}</Row>
            {(item.holderName || item.category === 'Key') && (
              <Row label={t('inventory.holder', 'Bei')}>{item.holderName ?? '—'}</Row>
            )}
            {item.serialNumber && (
              <Row label={t('inventory.number', 'Nummer')} mono>
                {item.serialNumber}
              </Row>
            )}
            {item.location && <Row label={t('inventory.location', 'Standort')}>{item.location}</Row>}
            {item.cost && (
              <Row label={t('inventory.cost', 'Kosten')} mono>
                CHF {item.cost}
              </Row>
            )}
          </Card>
          {item.stock !== null && <StockCard item={item} canEdit={access.canEdit} />}
          <HistoryCard itemId={item.id} />
          {item.links.length > 0 && (
            <Card icon={<IconLink size={16} />} title={t('inventory.links', 'Links')}>
              <Stack gap={6} px={16} py={12}>
                {item.links.map((link, i) => (
                  <Anchor
                    key={link.url + i}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    fz="sm"
                    style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}
                  >
                    <IconExternalLink size={16} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {link.label || link.url}
                    </span>
                  </Anchor>
                ))}
              </Stack>
            </Card>
          )}
        </div>

        <Paper withBorder style={{ overflow: 'hidden' }}>
          {/* A key needs no induction: the Keys add-on hands it out below. */}
          {item.category === 'Key' ? null : item.instructionRequired ? (
            <PanelSection
              label={t('inventory.instructionRequired', 'Einweisung nötig')}
              right={
                <Text fz="xs" className="num" style={{ color: 'var(--hb-text-3)' }}>
                  {item.instructedMemberIds.length}
                </Text>
              }
            >
              {!isSelfInstructed && me !== null && (
                <Button mb="md" leftSection={<IconUserCheck size={16} />} onClick={instructSelf} disabled={busy}>
                  {t('inventory.markMyselfInstructed', 'Mich als eingewiesen markieren')}
                </Button>
              )}
              {isSelfInstructed && (
                <Group
                  gap={8}
                  mb="md"
                  px={12}
                  py={8}
                  style={{
                    fontSize: 'var(--mantine-font-size-sm)',
                    color: 'var(--mantine-color-green-text)',
                    background: 'var(--mantine-color-green-light)',
                    borderRadius: 8,
                  }}
                >
                  <IconCircleCheck size={16} />
                  {t('inventory.youAreInstructed', 'Du bist für diesen Gegenstand eingewiesen')}
                </Group>
              )}
              {access.canInstruct && (
                <MemberAddSearch
                  value={addSearch}
                  onChange={setAddSearch}
                  placeholder={t('inventory.searchMembersPlaceholder', 'Mitglieder suchen …')}
                  results={addResults}
                  onPick={(m) => instruct(Number(m.id), m.name)}
                  disabled={busy}
                />
              )}
              {item.instructedMemberIds.length === 0 ? (
                <Text fz="sm" ta="center" py="lg" style={{ color: 'var(--hb-text-3)' }}>
                  {t('inventory.noMembersInstructed', 'Noch niemand eingewiesen.')}
                </Text>
              ) : (
                <div style={{ marginTop: 8 }} data-testid="item-instructed">
                  {item.instructedMemberNames.map((name, i) => (
                    <PanelMemberRow
                      key={item.instructedMemberIds[i]}
                      name={name}
                      detail={t('inventory.instructed', 'Eingewiesen')}
                      right={
                        access.canInstruct && (
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => unInstruct(item.instructedMemberIds[i])}
                            disabled={busy}
                            aria-label={t('common.remove', 'Entfernen')}
                          >
                            <IconX size={16} />
                          </ActionIcon>
                        )
                      }
                    />
                  ))}
                </div>
              )}
            </PanelSection>
          ) : (
            <PanelSection>
              <Group gap={8} wrap="nowrap" style={{ fontSize: 'var(--mantine-font-size-sm)', color: 'var(--hb-text-3)' }}>
                <IconInfoCircle size={16} style={{ flexShrink: 0 }} />
                {t('inventory.noInstructionRequired', 'Für diesen Gegenstand ist keine Einweisung nötig.')}
              </Group>
            </PanelSection>
          )}
          {/* Other plugins add to the item here, e.g. the usage guide. */}
          <PluginSlot name="inventory.item" props={{ itemId: Number(item.id) }} />
        </Paper>
      </div>

      {editOpen && (
        <ItemFormModal
          key={item.id}
          open
          item={item}
          canHandOn={access.canHandOn}
          canGiveAway={access.canGiveAway}
          ownerIfFixed={me ?? undefined}
          onClose={() => setEditOpen(false)}
          onSubmit={save}
        />
      )}
      <ConfirmModal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title={t('inventory.deleteItemTitle', '«{{name}}» löschen?', { name: item.name })}
        body={t('inventory.deleteItemBody', 'Der Gegenstand und alle Einweisungen dazu werden endgültig gelöscht.')}
        onConfirm={destroy}
      />
    </div>
  )
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--mantine-font-size-xs)', color: 'var(--hb-text-2)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 'var(--mantine-font-size-md)', fontWeight: 600, color: 'var(--hb-text)' }}>{children}</div>
    </div>
  )
}

/** A counted item's stock: how many, when to reorder, restock or take some. */
function StockCard({ item, canEdit }: { item: InventoryItem; canEdit: boolean }) {
  const { t } = useT()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [amount, setAmount] = useState<number | string>(1)
  const [busy, setBusy] = useState(false)
  const change = async (sign: 1 | -1) => {
    const n = Number(amount)
    if (!Number.isInteger(n) || n <= 0) return
    setBusy(true)
    try {
      await adjustStock(
        item.id,
        sign * n,
        sign > 0 ? t('inventory.stock.restocked', 'Aufgefüllt') : t('inventory.stock.taken', 'Entnommen'),
      )
      await queryClient.invalidateQueries({ queryKey: QK })
    } catch (e) {
      notify('error', t('inventory.failed', 'Fehler'), e instanceof Error ? e.message : t('common.unknownError', 'Unbekannter Fehler'))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card icon={<IconStack2 size={16} />} title={t('inventory.stock.label', 'Bestand')}>
      <Row label={t('inventory.stock.label', 'Bestand')} mono>
        {[item.stock, item.unit].filter((x) => x !== '').join(' ')}
        {item.lowStock && (
          <Badge ml={8} size="sm" variant="light" color="red">
            {t('inventory.stock.low', 'Knapp')}
          </Badge>
        )}
      </Row>
      <Row label={t('inventory.stock.min', 'Nachbestellen ab')} mono>
        {item.minStock ?? '—'}
      </Row>
      {canEdit && (
        <Group gap={8} px={16} py={12} wrap="wrap">
          <NumberInput
            aria-label={t('inventory.stock.amount', 'Anzahl')}
            value={amount}
            onChange={setAmount}
            min={1}
            max={9999}
            allowDecimal={false}
            w={100}
            size="sm"
          />
          <Button size="sm" variant="light" loading={busy} onClick={() => change(1)}>
            {t('inventory.stock.restock', 'Auffüllen')}
          </Button>
          <Button size="sm" variant="default" loading={busy} onClick={() => change(-1)}>
            {t('inventory.stock.take', 'Entnehmen')}
          </Button>
        </Group>
      )}
    </Card>
  )
}

/** Checkouts, returns and what add-ons recorded (Keys: handovers). */
function HistoryCard({ itemId }: { itemId: string }) {
  const { t } = useT()
  const { data: history = [] } = useQuery({
    queryKey: [...QK, itemId, 'history'],
    queryFn: () => getItemHistory(itemId),
  })
  return (
    <Card icon={<IconHistory size={16} />} title={t('inventory.history.title', 'Verlauf')}>
      {history.length === 0 ? (
        <Text fz="sm" px={16} py={12} style={{ color: 'var(--hb-text-3)' }}>
          {t('inventory.history.empty', 'Noch nichts passiert.')}
        </Text>
      ) : (
        <div data-testid="item-history">
          {history.map((h) => (
            <div key={h.id} style={{ padding: '10px 16px', borderBottom: '1px solid var(--hb-border)' }}>
              <Text fz="sm">
                <strong>{t(`inventory.history.${h.action}`, h.action)}</strong>
                {h.memberName && <> · {h.memberName}</>}
              </Text>
              <Text fz="xs" style={{ color: 'var(--hb-text-3)' }}>
                {new Date(h.at).toLocaleString()}
                {h.byName && <> · {h.byName}</>}
                {h.note && <> · {h.note}</>}
              </Text>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function Card({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <Paper withBorder style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '12px 16px',
          borderBottom: '1px solid var(--hb-border)',
          fontSize: 'var(--mantine-font-size-sm)',
          fontWeight: 700,
        }}
      >
        <span style={{ color: 'var(--mantine-color-acc-7)', display: 'flex' }}>{icon}</span>
        {title}
      </div>
      <div className="member-rows">{children}</div>
    </Paper>
  )
}

function Row({ label, mono, children }: { label: string; mono?: boolean; children: ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 12,
        padding: '10px 16px',
        borderBottom: '1px solid var(--hb-border)',
      }}
    >
      <span style={{ fontSize: 'var(--mantine-font-size-xs)', color: 'var(--hb-text-2)', flexShrink: 0 }}>{label}</span>
      <span
        className={mono ? 'num' : ''}
        style={{ fontSize: 'var(--mantine-font-size-sm)', fontWeight: 500, textAlign: 'right', overflowWrap: 'anywhere' }}
      >
        {children}
      </span>
    </div>
  )
}

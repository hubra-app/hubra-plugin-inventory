import { useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from 'react'
import {
  Anchor,
  Button,
  Collapse,
  Paper,
  SegmentedControl,
  Select,
  Skeleton,
  Text,
  Textarea,
  TextInput,
  UnstyledButton,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  IconArrowLeft,
  IconCertificate,
  IconChevronDown,
  IconExternalLink,
  IconInfoCircle,
  IconListDetails,
  IconPencil,
} from '@tabler/icons-react'
import { MarkdownRenderer, PageHead, useT, useToast } from '@hubra/plugin-sdk'
import { getGuide, guideQualifications, saveGuide } from './guideApi'
import { headings, readingMinutes, type TocEntry } from './toc'

/** Puts the anchors from `toc` on the rendered h1–h3 headings, in order. */
function useHeadingIds(ref: RefObject<HTMLElement | null>, toc: TocEntry[]) {
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.querySelectorAll('h1, h2, h3').forEach((h, i) => {
      if (!toc[i]) return
      h.id = toc[i].id
      ;(h as HTMLElement).style.scrollMarginTop = '16px'
    })
  })
}

/** The heading the reader is at: the last one above the top third of the window. */
function useActiveHeading(toc: TocEntry[]) {
  const [active, setActive] = useState<string | null>(toc[0]?.id ?? null)
  useEffect(() => {
    if (!toc.length) return
    const onScroll = () => {
      let current = toc[0].id
      for (const entry of toc) {
        const h = document.getElementById(entry.id)
        if (h && h.getBoundingClientRect().top < window.innerHeight / 3) current = entry.id
      }
      setActive(current)
    }
    onScroll()
    // The app scrolls inside its main pane, not the window: listen to both.
    document.addEventListener('scroll', onScroll, { capture: true, passive: true })
    return () => document.removeEventListener('scroll', onScroll, { capture: true })
  }, [toc])
  return active
}

function TocList({
  toc,
  active,
  onPick,
}: {
  toc: TocEntry[]
  active: string | null
  onPick: (id: string) => void
}) {
  return (
    <nav>
      {toc.map((entry) => {
        const on = entry.id === active
        return (
          <a
            key={entry.id}
            href={`#${entry.id}`}
            onClick={(e) => {
              e.preventDefault()
              onPick(entry.id)
            }}
            aria-current={on ? 'location' : undefined}
            style={{
              display: 'block',
              padding: '5px 10px',
              paddingLeft: entry.level === 3 ? 24 : 10,
              borderLeft: `2px solid ${on ? 'var(--mantine-primary-color-filled)' : 'var(--hb-border)'}`,
              color: on ? 'var(--mantine-primary-color-text)' : 'var(--hb-text-2)',
              fontWeight: on ? 600 : 400,
              fontSize: 'var(--mantine-font-size-sm)',
              lineHeight: 1.4,
              textDecoration: 'none',
            }}
          >
            {entry.text}
          </a>
        )
      })}
    </nav>
  )
}

function SideLabel({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 'var(--mantine-font-size-xs)',
        fontWeight: 600,
        color: 'var(--hb-text-3)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  )
}

/**
 * An item's guide as a page of its own, /app/inventory/<id>/guide: the
 * guide at reading width, a table of contents beside it (above it on
 * phones), and a link back to the item. `?edit=1` opens the editor;
 * `#<heading>` links to a section.
 */
export function GuidePage() {
  const { t } = useT()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { hash } = useLocation()
  const [params, setParams] = useSearchParams()
  const itemId = Number(useParams().id)
  const wide = useMediaQuery('(min-width: 62em)', true)

  const { data: guide, isLoading, error } = useQuery({
    queryKey: ['inventory', 'guide', itemId],
    queryFn: () => getGuide(itemId),
    enabled: Number.isFinite(itemId),
  })
  // Club rights or the item's owner or responsible person (the API decides).
  const canWrite = !!guide?.canEdit

  const editing = canWrite && params.get('edit') === '1'
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [qualificationId, setQualificationId] = useState<string | null>(null)
  const kinds = useQuery({ queryKey: ['inventory', 'guide-qualifications'], queryFn: guideQualifications, enabled: editing })
  const [mode, setMode] = useState<'write' | 'preview'>('write')
  const [busy, setBusy] = useState(false)
  const [tocOpen, setTocOpen] = useState(false)

  useEffect(() => {
    if (editing && guide) {
      setText(guide.guide ?? '')
      setUrl(guide.guideUrl ?? '')
      setQualificationId(guide.qualification ? String(guide.qualification.id) : null)
      setMode('write')
    }
  }, [editing, guide])

  const content = guide?.guide ?? ''
  const toc = useMemo(() => headings(content), [content])
  const articleRef = useRef<HTMLDivElement>(null)
  // The same element on every render, so the headings are not remounted
  // (and lose their ids) when the active heading changes.
  const rendered = useMemo(() => <MarkdownRenderer content={content} />, [content])
  useHeadingIds(articleRef, toc)
  const active = useActiveHeading(editing ? [] : toc)

  const jump = (id: string, smooth = true) => {
    const el = document.getElementById(id)
    if (!el) return
    el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' })
    window.history.replaceState(window.history.state, '', `#${id}`)
    setTocOpen(false)
  }

  // A link to a section (#vor-dem-einschalten) scrolls there once the guide is in.
  useEffect(() => {
    if (!hash || !toc.length || editing) return
    const id = decodeURIComponent(hash.slice(1))
    const timer = window.setTimeout(() => jump(id, false), 50)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hash, toc, editing])

  const itemPath = `/app/inventory/${itemId}`
  const setEditing = (on: boolean) => {
    const next = new URLSearchParams(params)
    if (on) next.set('edit', '1')
    else next.delete('edit')
    setParams(next, { replace: true })
  }

  const save = async () => {
    setBusy(true)
    try {
      await saveGuide(itemId, {
        guide: text.trim() ? text : null,
        guideUrl: url.trim() || null,
        // Without Qualifications the choice isn't shown: keep what is stored.
        qualificationId: kinds.data?.length ? (qualificationId ? Number(qualificationId) : null) : undefined,
      })
      await queryClient.invalidateQueries({ queryKey: ['inventory', 'guide', itemId] })
      setEditing(false)
      notify('success', t('inventory.guide.saved', 'Guide saved'))
    } catch (err: unknown) {
      notify(
        'error',
        t('inventory.failed', 'Fehler'),
        err instanceof Error ? err.message : t('common.unknownError'),
      )
    } finally {
      setBusy(false)
    }
  }

  const back = (
    <Button
      component={Link}
      to={itemPath}
      variant="subtle"
      size="compact-sm"
      leftSection={<IconArrowLeft size={16} />}
      style={{ marginLeft: -8 }}
    >
      {guide?.itemName ?? t('inventory.guide.backToItem', 'Back to the item')}
    </Button>
  )

  if (isLoading) {
    return (
      <div>
        <Skeleton height={20} width={160} mb={16} />
        <Skeleton height={36} width={320} mb={24} />
        <Skeleton height={280} />
      </div>
    )
  }

  if (error || !guide) {
    return (
      <div>
        <PageHead
          title={t('inventory.guide.notFound', 'Guide not found')}
          desc={t('inventory.guide.notFoundDesc', 'The item may have been deleted.')}
          back={
            <Button
              component={Link}
              to="/app/inventory"
              variant="subtle"
              size="compact-sm"
              leftSection={<IconArrowLeft size={16} />}
              style={{ marginLeft: -8 }}
            >
              {t('inventory.guide.backToInventory', 'Back to the inventory')}
            </Button>
          }
        />
      </div>
    )
  }

  const empty = !content && !guide.guideUrl
  const minutes = readingMinutes(content)
  const meta = [
    toc.length
      ? t('inventory.guide.sections', '{{count}} sections', { count: toc.length })
      : null,
    content ? t('inventory.guide.minutes', '{{count}} min read', { count: minutes }) : null,
  ]
    .filter(Boolean)
    .join(' · ')

  const manualButton = guide.guideUrl && (
    <Button
      component="a"
      href={guide.guideUrl}
      target="_blank"
      rel="noopener noreferrer"
      variant="default"
      leftSection={<IconExternalLink size={16} />}
    >
      {t('inventory.guide.openLink', 'Open manual')}
    </Button>
  )

  const head = (
    <PageHead
      back={back}
      eyebrow={t('inventory.guide.title', 'Guide')}
      title={guide.itemName}
      desc={!editing && meta ? meta : undefined}
      actions={
        editing ? null : (
          <>
            {content && manualButton}
            {canWrite && (
              <Button
                variant="default"
                leftSection={<IconPencil size={16} />}
                onClick={() => setEditing(true)}
              >
                {empty ? t('inventory.guide.add', 'Add guide') : t('common.edit', 'Edit')}
              </Button>
            )}
          </>
        )
      }
    />
  )

  if (editing) {
    return (
      <div>
        {head}
        <Paper withBorder p={{ base: 'md', sm: 'xl' }} style={{ maxWidth: 880 }}>
          <SegmentedControl
            value={mode}
            onChange={(v) => setMode(v as 'write' | 'preview')}
            data={[
              { value: 'write', label: t('inventory.guide.write', 'Write') },
              { value: 'preview', label: t('inventory.guide.preview', 'Preview') },
            ]}
            mb="md"
          />
          {mode === 'write' ? (
            <Textarea
              value={text}
              onChange={(e) => setText(e.currentTarget.value)}
              autosize
              minRows={14}
              maxRows={40}
              aria-label={t('inventory.guide.title', 'Guide')}
              placeholder={t(
                'inventory.guide.placeholder',
                'Steps, safety rules, what to check after use. Markdown works.',
              )}
              description={t(
                'inventory.guide.headingsHint',
                'Start a section with ## Heading: it gets its own entry in the table of contents and a link of its own.',
              )}
              inputWrapperOrder={['input', 'description']}
              styles={{ input: { fontFamily: 'var(--mantine-font-family-monospace)', fontSize: 'var(--mantine-font-size-sm)' } }}
            />
          ) : (
            <div
              style={{
                minHeight: 200,
                padding: 16,
                border: '1px solid var(--hb-border)',
                borderRadius: 'var(--mantine-radius-md)',
                lineHeight: 1.65,
              }}
            >
              {text.trim() ? (
                <MarkdownRenderer content={text} />
              ) : (
                <Text c="dimmed" fz="sm">
                  {t('inventory.guide.previewEmpty', 'Nothing to preview yet.')}
                </Text>
              )}
            </div>
          )}
          <TextInput
            mt="lg"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            label={t('inventory.guide.link', 'Link to manual or video')}
            placeholder="https://"
          />
          {(kinds.data?.length ?? 0) > 0 && (
          <Select
            mt="md"
            clearable
            value={qualificationId}
            onChange={setQualificationId}
            data={(kinds.data ?? []).map((k) => ({ value: String(k.id), label: k.name }))}
            label={t('inventory.guide.qualification.needed', 'Qualification it takes')}
            description={t('inventory.guide.qualification.neededHint', 'Shown on the guide, with whether the reader holds it.')}
            placeholder={t('inventory.guide.qualification.noneNeeded', 'None')}
          />
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 24 }}>
            <Button variant="subtle" onClick={() => setEditing(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={save} loading={busy}>
              {t('common.save')}
            </Button>
          </div>
        </Paper>
      </div>
    )
  }

  const instructionNote = guide.instructionRequired && (
    <div
      style={{
        display: 'flex',
        gap: 8,
        alignItems: 'flex-start',
        fontSize: 'var(--mantine-font-size-sm)',
        color: 'var(--hb-text-2)',
        lineHeight: 1.45,
      }}
    >
      <IconInfoCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
      <span>
        {t('inventory.guide.needsInstruction', 'This item needs an induction before first use.')}{' '}
        <Anchor component={Link} to={itemPath} fz="sm">
          {t('inventory.guide.seeItem', 'See who is inducted')}
        </Anchor>
      </span>
    </div>
  )

  const q = guide.qualification
  const qualificationNote = q && (
    <div
      style={{
        display: 'flex',
        gap: 8,
        alignItems: 'flex-start',
        fontSize: 'var(--mantine-font-size-sm)',
        color: q.mine === 'valid' ? 'var(--hb-text-2)' : 'var(--mantine-color-red-7)',
        lineHeight: 1.45,
      }}
    >
      <IconCertificate size={16} style={{ flexShrink: 0, marginTop: 2 }} />
      <span>
        {t('inventory.guide.qualification.takes', 'It takes: {{name}}.', { name: q.name })}{' '}
        {t(`inventory.guide.qualification.yours.${q.mine ?? 'none'}`)}
      </span>
    </div>
  )

  const article = (
    <Paper withBorder p={{ base: 'md', sm: 'xl' }} style={{ minWidth: 0 }}>
      {content ? (
        <div ref={articleRef} style={{ lineHeight: 1.7, maxWidth: 720 }}>
          {rendered}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '32px 8px' }}>
          <Text c="dimmed" fz="sm" mb={canWrite ? 'md' : 0}>
            {guide.guideUrl
              ? t('inventory.guide.onlyLink', 'This guide is a link to the manual.')
              : t('inventory.guide.none', 'There is no guide for this item yet.')}
          </Text>
          {guide.guideUrl && <div style={{ marginTop: 12 }}>{manualButton}</div>}
          {canWrite && !guide.guideUrl && (
            <Button variant="default" onClick={() => setEditing(true)}>
              {t('inventory.guide.add', 'Add guide')}
            </Button>
          )}
        </div>
      )}
    </Paper>
  )

  if (!wide) {
    return (
      <div>
        {head}
        {instructionNote && <div style={{ marginBottom: 16 }}>{instructionNote}</div>}
        {qualificationNote && <div style={{ marginBottom: 16 }}>{qualificationNote}</div>}
        {toc.length > 1 && (
          <Paper withBorder mb="md" style={{ overflow: 'hidden' }}>
            <UnstyledButton
              onClick={() => setTocOpen((o) => !o)}
              aria-expanded={tocOpen}
              style={{
                display: 'flex',
                width: '100%',
                alignItems: 'center',
                gap: 10,
                padding: '12px 16px',
                fontSize: 'var(--mantine-font-size-sm)',
                fontWeight: 600,
                color: 'var(--hb-text)',
              }}
            >
              <IconListDetails size={18} />
              <span style={{ flex: 1 }}>
                {t('inventory.guide.contents', 'Contents')}
                <span style={{ fontWeight: 400, color: 'var(--hb-text-3)' }}> · {toc.length}</span>
              </span>
              <IconChevronDown
                size={18}
                style={{ transform: tocOpen ? 'rotate(180deg)' : undefined, transition: 'transform 150ms' }}
              />
            </UnstyledButton>
            <Collapse expanded={tocOpen}>
              <div style={{ padding: '0 16px 14px' }}>
                <TocList toc={toc} active={active} onPick={jump} />
              </div>
            </Collapse>
          </Paper>
        )}
        {article}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100 }}>
      {head}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 260px',
          gap: 32,
          alignItems: 'start',
        }}
      >
        {article}
        <aside style={{ position: 'sticky', top: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {toc.length > 1 && (
            <div>
              <SideLabel>{t('inventory.guide.contents', 'Contents')}</SideLabel>
              <TocList toc={toc} active={active} onPick={jump} />
            </div>
          )}
          {instructionNote}
          {qualificationNote}
          <div>
            <Button
              variant="subtle"
              size="compact-sm"
              leftSection={<IconArrowLeft size={14} />}
              onClick={() => navigate(itemPath)}
              style={{ marginLeft: -8 }}
            >
              {t('inventory.guide.backToItem', 'Back to the item')}
            </Button>
          </div>
        </aside>
      </div>
    </div>
  )
}

import { Button, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { IconBook2, IconExternalLink, IconPlus } from '@tabler/icons-react'
import { useT } from '@hubra/plugin-sdk'
import { getGuide } from './guideApi'
import { firstParagraph, headings, readingMinutes } from './toc'

/**
 * Shown in an inventory item's detail panel: a short preview of the guide
 * and a button to its own page. The guide itself is read and edited there,
 * not in the panel.
 */
export function GuideSection({ itemId }: { itemId: number }) {
  const { t } = useT()
  const { data: guide } = useQuery({
    queryKey: ['inventory', 'guide', itemId],
    queryFn: () => getGuide(itemId),
  })

  const canWrite = !!guide?.canEdit
  const content = guide?.guide ?? ''
  const empty = !content && !guide?.guideUrl
  if (!guide || (empty && !canWrite)) return null

  const page = `/app/inventory/${itemId}/guide`
  const sections = headings(content).length
  const meta = [
    sections ? t('inventory.guide.sections', '{{count}} sections', { count: sections }) : null,
    content
      ? t('inventory.guide.minutes', '{{count}} min read', { count: readingMinutes(content) })
      : null,
  ]
    .filter(Boolean)
    .join(' · ')
  const preview = firstParagraph(content)

  return (
    <section style={{ padding: '16px 20px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          marginBottom: 10,
        }}
      >
        <div
          style={{
            fontSize: 'var(--mantine-font-size-xs)',
            fontWeight: 600,
            color: 'var(--hb-text-3)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          {t('inventory.guide.title', 'Guide')}
        </div>
        {canWrite && !empty && (
          <Button component={Link} to={`${page}?edit=1`} size="compact-xs" variant="subtle">
            {t('common.edit', 'Edit')}
          </Button>
        )}
      </div>
      {empty ? (
        <Button
          component={Link}
          to={`${page}?edit=1`}
          variant="default"
          fullWidth
          leftSection={<IconPlus size={16} />}
        >
          {t('inventory.guide.add', 'Add guide')}
        </Button>
      ) : (
        <div
          style={{
            border: '1px solid var(--hb-border)',
            borderRadius: 'var(--mantine-radius-md)',
            padding: 14,
            background: 'var(--hb-surface-2)',
          }}
        >
          {preview && (
            <Text
              fz="sm"
              lineClamp={3}
              style={{ color: 'var(--hb-text)', lineHeight: 1.55 }}
              mb={meta ? 6 : 12}
            >
              {preview}
            </Text>
          )}
          {meta && (
            <Text fz="xs" mb={12} style={{ color: 'var(--hb-text-3)' }}>
              {meta}
            </Text>
          )}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {content && (
              <Button component={Link} to={page} size="sm" leftSection={<IconBook2 size={16} />}>
                {t('inventory.guide.read', 'Read guide')}
              </Button>
            )}
            {guide.guideUrl && (
              <Button
                component="a"
                href={guide.guideUrl}
                target="_blank"
                rel="noopener noreferrer"
                size="sm"
                variant="default"
                leftSection={<IconExternalLink size={16} />}
              >
                {t('inventory.guide.openLink', 'Open manual')}
              </Button>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

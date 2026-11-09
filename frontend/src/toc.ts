/** A heading of a guide, for its table of contents. */
export interface TocEntry {
  /** 2 for `#`/`##`, 3 for `###`. */
  level: 2 | 3
  text: string
  /** The heading's anchor, unique within the guide. */
  id: string
}

/** A URL-safe anchor for a heading: "Vor dem Einschalten" → "vor-dem-einschalten". */
export function slugify(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/ä/g, 'ae')
      .replace(/ö/g, 'oe')
      .replace(/ü/g, 'ue')
      .replace(/ß/g, 'ss')
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'abschnitt'
  )
}

/** Strips inline Markdown (bold, links, code) from a heading's text. */
function plain(text: string): string {
  return text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*_`~]/g, '')
    .replace(/\s+#+\s*$/, '')
    .trim()
}

/**
 * The guide's `#`, `##` and `###` headings in order, skipping fenced code.
 * They line up one to one with the h1–h3 elements the Markdown renders to.
 */
export function headings(markdown: string): TocEntry[] {
  const out: TocEntry[] = []
  const seen = new Map<string, number>()
  let fence: string | null = null
  for (const line of markdown.split('\n')) {
    const f = line.match(/^\s{0,3}(```|~~~)/)
    if (f) {
      fence = fence === null ? f[1] : fence === f[1] ? null : fence
      continue
    }
    if (fence) continue
    const m = line.match(/^\s{0,3}(#{1,3})\s+(.+)$/)
    if (!m) continue
    const text = plain(m[2])
    if (!text) continue
    const base = slugify(text)
    const n = seen.get(base) ?? 0
    seen.set(base, n + 1)
    out.push({ level: m[1].length === 3 ? 3 : 2, text, id: n ? `${base}-${n + 1}` : base })
  }
  return out
}

/** About how many minutes the guide takes to read (200 words a minute). */
export function readingMinutes(markdown: string): number {
  const words = markdown.split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / 200))
}

/** The first paragraph of plain text, for a short preview. */
export function firstParagraph(markdown: string): string {
  for (const block of markdown.split(/\n\s*\n/)) {
    const b = block.trim()
    if (!b || /^(#|```|~~~|>|[-*+]\s|\d+\.\s|\|)/.test(b)) continue
    return plain(b.replace(/\n/g, ' '))
  }
  return ''
}

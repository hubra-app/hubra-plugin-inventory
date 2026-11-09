import { apiFetch } from '@hubra/plugin-sdk'

/** Whether the reader holds the qualification the item takes. */
export type QualificationState = 'valid' | 'soon' | 'expired'

export interface Guide {
  itemId: number
  itemName: string
  guide: string | null
  guideUrl: string | null
  instructionRequired: boolean
  /** The reader may change the guide (club right, or owner/responsible). */
  canEdit: boolean
  /** The qualification it takes (Qualifications plugin), and whether I hold it. */
  qualification: { id: number; name: string; mine: QualificationState | null } | null
}

export const getGuide = (itemId: number) => apiFetch<Guide>(`/inventory/${itemId}/guide`)

export const saveGuide = (
  itemId: number,
  input: { guide: string | null; guideUrl: string | null; qualificationId?: number | null },
) =>
  apiFetch<Guide>(`/inventory/${itemId}/guide`, {
    method: 'PUT',
    body: JSON.stringify({
      guide: input.guide,
      guide_url: input.guideUrl,
      ...(input.qualificationId !== undefined && { qualification_id: input.qualificationId }),
    }),
  })

/** The qualifications an item can take; empty without the Qualifications plugin. */
export const guideQualifications = () =>
  apiFetch<{ id: number; name: string }[]>('/inventory/guide-qualifications')

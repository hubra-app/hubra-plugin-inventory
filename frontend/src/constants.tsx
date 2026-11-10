import { categoryColors, useModules } from '@hubra/plugin-sdk'
import {
  IconTool,
  IconBox,
  IconStack2,
  IconCircleCheck,
  IconAlertCircle,
  IconClock,
  IconArchive,
  IconKey,
  IconBottle,
} from '@tabler/icons-react'
import type { InventoryCategory, InventoryStatus } from './types'

export const CATEGORIES: InventoryCategory[] = ['Tool', 'Item', 'Material', 'Consumable', 'Key']

type T = (key: string, fallback: string) => string

export function categoryLabel(t: T, c: InventoryCategory): string {
  switch (c) {
    case 'Tool':
      return t('inventory.tool', 'Werkzeug')
    case 'Item':
      return t('inventory.itemLabel', 'Gegenstand')
    case 'Key':
      return t('inventory.key', 'Schlüssel')
    case 'Consumable':
      return t('inventory.consumable', 'Verbrauchsmaterial')
    default:
      return t('inventory.material', 'Material')
  }
}

/**
 * The types to offer: "Key" while the Keys add-on is on (it hands keys out
 * and keeps their history) or some item already is a key.
 */
export function useCategories(items: { category: InventoryCategory }[] = []) {
  const { has } = useModules()
  const keys = has('inventory.keys') || items.some((i) => i.category === 'Key')
  return keys ? CATEGORIES : CATEGORIES.filter((c) => c !== 'Key')
}
export const STATUSES: InventoryStatus[] = [
  'available',
  'in_use',
  'maintenance',
  'broken',
  'archived',
]

export const CATEGORY_ICONS: Record<InventoryCategory, React.ReactNode> = {
  Tool: <IconTool size={16} />,
  Item: <IconBox size={16} />,
  Material: <IconStack2 size={16} />,
  Key: <IconKey size={16} />,
  Consumable: <IconBottle size={16} />,
}

export const CATEGORY_COLORS: Record<InventoryCategory, string> = {
  Tool: categoryColors.blue,
  Item: categoryColors.green,
  Material: categoryColors.orange,
  Key: categoryColors.yellow,
  Consumable: categoryColors.purple,
}

export const STATUS_CONFIG: Record<
  InventoryStatus,
  { label: string; color: string; icon: React.ReactNode }
> = {
  available: {
    label: 'Verfügbar',
    color: 'var(--mantine-color-green-text)',
    icon: <IconCircleCheck size={12} />,
  },
  in_use: {
    label: 'In Gebrauch',
    color: 'var(--mantine-color-acc-text)',
    icon: <IconClock size={12} />,
  },
  maintenance: {
    label: 'Wartung',
    color: 'var(--mantine-color-orange-text)',
    icon: <IconAlertCircle size={12} />,
  },
  broken: {
    label: 'Defekt',
    color: 'var(--mantine-color-red-text)',
    icon: <IconAlertCircle size={12} />,
  },
  archived: {
    label: 'Archiviert',
    color: 'var(--hb-text-3)',
    icon: <IconArchive size={12} />,
  },
  checked_out: {
    label: 'Ausgeliehen',
    color: 'var(--mantine-color-acc-text)',
    icon: <IconClock size={12} />,
  },
  pending: {
    label: 'Ausstehend',
    color: 'var(--mantine-color-orange-text)',
    icon: <IconAlertCircle size={12} />,
  },
  lost: {
    label: 'Verloren',
    color: 'var(--mantine-color-red-text)',
    icon: <IconAlertCircle size={12} />,
  },
  retired: {
    label: 'Ausgemustert',
    color: 'var(--hb-text-3)',
    icon: <IconArchive size={12} />,
  },
}

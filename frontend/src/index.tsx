import { categoryColors, colorText, registerPlugin } from '@hubra/plugin-sdk'
import { IconPackage } from '@tabler/icons-react'
import { listInventory } from './api'
import { InventoryScreen } from './Inventory'
import { InventoryItemDetailScreen } from './InventoryItemDetail'
import { GuidePage } from './GuidePage'
import translations from './translations.json'

registerPlugin({
  id: 'inventory',
  routes: [
    {
      path: 'inventory',
      module: 'inventory',
      perm: 'inventory.items.read',
      component: InventoryScreen,
    },
    {
      path: 'inventory/:id',
      module: 'inventory',
      perm: 'inventory.items.read',
      component: InventoryItemDetailScreen,
    },
    {
      path: 'inventory/:id/guide',
      module: 'inventory',
      perm: 'inventory.items.read',
      component: GuidePage,
    },
  ],
  search: [
    {
      id: 'items',
      module: 'inventory',
      perm: 'inventory.items.read',
      label: 'shell.searchKind.inventory',
      color: {
        bg: `color-mix(in srgb, ${categoryColors.purple} 12%, var(--hb-surface))`,
        color: colorText(categoryColors.purple),
      },
      load: async () =>
        (await listInventory()).map((item) => ({
          id: item.id,
          label: item.name,
          sub: item.category,
          keywords: item.description,
          path: `/app/inventory/${item.id}`,
        })),
    },
  ],
  icons: { package: IconPackage },
  translations,
})

export type InventoryCategory =
  | "Tool"
  | "Item"
  | "Material"
  | "Key"
  | "Consumable";
export type InventoryStatus =
  | "available"
  | "in_use"
  | "maintenance"
  | "broken"
  | "archived"
  | "checked_out"
  | "pending"
  | "lost"
  | "retired";
export type InventoryVisibility = "private" | "shared";

export interface InventoryLink {
  label: string;
  url: string;
}

export interface InventoryItem {
  id: string;
  name: string;
  category: InventoryCategory;
  description: string;
  ownerId: number | null;
  ownerName: string | null;
  responsibleId: number | null;
  responsibleName: string | null;
  /** Who has it now, when an add-on handed it out (Keys: the key holder). */
  holderId: number | null;
  holderName: string | null;
  visibility: InventoryVisibility;
  status: InventoryStatus;
  cost: string | null;
  links: InventoryLink[];
  instructionRequired: boolean;
  instructedMemberIds: number[];
  instructedMemberNames: string[];
  createdAt: string;
  updatedAt: string;
  purchaseDate?: string;
  purchaseCost?: string | null;
  currentValue?: string | null;
  location?: string;
  serialNumber?: string;
  barcodeId?: string;
  documents?: { name: string; url: string; type?: string }[];
  imageUrl?: string | null;
  /** The club lets members confirm their own induction (item page only). */
  selfInduction?: boolean;
  notes?: string;
  /** How many are in stock; null while the item isn't counted. */
  stock: number | null;
  /** Reorder level: at or below it the item shows as low. */
  minStock: number | null;
  unit: string;
  lowStock: boolean;
}

/** One line of an item's history: a checkout, a return, or what an add-on
 * recorded (Keys: issue, return, lost, found, retire). */
export interface InventoryHistoryEntry {
  id: string;
  action: string;
  memberId: number | null;
  memberName: string | null;
  byName: string | null;
  note: string | null;
  at: string;
}

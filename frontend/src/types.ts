export type InventoryCategory = "Tool" | "Item" | "Material";
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
  notes?: string;
}

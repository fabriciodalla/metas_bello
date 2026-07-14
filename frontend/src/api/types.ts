export interface HierarchyNodeSummary {
  id: number;
  level: string;
  nome: string;
}

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  hierarchy_node: HierarchyNodeSummary | null;
}

export interface HierarchyNode {
  id: number;
  level: string;
  level_display: string;
  parent: number | null;
  nome: string;
  ativo: boolean;
}

export interface Cycle {
  id: number;
  ano: number;
  mes: number;
  status: "ABERTO" | "FECHADO";
  created_at: string;
  closed_at: string | null;
}

export type Granularity = "GROUP" | "SUBGROUP" | "PRODUCT";

export interface GoalAllocation {
  id: number;
  cycle: number;
  owner_node: number;
  owner_node_level: string;
  owner_node_nome: string;
  parent_allocation: number | null;
  granularity: Granularity;
  group: number | null;
  subgroup: number | null;
  product: number | null;
  quantity_kg: number;
  distributed: boolean;
  criado_por: number;
  created_at: string;
  updated_at: string;
}

export interface ProductGroup {
  id: number;
  nome: string;
  ativo: boolean;
}

export interface ProductSubgroup {
  id: number;
  nome: string;
  group: number;
  ativo: boolean;
}

export interface StuckAllocation {
  allocation_id: number;
  owner_node_id: number;
  owner_node_level: string;
  quantity_kg: number;
}

export interface CycleCompleteness {
  complete: boolean;
  stuck_allocations: StuckAllocation[];
}

export interface ChildAllocationInput {
  owner_node_id: number;
  quantity_kg: number;
  granularity: Granularity;
  group_id?: number | null;
  subgroup_id?: number | null;
  product_id?: number | null;
}

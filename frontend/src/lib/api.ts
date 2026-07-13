const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    throw new Error("Nao autorizado");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // ── Auth ────────────────────────────────
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST", body: JSON.stringify({ username, password }),
    }),
  me: () => request<User>("/auth/me"),

  // ── Hierarchy ───────────────────────────
  getLevels: () => request<HierarchyLevel[]>("/hierarchy/levels"),
  getNodes: (params?: { level_id?: number; parent_id?: number; active_only?: boolean }) =>
    request<HierarchyNode[]>(`/hierarchy/nodes${qs(params || {})}`),
  getNode: (id: number) => request<HierarchyNode>(`/hierarchy/nodes/${id}`),
  getChildren: (id: number) => request<HierarchyNode[]>(`/hierarchy/nodes/${id}/children`),
  getTree: () => request<HierarchyTreeNode[]>("/hierarchy/tree"),
  createNode: (data: { level_id: number; parent_id?: number; source_id: string; name: string }) =>
    request<HierarchyNode>("/hierarchy/nodes", { method: "POST", body: JSON.stringify(data) }),
  updateNode: (id: number, data: { name?: string; parent_id?: number; is_active?: boolean }) =>
    request<HierarchyNode>(`/hierarchy/nodes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  getHierarchyEvents: (nodeId?: number) =>
    request<HierarchyEvent[]>(`/hierarchy/events${qs({ node_id: nodeId })}`),

  // ── Cycles ──────────────────────────────
  getCycles: () => request<GoalCycle[]>("/goals/cycles"),
  createCycle: (month: number, year: number, workingDays?: number) =>
    request<GoalCycle>("/goals/cycles", {
      method: "POST", body: JSON.stringify({ month, year, working_days: workingDays }),
    }),
  getCycle: (id: number) => request<GoalCycle>(`/goals/cycles/${id}`),
  updateCycle: (id: number, data: { status?: string; working_days?: number }) =>
    request<GoalCycle>(`/goals/cycles/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // ── Seller Goals ────────────────────────
  getSellerGoals: (cycleId: number, params?: { category_id?: number; seller_node_id?: number }) =>
    request<SellerGoal[]>(`/goals/seller-goals${qs({ cycle_id: cycleId, ...params })}`),
  getGoalSummary: (cycleId: number, nodeId: number) =>
    request<GoalSummary[]>(`/goals/seller-goals/summary${qs({ cycle_id: cycleId, node_id: nodeId })}`),

  // ── Workspace ───────────────────────────
  getWorkspace: (cycleId: number, categoryId: number, sourceNodeId: number) =>
    request<Workspace>(`/goals/workspace${qs({ cycle_id: cycleId, category_id: categoryId, source_node_id: sourceNodeId })}`),
  distribute: (cycleId: number, categoryId: number, sourceNodeId: number, data: { destination_node_id: number; quantity_kg: number; product_id?: number }) =>
    request<Distribution>(`/goals/workspace/${cycleId}/${categoryId}/${sourceNodeId}/distribute`, {
      method: "POST", body: JSON.stringify(data),
    }),
  bulkDistribute: (cycleId: number, categoryId: number, sourceNodeId: number, items: { destination_node_id: number; quantity_kg: number; product_id?: number }[]) =>
    request<Workspace>(`/goals/workspace/${cycleId}/${categoryId}/${sourceNodeId}/bulk`, {
      method: "PUT", body: JSON.stringify({ items }),
    }),
  confirmDistributions: (cycleId: number, categoryId: number, sourceNodeId: number) =>
    request<{ confirmed: number; total_kg: string; seller_goals_created: number }>(
      `/goals/workspace/${cycleId}/${categoryId}/${sourceNodeId}/confirm`, { method: "POST" },
    ),
  deleteDistribution: (id: number) =>
    request<void>(`/goals/distributions/${id}`, { method: "DELETE" }),
  suggest: (cycleId: number, categoryId: number, sourceNodeId: number, engine: string, startMonth?: string, endMonth?: string) =>
    request<SuggestionResult>(`/goals/workspace/${cycleId}/${categoryId}/${sourceNodeId}/suggest`, {
      method: "POST", body: JSON.stringify({ engine, start_month: startMonth || "", end_month: endMonth || "" }),
    }),
  syncPortfolio: (cycleId: number) =>
    request<{ total_rows: number; matched_sellers: number; unmatched_sellers: number; unmatched_names: string[] }>(
      `/erp/portfolio/sync/${cycleId}`, { method: "POST" },
    ),
  portfolioStats: (cycleId: number) =>
    request<{ cycle_id: number; total_clients: number; matched_sellers: number; unmatched_sellers: number; sellers_count: number }>(
      `/erp/portfolio/stats/${cycleId}`,
    ),

  // ── Client Targets ──────────────────────
  getClientTargets: (goalId: number) => request<ClientTarget[]>(`/goals/seller-goals/${goalId}/clients`),
  addClientTarget: (goalId: number, data: { client_code: string; client_name: string; quantity_kg: number }) =>
    request<ClientTarget>(`/goals/seller-goals/${goalId}/clients`, { method: "POST", body: JSON.stringify(data) }),

  // ── Substitutions ───────────────────────
  getSubstitutions: (cycleId?: number) =>
    request<Substitution[]>(`/goals/substitutions${qs({ cycle_id: cycleId })}`),
  createSubstitution: (data: SubstitutionCreate) =>
    request<Substitution>("/goals/substitutions", { method: "POST", body: JSON.stringify(data) }),

  // ── Products / Categories ───────────────
  getCategories: () => request<CategoryRead[]>("/goals/categories"),

  // ── Node Dashboard ─────────────────────
  getNodeDashboard: (cycleId: number, nodeId?: number) =>
    request<NodeDashboard>(`/goals/node-dashboard${qs({ cycle_id: cycleId, node_id: nodeId })}`),

  // ── Gerencia ───────────────────────────
  getGerenteNodes: () =>
    request<{ id: number; name: string }[]>("/goals/gerencia/nodes"),
  getGerenciaOverview: (cycleId: number, nodeId?: number) =>
    request<GerenciaOverview>(`/goals/gerencia/${cycleId}${qs({ node_id: nodeId })}`),
  setGerenciaBudget: (cycleId: number, items: { category_id: number; budget_kg: number }[], nodeId?: number) =>
    request<{ updated: number }>(`/goals/gerencia/${cycleId}/budget${qs({ node_id: nodeId })}`, {
      method: "PUT", body: JSON.stringify({ items }),
    }),
  getGerenciaDashboard: (cycleId: number, nodeId?: number) =>
    request<DashboardData>(`/goals/gerencia/${cycleId}/dashboard${qs({ node_id: nodeId })}`),

  // ── Calendar / Working Days ────────────
  getHolidays: (year?: number) =>
    request<Holiday[]>(`/calendar/holidays${qs({ year })}`),
  createHoliday: (data: { holiday_date: string; name: string }) =>
    request<Holiday>("/calendar/holidays", { method: "POST", body: JSON.stringify(data) }),
  bulkCreateHolidays: (holidays: { holiday_date: string; name: string }[]) =>
    request<Holiday[]>("/calendar/holidays/bulk", { method: "POST", body: JSON.stringify({ holidays }) }),
  deleteHoliday: (id: number) =>
    request<void>(`/calendar/holidays/${id}`, { method: "DELETE" }),
  getWorkingDaysPreview: (cycleId: number) =>
    request<WorkingDaysPreview>(`/calendar/working-days/${cycleId}`),
  updateWorkingDays: (cycleId: number, months: { year: number; month: number; confirmed_days: number }[]) =>
    request<WorkingDaysPreview>(`/calendar/working-days/${cycleId}`, {
      method: "PUT", body: JSON.stringify({ months }),
    }),
};

// ── Types ──────────────────────────────────

export interface User {
  id: number; email: string; username: string; full_name: string;
  role: string; scope_node_id: number | null; is_active: boolean;
}
export interface HierarchyLevel {
  id: number; name: string; depth: number; prefix: string; is_active: boolean;
}
export interface HierarchyNode {
  id: number; level_id: number; parent_id: number | null; source_id: string;
  name: string; is_active: boolean; level?: HierarchyLevel;
}
export interface HierarchyTreeNode {
  id: number; source_id: string; name: string; level: HierarchyLevel;
  is_active: boolean; children: HierarchyTreeNode[];
}
export interface HierarchyEvent {
  id: number; node_id: number; node_name: string; event_type: string;
  old_parent_id: number | null; new_parent_id: number | null;
  old_parent_name: string; new_parent_name: string;
  effective_on: string; notes: string; created_at: string;
}
export interface GoalCycle {
  id: number; month: number; year: number; status: string;
  working_days: number | null; total_kg: number; sellers_count: number;
}
export interface SellerGoal {
  id: number; cycle_id: number; cycle_label: string;
  category_id: number; category_name: string;
  product_id: number; product_name: string;
  seller_node_id: number; seller_name: string;
  quantity_kg: number; notes: string;
}
export interface GoalSummary {
  node_id: number; node_name: string; node_level: string;
  category_id: number; category_name: string;
  total_kg: number; sellers_count: number; products_count: number;
}
export interface Distribution {
  id: number; cycle_id: number; category_id: number; category_name: string;
  product_id: number | null; product_name: string;
  source_node_id: number | null; source_name: string;
  destination_node_id: number; destination_name: string; destination_level: string;
  quantity_kg: number; status: string; engine_used: string;
}
export interface Workspace {
  source_node_id: number; source_name: string; source_level: string;
  category_id: number; category_name: string;
  received_kg: number; distributed_kg: number; remaining_kg: number;
  can_confirm: boolean; is_product_level: boolean;
  items: Distribution[];
}
export interface SuggestionItem {
  destination_node_id: number; destination_name: string;
  product_id: number | null; product_name: string;
  suggested_kg: number; percent: number;
}
export interface SuggestionResult {
  engine: string; items: SuggestionItem[]; total_kg: number;
}
export interface ClientTarget {
  id: number; seller_goal_id: number; client_code: string;
  client_name: string; quantity_kg: number;
}
export interface Substitution {
  id: number; titular_node_id: number; titular_name: string;
  substitute_node_id: number; substitute_name: string;
  cycle_id: number; starts_on: string; ends_on: string; notes: string;
}
export interface SubstitutionCreate {
  titular_node_id: number; substitute_node_id: number;
  cycle_id: number; starts_on: string; ends_on: string; notes: string;
}
export interface ProductCategory {
  id: number; source_id: string; name: string; is_active: boolean;
}
export interface CategoryRead {
  id: number; source_id: string; name: string; is_active: boolean; products_count: number;
}
export interface GerenciaCategoryBudget {
  category_id: number; category_name: string;
  budget_kg: number; distributed_kg: number; remaining_kg: number;
  children_count: number; is_confirmed: boolean;
}
export interface GerenciaOverview {
  cycle_id: number; cycle_label: string;
  gerente_node_id: number; gerente_name: string;
  categories: GerenciaCategoryBudget[];
}
export interface ProductTarget {
  product_id: number; product_name: string;
  sum_3m: number; daily_avg: number; individual_target: number;
}
export interface CategoryTargets {
  category_id: number; category_name: string;
  products: ProductTarget[];
  total_sum_3m: number; total_daily_avg: number;
  total_individual: number; current_meta: number;
}
export interface TargetsOverview {
  cycle_id: number; cycle_label: string;
  gerente_node_id: number; gerente_name: string;
  target_working_days: number; prev_working_days: number;
  categories: CategoryTargets[];
}
export interface HierarchyStatus {
  node_id: number; node_name: string; level_name: string;
  depth: number; parent_name: string;
  has_distributed: boolean; total_received: number; total_distributed: number;
}
export interface DashboardData {
  targets: TargetsOverview;
  hierarchy_status: HierarchyStatus[];
}
export interface NodeCategoryStatus {
  category_id: number; category_name: string;
  received_kg: number; distributed_kg: number; remaining_kg: number;
  is_fully_distributed: boolean;
}
export interface SubordinateStatus {
  node_id: number; node_name: string; level_name: string;
  total_received_kg: number; total_distributed_kg: number;
  has_distributed: boolean;
}
export interface NodeDashboard {
  node_id: number; node_name: string; level_name: string;
  cycle_id: number; cycle_label: string;
  categories: NodeCategoryStatus[];
  subordinates: SubordinateStatus[];
}
export interface Holiday {
  id: number; holiday_date: string; year: number; name: string;
}
export interface MonthWorkingDays {
  year: number; month: number; label: string;
  weekdays: number; holidays_count: number;
  calculated_days: number; confirmed_days: number | null;
  effective_days: number; is_target: boolean;
}
export interface WorkingDaysPreview {
  cycle_id: number; target_month: number; target_year: number;
  months: MonthWorkingDays[];
}

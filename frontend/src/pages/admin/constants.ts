export const LEVELS = ["GERENTE", "LOCAL", "SUPERVISOR", "VENDEDOR"] as const;
export type Level = (typeof LEVELS)[number];

export const LEVEL_LABELS: Record<Level, string> = {
  GERENTE: "Gerente",
  LOCAL: "Coordenador Local",
  SUPERVISOR: "Supervisor",
  VENDEDOR: "Vendedor",
};

// Supervisor só tem Vendedor como subordinado, e Vendedor é folha (nunca aparece em
// pendências/visão geral) — então Visão Geral e Pendências nunca teriam nada pra mostrar pra ele.
// Mesmo critério usado no menu (Sidebar) e no redirecionamento padrão pós-login (App).
export const OVERVIEW_LEVELS = new Set<Level>(["GERENTE", "LOCAL"]);

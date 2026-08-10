import type { HierarchyNodeSummary } from "../api/types";

// Rótulo da tela "Distribuir Metas" (rota /distribuicao/distribuir), compartilhado por
// Sidebar, Topbar e DistributionPage — muda conforme o nível de quem está logado, mas os três
// precisam concordar no mesmo texto (mesma ordem de `overviewNode` em DistributionPage).
export function distribuirMetasLabel(hierarchyNodes: HierarchyNodeSummary[]): string {
  const levels = new Set(hierarchyNodes.map((n) => n.level));
  if (levels.has("GERENTE")) return "Metas Coordenador Local";
  return "Distribuir Metas";
}

// Coordenador Local puro e Supervisor puro não têm mais uso pra essa tela — os fluxos deles
// inteiros já vivem em "Distribuir Produtos"/"Meta Supervisor" e em "Meta Vendedor".
export function showsDistribuirMetas(hierarchyNodes: HierarchyNodeSummary[]): boolean {
  const levels = new Set(hierarchyNodes.map((n) => n.level));
  return levels.has("GERENTE");
}

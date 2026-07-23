import { SubgroupCascadeWorkspace } from "../components/SubgroupCascadeWorkspace";

// Tela do Coordenador Local: distribui cada meta por subgrupo (criada em "Distribuir Produtos")
// entre os Supervisores. Ver SubgroupCascadeWorkspace para a lógica completa — compartilhada com
// "Meta Vendedor" (MetaVendedorPage.tsx), um nível abaixo na hierarquia.
export function MetaSupervisorPage() {
  return (
    <SubgroupCascadeWorkspace
      ownerLevel="LOCAL"
      noAccessMessage="Esta tela é só para quem tem uma posição de Coordenador Local."
      targetLabelPlural="Supervisores"
      targetLabelSingular="supervisor"
    />
  );
}

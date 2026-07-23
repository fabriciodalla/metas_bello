import { SubgroupCascadeWorkspace } from "../components/SubgroupCascadeWorkspace";

// Tela do Supervisor: distribui cada meta por subgrupo (recebida do Coordenador Local em "Meta
// Supervisor") entre os Vendedores da sua base. Espelho de MetaSupervisorPage.tsx, um nível abaixo
// na hierarquia — ver SubgroupCascadeWorkspace para a lógica completa (compartilhada).
export function MetaVendedorPage() {
  return (
    <SubgroupCascadeWorkspace
      ownerLevel="SUPERVISOR"
      noAccessMessage="Esta tela é só para quem tem uma posição de Supervisor."
      targetLabelPlural="Vendedores"
      targetLabelSingular="vendedor"
    />
  );
}

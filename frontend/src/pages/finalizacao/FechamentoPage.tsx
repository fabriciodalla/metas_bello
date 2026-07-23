import { CheckCircle2 } from "lucide-react";
import { EmptyState } from "../../components/ui/EmptyState";

export function FechamentoPage() {
  return (
    <section>
      <EmptyState icon={<CheckCircle2 size={28} strokeWidth={1.5} />}>Reservado para uso futuro.</EmptyState>
    </section>
  );
}

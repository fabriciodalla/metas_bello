import { TrendingUp } from "lucide-react";
import { EmptyState } from "../../components/ui/EmptyState";

export function AcumuladoVendasPage() {
  return (
    <section>
      <EmptyState icon={<TrendingUp size={28} strokeWidth={1.5} />}>Reservado para uso futuro.</EmptyState>
    </section>
  );
}

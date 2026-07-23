import { BarChart3 } from "lucide-react";
import { EmptyState } from "../../components/ui/EmptyState";

export function DashboardPage() {
  return (
    <section>
      <EmptyState icon={<BarChart3 size={28} strokeWidth={1.5} />}>Reservado para uso futuro.</EmptyState>
    </section>
  );
}

import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { AllocationOverview, Cycle } from "../../api/types";

export function useCycleOverview() {
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [overview, setOverview] = useState<AllocationOverview[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void api.get<Cycle[]>("/cycles/").then(setCycles);
  }, []);

  useEffect(() => {
    if (cycles.length === 0) return;
    setSelectedCycleId((current) => {
      if (current !== null) return current;
      const open = cycles.find((cycle) => cycle.status === "ABERTO");
      return open?.id ?? cycles[0].id;
    });
  }, [cycles]);

  useEffect(() => {
    if (selectedCycleId === null) return;
    setLoading(true);
    void api
      .get<AllocationOverview[]>(`/cycles/${selectedCycleId}/distribution-overview/`)
      .then(setOverview)
      .finally(() => setLoading(false));
  }, [selectedCycleId]);

  return { cycles, selectedCycleId, setSelectedCycleId, overview, loading };
}

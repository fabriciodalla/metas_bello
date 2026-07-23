import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Cycle, GoalAllocation } from "../../api/types";

export function useCycleAllocations() {
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [allocations, setAllocations] = useState<GoalAllocation[]>([]);
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

  function reload() {
    if (selectedCycleId === null) return;
    setLoading(true);
    void api
      .get<GoalAllocation[]>(`/allocations/?cycle=${selectedCycleId}`)
      .then(setAllocations)
      .finally(() => setLoading(false));
  }

  useEffect(reload, [selectedCycleId]);

  return { cycles, selectedCycleId, setSelectedCycleId, allocations, loading, reload };
}

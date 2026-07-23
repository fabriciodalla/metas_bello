import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { VendedorAllocationRow } from "../../api/types";
import { CycleSelect } from "./CycleSelect";
import { useCycleOverview } from "./useCycleOverview";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { Spinner } from "../../components/ui/Spinner";
import { Badge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";

export function MetasPage() {
  const { cycles, selectedCycleId, setSelectedCycleId } = useCycleOverview();
  const [rows, setRows] = useState<VendedorAllocationRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const selectedCycle = cycles.find((cycle) => cycle.id === selectedCycleId);
  const cicloLabel = selectedCycle ? `${String(selectedCycle.mes).padStart(2, "0")}/${selectedCycle.ano}` : "";

  useEffect(() => {
    if (selectedCycleId === null) return;
    setLoading(true);
    void api
      .get<VendedorAllocationRow[]>(`/cycles/${selectedCycleId}/vendedor-report/`)
      .then(setRows)
      .finally(() => setLoading(false));
  }, [selectedCycleId]);

  async function handleDownload() {
    if (selectedCycleId === null) return;
    setDownloadError(null);
    try {
      await api.download(`/cycles/${selectedCycleId}/export/`, `meta_${selectedCycleId}.csv`);
    } catch (error) {
      setDownloadError(error instanceof ApiError ? error.message : "Falha ao baixar o arquivo.");
    }
  }

  return (
    <section>
      <div className="field-group">
        <CycleSelect cycles={cycles} value={selectedCycleId} onChange={setSelectedCycleId} />
        <Button variant="outline" onClick={() => void handleDownload()} disabled={selectedCycleId === null}>
          <Download size={16} /> Baixar meta completa (CSV)
        </Button>
      </div>
      {downloadError && (
        <Alert variant="danger" role="alert">
          {downloadError}
        </Alert>
      )}

      {loading && <Spinner />}
      {!loading && rows.length === 0 && <EmptyState>Nenhuma meta chegou ao Vendedor neste ciclo ainda.</EmptyState>}
      {!loading && rows.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Coordenador Regional</th>
                <th>Coordenador Local</th>
                <th>Supervisor</th>
                <th>Vendedor</th>
                <th>Grupo</th>
                <th>Subgrupo</th>
                <th>Meta (kg)</th>
                <th>Ciclo</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <td>{row.regional}</td>
                  <td>{row.local}</td>
                  <td>{row.supervisor}</td>
                  <td>{row.vendedor}</td>
                  <td>{row.grupo}</td>
                  <td>{row.subgrupo}</td>
                  <td>{row.quantity_kg}</td>
                  <td>{cicloLabel}</td>
                  <td>
                    <Badge variant={row.status === "META AJUSTADA" ? "warning" : "success"}>{row.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

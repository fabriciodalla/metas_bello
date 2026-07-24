import { ChevronDown, ChevronUp } from "lucide-react";
import { Fragment, useState } from "react";
import { Badge } from "./ui/Badge";

export interface PendingAllocationItem {
  id: number;
  ownerNodeId: number;
  ownerNodeUsernames: string[];
  ownerNodeLevel: string;
  groupNome: string | null;
  subgroupNome: string | null;
  quantityKg: number;
  createdAt: string;
}

interface GroupRow {
  groupNome: string;
  totalKg: number;
  earliestCreatedAt: string;
  items: PendingAllocationItem[];
}

interface OwnerGroup {
  ownerNodeId: number;
  ownerNodeUsernames: string[];
  ownerNodeLevel: string;
  totalKg: number;
  groupRows: GroupRow[];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

function formatKg(value: number): string {
  return `${value.toLocaleString("pt-BR")} kg`;
}

// Um subgrupo pendente ainda pertence ao mesmo grupo — junta tudo numa linha por grupo (em vez de
// uma por subgrupo) pra visão geral não crescer demais; só quando um grupo tem mais de um item
// pendente (vários subgrupos) é que aparece o detalhe de quantos faltam.
function aggregateByGroup(items: PendingAllocationItem[]): GroupRow[] {
  const byGroup = new Map<string, GroupRow>();
  for (const item of items) {
    const key = item.groupNome ?? "Sem grupo";
    let row = byGroup.get(key);
    if (!row) {
      row = { groupNome: key, totalKg: 0, earliestCreatedAt: item.createdAt, items: [] };
      byGroup.set(key, row);
    }
    row.totalKg += item.quantityKg;
    row.items.push(item);
    if (item.createdAt < row.earliestCreatedAt) row.earliestCreatedAt = item.createdAt;
  }
  return [...byGroup.values()].sort((a, b) => b.totalKg - a.totalKg);
}

function groupByOwner(items: PendingAllocationItem[]): OwnerGroup[] {
  const byOwner = new Map<number, { ownerNodeUsernames: string[]; ownerNodeLevel: string; items: PendingAllocationItem[] }>();
  for (const item of items) {
    let owner = byOwner.get(item.ownerNodeId);
    if (!owner) {
      owner = { ownerNodeUsernames: item.ownerNodeUsernames, ownerNodeLevel: item.ownerNodeLevel, items: [] };
      byOwner.set(item.ownerNodeId, owner);
    }
    owner.items.push(item);
  }
  return [...byOwner.entries()]
    .map(([ownerNodeId, owner]) => ({
      ownerNodeId,
      ownerNodeUsernames: owner.ownerNodeUsernames,
      ownerNodeLevel: owner.ownerNodeLevel,
      totalKg: owner.items.reduce((sum, item) => sum + item.quantityKg, 0),
      groupRows: aggregateByGroup(owner.items),
    }))
    .sort((a, b) => b.totalKg - a.totalKg);
}

function rowLabel(row: GroupRow) {
  if (row.items.length === 1) {
    const item = row.items[0];
    return item.subgroupNome ? `${row.groupNome} / ${item.subgroupNome}` : row.groupNome;
  }
  return (
    <>
      {row.groupNome} <Badge variant="neutral">{row.items.length} subgrupos</Badge>
    </>
  );
}

// Uma linha por usuário/nó pendente (não por grupo) — cada grupo com pendência vira uma linha no
// detalhe expansível (subgrupos do mesmo grupo somados numa linha só), para deixar claro o que
// falta sem repetir o mesmo usuário nem inflar a lista com uma linha por subgrupo.
export function PendingAllocationsTable({ items }: { items: PendingAllocationItem[] }) {
  const groups = groupByOwner(items);
  const [openOwners, setOpenOwners] = useState<Set<number>>(new Set());

  function toggle(ownerNodeId: number) {
    setOpenOwners((prev) => {
      const next = new Set(prev);
      if (next.has(ownerNodeId)) next.delete(ownerNodeId);
      else next.add(ownerNodeId);
      return next;
    });
  }

  return (
    <div className="table-wrap">
      <table className="table pending-table">
        <thead>
          <tr>
            <th aria-hidden="true" />
            <th>Usuário(s)</th>
            <th>Nível</th>
            <th>Grupos pendentes</th>
            <th>Total pendente</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => {
            const isOpen = openOwners.has(group.ownerNodeId);
            return (
              <Fragment key={group.ownerNodeId}>
                <tr className="pending-row-summary" onClick={() => toggle(group.ownerNodeId)}>
                  <td className="pending-row-toggle">
                    {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </td>
                  <td>
                    {group.ownerNodeUsernames.length > 0 ? (
                      group.ownerNodeUsernames.join(", ")
                    ) : (
                      <Badge variant="neutral">sem usuário vinculado</Badge>
                    )}
                  </td>
                  <td>{group.ownerNodeLevel}</td>
                  <td>
                    <Badge variant="warning">{group.groupRows.length}</Badge>
                  </td>
                  <td>{formatKg(group.totalKg)}</td>
                </tr>
                {isOpen && (
                  <tr className="pending-row-detail">
                    <td />
                    <td colSpan={4}>
                      <table className="pending-detail-table">
                        <thead>
                          <tr>
                            <th>Grupo</th>
                            <th>Meta (kg)</th>
                            <th>Disponibilizado em</th>
                          </tr>
                        </thead>
                        <tbody>
                          {group.groupRows.map((row) => (
                            <tr key={row.groupNome}>
                              <td>{rowLabel(row)}</td>
                              <td>{formatKg(row.totalKg)}</td>
                              <td>{formatDate(row.earliestCreatedAt)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

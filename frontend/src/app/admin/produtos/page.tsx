"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";

interface Category { id: number; source_id: string; name: string; is_active: boolean; products: Product[]; }
interface Product { id: number; source_id: string; name: string; is_active: boolean; category_id: number; }

export default function ProdutosAdminPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/hierarchy/levels`);
      // TODO: add product category endpoint
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-4">Produtos</h2>
      <p className="text-sm text-gray-500 mb-6">Categorias e produtos cadastrados. Gerencie ativacao e inclusao de novos itens.</p>

      {loading ? <p className="text-gray-400">Carregando...</p> : (
        <div className="bg-white rounded-xl border p-5">
          <p className="text-gray-400 text-center py-8">Endpoint de produtos sera adicionado. Dados carregados via seed.</p>
        </div>
      )}
    </Shell>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "./Sidebar";
import { api, User } from "@/lib/api";

export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    api.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-400">Carregando...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar role={user.role} />
      <main className="flex-1 p-6">
        <div className="flex justify-between items-center mb-6">
          <div />
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">
              {user.full_name || user.username}
            </span>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              {user.role}
            </span>
            <button
              onClick={() => {
                localStorage.removeItem("token");
                router.push("/login");
              }}
              className="text-xs text-gray-400 hover:text-red-500"
            >
              Sair
            </button>
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}

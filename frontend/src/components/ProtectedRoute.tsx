import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Spinner } from "./ui/Spinner";

export function ProtectedRoute({
  children,
  adminOnly = false,
  blockAdmin = false,
  gerenteOnly = false,
  localOnly = false,
  supervisorOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
  blockAdmin?: boolean;
  gerenteOnly?: boolean;
  localOnly?: boolean;
  supervisorOnly?: boolean;
}) {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <div className="page">
        <Spinner />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && !user.is_admin) return <Navigate to="/distribuicao" replace />;
  if (blockAdmin && user.is_admin) return <Navigate to="/admin/visao-geral" replace />;
  if (gerenteOnly && !user.hierarchy_nodes.some((n) => n.level === "GERENTE")) {
    return <Navigate to="/distribuicao/distribuir" replace />;
  }
  if (localOnly && !user.hierarchy_nodes.some((n) => n.level === "LOCAL")) {
    return <Navigate to="/distribuicao/distribuir" replace />;
  }
  if (supervisorOnly && !user.hierarchy_nodes.some((n) => n.level === "SUPERVISOR")) {
    return <Navigate to="/distribuicao/distribuir" replace />;
  }
  return <>{children}</>;
}

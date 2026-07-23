import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Sidebar } from "./components/ui/Sidebar";
import { Topbar } from "./components/ui/Topbar";
import { LoginPage } from "./pages/LoginPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { DistributionPage } from "./pages/DistributionPage";
import { DistribuirProdutosPage } from "./pages/DistribuirProdutosPage";
import { MetaSupervisorPage } from "./pages/MetaSupervisorPage";
import { MetaVendedorPage } from "./pages/MetaVendedorPage";
import { MetaGerencialPage } from "./pages/MetaGerencialPage";
import { NivelLayout } from "./pages/nivel/NivelLayout";
import { NivelOverviewPage } from "./pages/nivel/NivelOverviewPage";
import { NivelPendenciasPage } from "./pages/nivel/NivelPendenciasPage";
import { AcompanhamentoLayout } from "./pages/acompanhamento/AcompanhamentoLayout";
import { AcumuladoVendasPage } from "./pages/acompanhamento/AcumuladoVendasPage";
import { AcumuladoClientesPage } from "./pages/acompanhamento/AcumuladoClientesPage";
import { MetasGeraisPage } from "./pages/acompanhamento/MetasGeraisPage";
import { FinalizacaoLayout } from "./pages/finalizacao/FinalizacaoLayout";
import { FechamentoPage } from "./pages/finalizacao/FechamentoPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { OverviewPage } from "./pages/admin/OverviewPage";
import { GestaoPage } from "./pages/admin/GestaoPage";
import { MetasPage } from "./pages/admin/MetasPage";
import { PendenciasPage } from "./pages/admin/PendenciasPage";
import { PreProcessamentoPage } from "./pages/admin/PreProcessamentoPage";
import { DashboardPage } from "./pages/admin/DashboardPage";
import { OVERVIEW_LEVELS, type Level } from "./pages/admin/constants";

const PUBLIC_AUTH_ROUTES = [/^\/login$/, /^\/esqueci-senha$/, /^\/redefinir-senha\//];

function DefaultRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.is_admin ? "/admin/visao-geral" : "/distribuicao"} replace />;
}

function NivelIndexRedirect() {
  const { user } = useAuth();
  const levels = new Set(user?.hierarchy_nodes.map((n) => n.level) ?? []);
  const hasOverview = [...levels].some((level) => OVERVIEW_LEVELS.has(level as Level));
  if (hasOverview) return <Navigate to="visao-geral" replace />;
  // Supervisor não tem Visão Geral (só tem Vendedor como subordinado) — a tela que ele realmente
  // usa pra distribuir é Meta Vendedor.
  if (levels.has("SUPERVISOR")) return <Navigate to="meta-vendedor" replace />;
  return <Navigate to="distribuir" replace />;
}

function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  // Essas rotas nunca mostram a casca autenticada (sidebar/topbar), mesmo que uma sessão já
  // exista — trocar de Fragment pra shell no meio do carregamento remonta {children} e zera o
  // estado local do formulário (o `user` só resolve depois do primeiro paint).
  const isPublicAuthRoute = PUBLIC_AUTH_ROUTES.some((pattern) => pattern.test(location.pathname));

  if (!user || isPublicAuthRoute) return <>{children}</>;

  return (
    <div className="app-shell">
      <Sidebar user={user} />
      <div className="app-main">
        <Topbar user={user} onLogout={logout} />
        {children}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/esqueci-senha" element={<ForgotPasswordPage />} />
            <Route path="/redefinir-senha/:uid/:token" element={<ResetPasswordPage />} />
            <Route
              path="/distribuicao"
              element={
                <ProtectedRoute blockAdmin>
                  <NivelLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<NivelIndexRedirect />} />
              <Route path="distribuir" element={<DistributionPage />} />
              <Route path="visao-geral" element={<NivelOverviewPage />} />
              <Route path="pendencias" element={<NivelPendenciasPage />} />
              <Route
                path="meta-gerencial"
                element={
                  <ProtectedRoute blockAdmin gerenteOnly>
                    <MetaGerencialPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="distribuir-produtos"
                element={
                  <ProtectedRoute blockAdmin localOnly>
                    <DistribuirProdutosPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="meta-supervisor"
                element={
                  <ProtectedRoute blockAdmin localOnly>
                    <MetaSupervisorPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="meta-vendedor"
                element={
                  <ProtectedRoute blockAdmin supervisorOnly>
                    <MetaVendedorPage />
                  </ProtectedRoute>
                }
              />
            </Route>
            <Route
              path="/acompanhamento"
              element={
                <ProtectedRoute blockAdmin>
                  <AcompanhamentoLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="acumulado-vendas" replace />} />
              <Route path="acumulado-vendas" element={<AcumuladoVendasPage />} />
              <Route path="acumulado-clientes" element={<AcumuladoClientesPage />} />
              <Route path="metas-gerais" element={<MetasGeraisPage />} />
            </Route>
            <Route
              path="/finalizacao"
              element={
                <ProtectedRoute blockAdmin>
                  <FinalizacaoLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="fechamento" replace />} />
              <Route path="fechamento" element={<FechamentoPage />} />
            </Route>
            <Route
              path="/admin"
              element={
                <ProtectedRoute adminOnly>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="visao-geral" replace />} />
              <Route path="visao-geral" element={<OverviewPage />} />
              <Route path="gestao" element={<GestaoPage />} />
              <Route path="metas" element={<MetasPage />} />
              <Route path="pendencias" element={<PendenciasPage />} />
              <Route path="pre-processamento" element={<PreProcessamentoPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
            </Route>
            <Route path="*" element={<DefaultRedirect />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
}

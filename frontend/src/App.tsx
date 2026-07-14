import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter, Routes, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { DistributionPage } from "./pages/DistributionPage";
import { AdminPage } from "./pages/AdminPage";

function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div>
      {user && (
        <nav className="topnav">
          <Link to="/distribuicao">Distribuição</Link>
          {user.is_admin && <Link to="/admin">Administrador</Link>}
          <span className="spacer" />
          <span>{user.username}</span>
          <button type="button" onClick={() => void logout()}>
            Sair
          </button>
        </nav>
      )}
      {children}
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
            <Route
              path="/distribuicao"
              element={
                <ProtectedRoute>
                  <DistributionPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/distribuicao" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
}

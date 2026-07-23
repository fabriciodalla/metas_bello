import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      await api.get("/auth/csrf/");
      try {
        const me = await api.get<User>("/auth/me/");
        setUser(me);
      } catch (error) {
        if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) {
          throw error;
        }
      } finally {
        setLoading(false);
      }
    }
    void bootstrap();
  }, []);

  async function login(email: string, password: string) {
    const loggedInUser = await api.post<User>("/auth/login/", { email, password });
    setUser(loggedInUser);
  }

  async function logout() {
    await api.post("/auth/logout/");
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth precisa estar dentro de um AuthProvider.");
  return context;
}

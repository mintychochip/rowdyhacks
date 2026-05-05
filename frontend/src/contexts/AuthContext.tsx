import {
  useUser,
  useAuth as useClerkAuth,
  ClerkProvider,
} from "@clerk/clerk-react";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as api from "../services/api";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "";

// Export ClerkProvider for App.tsx
export { ClerkProvider };

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user: clerkUser, isLoaded } = useUser();
  const { getToken, signOut } = useClerkAuth();

  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;

    if (clerkUser) {
      setIsLoading(true);

      getToken()
        .then((clerkToken) => {
          if (!clerkToken) return;
          setToken(clerkToken);
          localStorage.setItem("auth_token", clerkToken);

          return api.getMe();
        })
        .then((userData) => {
          if (userData) {
            setUser({
              id: userData.id,
              email: userData.email,
              name: userData.name,
              role: userData.role,
            });
          }
        })
        .catch((err) => {
          console.error("Failed to sync user:", err);
          localStorage.removeItem("auth_token");
        })
        .finally(() => setIsLoading(false));
    } else {
      localStorage.removeItem("auth_token");
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  }, [clerkUser, isLoaded, getToken]);

  const login = () => {
    // Clerk handles this via SignIn component
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    signOut?.();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading: isLoading || !isLoaded,
        isAuthenticated: !!clerkUser,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { CLERK_KEY };

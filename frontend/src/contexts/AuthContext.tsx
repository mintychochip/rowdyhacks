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
import { setTokenGetter } from "../services/api";

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

  // Register Clerk's getToken with the API service for automatic token refresh
  useEffect(() => {
    setTokenGetter(async () => {
      try {
        return await getToken();
      } catch (e) {
        console.error('Failed to get Clerk token:', e);
        return null;
      }
    });
  }, [getToken]);

  useEffect(() => {
    if (!isLoaded) return;

    if (clerkUser) {
      setIsLoading(true);

      // Get fresh token and sync with backend
      const syncUser = async () => {
        try {
          const clerkToken = await getToken();
          if (!clerkToken) {
            console.error("No token available from Clerk");
            setIsLoading(false);
            return;
          }

          setToken(clerkToken);

          // Call backend to get or create user
          const userData = await api.getMe();

          if (userData) {
            setUser({
              id: userData.id,
              email: userData.email,
              name: userData.name,
              role: userData.role,
            });
          }
        } catch (err) {
          console.error("Failed to sync user:", err);
          // Backend sync failed - clear user but keep Clerk session
          // so we can retry on next render
          setUser(null);
        } finally {
          setIsLoading(false);
        }
      };

      syncUser();
    } else {
      setToken(null);
      setUser(null);
      setIsLoading(false);
    }
  }, [clerkUser, isLoaded, getToken]);

  const login = () => {
    // Clerk handles this via SignIn component
  };

  const logout = () => {
    signOut?.();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading: isLoading || !isLoaded,
        isAuthenticated: !!user, // Only authenticated if we have synced user data
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

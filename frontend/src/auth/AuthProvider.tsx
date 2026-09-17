import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { getCurrentUser, loginUser } from "../api/auth";
import type { Credentials } from "../api/auth";
import type { User } from "../types/api";

type AuthContextValue = {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (
    credentials: Credentials,
    signal?: AbortSignal,
  ) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const login = useCallback(
    async (
      credentials: Credentials,
      signal?: AbortSignal,
    ): Promise<void> => {
      const tokenResponse = await loginUser(credentials, signal);

      const currentUser = await getCurrentUser(
        tokenResponse.access_token,
        signal,
      );

      setAccessToken(tokenResponse.access_token);
      setUser(currentUser);
    },
    [],
  );

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isAuthenticated: user !== null && accessToken !== null,
      login,
      logout,
    }),
    [user, accessToken, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
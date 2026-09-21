import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getCurrentUser, loginUser } from "../api/auth";
import type { Credentials } from "../api/auth";
import { ApiError } from "../api/client";
import type { User } from "../types/api";

const TOKEN_STORAGE_KEY = "job-tracker.access-token";

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

  const [isInitializing, setIsInitializing] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreRevision, setRestoreRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function restoreSession(): Promise<void> {
      setIsInitializing(true);
      setRestoreError(null);

      try {
        const storedToken = sessionStorage.getItem(TOKEN_STORAGE_KEY);

        if (!storedToken) {
          return;
        }

        const currentUser = await getCurrentUser(
          storedToken,
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        setAccessToken(storedToken);
        setUser(currentUser);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          sessionStorage.removeItem(TOKEN_STORAGE_KEY);
          setAccessToken(null);
          setUser(null);
        } else {
          setRestoreError(
            error instanceof ApiError
              ? error.message
              : "Could not restore your session. Check that browser storage is available.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsInitializing(false);
        }
      }
    }

    void restoreSession();

    return () => controller.abort();
  }, [restoreRevision]);

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

      if (signal?.aborted) {
        return;
      }

      sessionStorage.setItem(
        TOKEN_STORAGE_KEY,
        tokenResponse.access_token,
      );

      setAccessToken(tokenResponse.access_token);
      setUser(currentUser);
      setRestoreError(null);
    },
    [],
  );

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);

    setAccessToken(null);
    setUser(null);
    setRestoreError(null);
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
      {isInitializing ? (
        <main className="page-container">
          <p role="status">Restoring session...</p>
        </main>
      ) : restoreError !== null ? (
        <main className="page-container">
          <h1>Could not restore session</h1>
          <p role="alert">{restoreError}</p>

          <button
            type="button"
            onClick={() => {
              setIsInitializing(true);
              setRestoreError(null);
              setRestoreRevision((value) => value + 1);
            }}
          >
            Try again
          </button>

          <button type="button" onClick={logout}>
            Clear session
          </button>
        </main>
      ) : (
        children
      )}
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
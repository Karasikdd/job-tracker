import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { ReactNode } from "react";

import { ApiError } from "../api/client";
import { getUnreadCount } from "../api/notifications";
import { useAuth } from "../auth/AuthProvider";

type NotificationsContextValue = {
  unreadCount: number | null;
  countError: boolean;
  refreshUnreadCount: () => void;
};

const NotificationsContext =
  createContext<NotificationsContextValue | null>(null);

export function NotificationsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { accessToken, logout } = useAuth();

  return (
    <NotificationsState
      key={accessToken ?? "signed-out"}
      token={accessToken}
      logout={logout}
    >
      {children}
    </NotificationsState>
  );
}

function NotificationsState({
  token,
  logout,
  children,
}: {
  token: string | null;
  logout: () => void;
  children: ReactNode;
}) {
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  const [countError, setCountError] = useState(false);
  const [revision, setRevision] = useState(0);

  const refreshUnreadCount = useCallback(() => {
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (token === null) {
      return;
    }

    const currentToken = token;
    const controller = new AbortController();

    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    async function poll(): Promise<void> {
      if (stopped || controller.signal.aborted) {
        return;
      }

      try {
        const result = await getUnreadCount(
          currentToken,
          controller.signal,
        );

        if (!stopped && !controller.signal.aborted) {
          setUnreadCount(result.count);
          setCountError(false);
        }
      } catch (error) {
        if (stopped || controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          stopped = true;
          setUnreadCount(null);
          logout();
          return;
        }

        setCountError(true);
      } finally {
        if (!stopped && !controller.signal.aborted) {
          timer = setTimeout(() => void poll(), 30_000);
        }
      }
    }

    if (!document.hidden) {
      void poll();
    }

    function handleVisibilityChange(): void {
      if (document.hidden) {
        stopped = true;
        controller.abort();
        clearTimeout(timer);
      } else {
        refreshUnreadCount();
      }
    }

    function handleOnline(): void {
      refreshUnreadCount();
    }

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );
    window.addEventListener("online", handleOnline);

    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );
      window.removeEventListener("online", handleOnline);
    };
  }, [token, logout, revision, refreshUnreadCount]);

  return (
    <NotificationsContext.Provider
      value={{ unreadCount, countError, refreshUnreadCount }}
    >
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsContextValue {
  const context = useContext(NotificationsContext);

  if (context === null) {
    throw new Error(
      "useNotifications must be used within NotificationsProvider",
    );
  }

  return context;
}
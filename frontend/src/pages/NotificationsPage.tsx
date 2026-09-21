import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import {
  listNotifications,
  markNotificationRead,
} from "../api/notifications";
import { useAuth } from "../auth/AuthProvider";
import { NotificationList } from "../components/NotificationList";
import { useNotifications } from "../notifications/NotificationsProvider";

import type { Notification } from "../types/notifications";

const PAGE_SIZE = 20;

export function NotificationsPage() {
  const { accessToken } = useAuth();

  if (accessToken === null) {
    return (
      <section>
        <h1>Please log in</h1>
        <Link to="/login">Go to login</Link>
      </section>
    );
  }

  return <NotificationsContent key={accessToken} token={accessToken} />;
}

function NotificationsContent({ token }: { token: string }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { refreshUnreadCount } = useNotifications();

  const [items, setItems] = useState<Notification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const actionController = useRef<AbortController | null>(null);

  const handleUnauthorized = useCallback(
    (error: unknown): boolean => {
      if (!(error instanceof ApiError) || error.status !== 401) {
        return false;
      }

      logout();
      navigate("/login", {
        replace: true,
        state: {
          from: "/notifications",
          message: "Your session has expired. Please log in again.",
        },
      });

      return true;
    },
    [logout, navigate],
  );

  useEffect(() => {
    return () => {
      actionController.current?.abort();
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function load(): Promise<void> {
      setIsLoading(true);
      setLoadError(null);

      try {
        const result = await listNotifications(
          token,
          unreadOnly,
          offset,
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        if (result.length === 0 && offset > 0) {
          setOffset((value) => Math.max(0, value - PAGE_SIZE));
          return;
        }

        setItems(result);
      } catch (error) {
        if (controller.signal.aborted || handleUnauthorized(error)) {
          return;
        }

        setLoadError(
          error instanceof ApiError
            ? error.message
            : "Could not load notifications.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, [token, unreadOnly, offset, revision, handleUnauthorized]);

  async function handleMarkRead(id: number): Promise<void> {
    if (actionController.current !== null) {
      return;
    }

    const controller = new AbortController();
    actionController.current = controller;

    setBusyId(id);
    setActionError(null);

    try {
      await markNotificationRead(token, id, controller.signal);

      if (controller.signal.aborted) {
        return;
      }

      setIsLoading(true);
      setRevision((value) => value + 1);
      refreshUnreadCount();
    } catch (error) {
      if (controller.signal.aborted || handleUnauthorized(error)) {
        return;
      }

      setActionError(
        error instanceof ApiError
          ? error.message
          : "Could not mark the notification as read.",
      );
    } finally {
      if (actionController.current === controller) {
        actionController.current = null;

        if (!controller.signal.aborted) {
          setBusyId(null);
        }
      }
    }
  }

  function refresh(): void {
    setIsLoading(true);
    setActionError(null);
    setRevision((value) => value + 1);
    refreshUnreadCount();
  }

  const busy = isLoading || busyId !== null;

  return (
    <section>
      <div className="page-heading">
        <div>
          <h1>Notifications</h1>
          <p>Reminders and updates for your applications.</p>
        </div>

        <button type="button" disabled={busy} onClick={refresh}>
          Refresh
        </button>
      </div>

      <label className="notification-filter">
        Show
        <select
          value={unreadOnly ? "unread" : "all"}
          disabled={busy}
          onChange={(event) => {
            setIsLoading(true);
            setUnreadOnly(event.target.value === "unread");
            setOffset(0);
            setActionError(null);
          }}
        >
          <option value="all">All notifications</option>
          <option value="unread">Unread only</option>
        </select>
      </label>

      {actionError !== null && <p role="alert">{actionError}</p>}

      {isLoading ? (
        <p role="status">Loading notifications...</p>
      ) : loadError !== null ? (
        <div role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={refresh}>
            Try again
          </button>
        </div>
      ) : (
        <>
          {items.length === 0 ? (
            <p>
              {unreadOnly
                ? "No unread notifications."
                : "No notifications yet."}
            </p>
          ) : (
            <NotificationList
              items={items}
              busyId={busyId}
              onMarkRead={(id) => void handleMarkRead(id)}
            />
          )}

          <div className="notification-actions">
            <button
              type="button"
              disabled={offset === 0 || busy}
              onClick={() => {
                setIsLoading(true);
                setOffset((value) => Math.max(0, value - PAGE_SIZE));
              }}
            >
              Previous
            </button>

            <span>Page {Math.floor(offset / PAGE_SIZE) + 1}</span>

            <button
              type="button"
              disabled={items.length < PAGE_SIZE || busy}
              onClick={() => {
                setIsLoading(true);
                setOffset((value) => value + PAGE_SIZE);
              }}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
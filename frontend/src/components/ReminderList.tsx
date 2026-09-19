import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import { getNotificationSettings } from "../api/notifications";
import {
  cancelReminder,
  createReminder,
  listApplicationReminders,
  updateReminder,
} from "../api/reminders";
import { useAuth } from "../auth/AuthProvider";
import { ReminderForm } from "./ReminderForm";

import type {
  Reminder,
  ReminderCreate,
  ReminderKind,
  ReminderStatus,
} from "../types/notifications";

const kindLabels: Record<ReminderKind, string> = {
  interview: "Interview",
  follow_up: "Follow-up",
  custom: "Custom",
};

const statusLabels: Record<ReminderStatus, string> = {
  scheduled: "Scheduled",
  fired: "Fired",
  cancelled: "Cancelled",
};

const dateFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Unknown date"
    : dateFormatter.format(date);
}

export function ReminderList({
  applicationId,
}: {
  applicationId: number;
}) {
  const { accessToken } = useAuth();

  if (accessToken === null) {
    return null;
  }

  return (
    <ReminderListContent
      key={`${applicationId}:${accessToken}`}
      applicationId={applicationId}
      token={accessToken}
    />
  );
}

function ReminderListContent({
  applicationId,
  token,
}: {
  applicationId: number;
  token: string;
}) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);

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
          from: location.pathname,
          message: "Your session has expired. Please log in again.",
        },
      });

      return true;
    },
    [logout, navigate, location.pathname],
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
        const [items, preferences] = await Promise.all([
          listApplicationReminders(
            token,
            applicationId,
            offset,
            controller.signal,
          ),
          getNotificationSettings(token, controller.signal),
        ]);

        if (!controller.signal.aborted) {
          setReminders(items);
          setEmailEnabled(preferences.email_enabled);
        }
      } catch (error) {
        if (controller.signal.aborted || handleUnauthorized(error)) {
          return;
        }

        setLoadError(
          error instanceof ApiError
            ? error.message
            : "Could not load reminders.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, [token, applicationId, offset, revision, handleUnauthorized]);

  async function handleSave(payload: ReminderCreate): Promise<void> {
    if (actionController.current !== null) {
      return;
    }

    const controller = new AbortController();
    actionController.current = controller;
    setIsSaving(true);
    setActionError(null);
    setNotice(null);

    try {
      if (editing !== null) {
        await updateReminder(
          token,
          editing.id,
          {
            title: payload.title,
            message: payload.message,
            remind_at: payload.remind_at,
            send_email: payload.send_email,
          },
          controller.signal,
        );
      } else {
        await createReminder(
          token,
          applicationId,
          payload,
          controller.signal,
        );
      }

      if (controller.signal.aborted) {
        return;
      }

      setShowForm(false);
      setEditing(null);
      setOffset(0);
      setRevision((value) => value + 1);
      setNotice("Reminder saved. The list is sorted by scheduled time.");
    } catch (error) {
      if (controller.signal.aborted || handleUnauthorized(error)) {
        return;
      }

      if (error instanceof ApiError && error.status === 409) {
        setShowForm(false);
        setEditing(null);
        setRevision((value) => value + 1);
        setNotice(
          `${error.message}. The list and email settings have been refreshed. ` +
          "If the reminder has fired, create a new one.",
        );
      } else {
        setActionError(
          error instanceof ApiError
            ? error.message
            : "Could not save the reminder.",
        );
      }
    } finally {
      if (actionController.current === controller) {
        actionController.current = null;

        if (!controller.signal.aborted) {
          setIsSaving(false);
        }
      }
    }
  }

  async function handleCancel(reminder: Reminder): Promise<void> {
    if (actionController.current !== null) {
      return;
    }

    if (!window.confirm(`Cancel "${reminder.title}"?`)) {
      return;
    }

    const controller = new AbortController();
    actionController.current = controller;
    setCancellingId(reminder.id);
    setActionError(null);
    setNotice(null);

    try {
      await cancelReminder(token, reminder.id, controller.signal);

      if (!controller.signal.aborted) {
        setRevision((value) => value + 1);
        setNotice("Reminder cancelled.");
      }
    } catch (error) {
      if (controller.signal.aborted || handleUnauthorized(error)) {
        return;
      }

      setActionError(
        error instanceof ApiError
          ? error.message
          : "Could not cancel the reminder.",
      );

      if (error instanceof ApiError && error.status === 409) {
        setRevision((value) => value + 1);
      }
    } finally {
      if (actionController.current === controller) {
        actionController.current = null;

        if (!controller.signal.aborted) {
          setCancellingId(null);
        }
      }
    }
  }

  const busy = isSaving || cancellingId !== null;

  return (
    <section className="detail-section">
      <div className="page-heading">
        <h2>Reminders</h2>

        <div className="reminder-actions">
          <button
            type="button"
            disabled={isLoading || busy || showForm}
            onClick={() => setRevision((value) => value + 1)}
          >
            Refresh
          </button>

          <button
            type="button"
            disabled={isLoading || busy || showForm || loadError !== null}
            onClick={() => {
              setEditing(null);
              setActionError(null);
              setNotice(null);
              setShowForm(true);
            }}
          >
            Add reminder
          </button>
        </div>
      </div>

      {notice !== null && <p role="status">{notice}</p>}

      {showForm && (
        <ReminderForm
          key={editing?.id ?? "new"}
          initialReminder={editing}
          emailEnabled={emailEnabled}
          isSubmitting={isSaving}
          errorMessage={actionError}
          onSubmit={handleSave}
          onCancel={() => {
            if (actionController.current !== null) {
              return;
            }

            setShowForm(false);
            setEditing(null);
            setActionError(null);
          }}
        />
      )}

      {!showForm && actionError !== null && (
        <p role="alert">{actionError}</p>
      )}

      {isLoading ? (
        <p role="status">Loading reminders...</p>
      ) : loadError !== null ? (
        <div role="alert">
          <p>{loadError}</p>
          <button
            type="button"
            onClick={() => setRevision((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          {reminders.length === 0 ? (
            <p>
              {offset === 0
                ? "No reminders yet."
                : "No more reminders. Return to the previous page."}
            </p>
          ) : (
            <ul className="reminder-list">
              {reminders.map((reminder) => (
                <li className="reminder-card" key={reminder.id}>
                  <h3>{reminder.title}</h3>

                  <p>
                    {kindLabels[reminder.kind]} ·{" "}
                    {statusLabels[reminder.status]}
                  </p>

                  <p>
                    Scheduled:{" "}
                    <time dateTime={reminder.remind_at}>
                      {formatDate(reminder.remind_at)}
                    </time>
                  </p>

                  {reminder.message && (
                    <p className="reminder-message">{reminder.message}</p>
                  )}

                  <p>
                    Email requested: {reminder.send_email ? "Yes" : "No"}
                  </p>

                  {reminder.fired_at && (
                    <p>
                      Processed:{" "}
                      <time dateTime={reminder.fired_at}>
                        {formatDate(reminder.fired_at)}
                      </time>
                    </p>
                  )}

                  {reminder.status === "scheduled" && (
                    <div className="reminder-actions">
                      <button
                        type="button"
                        disabled={busy || showForm}
                        onClick={() => {
                          setEditing(reminder);
                          setActionError(null);
                          setNotice(null);
                          setShowForm(true);
                        }}
                      >
                        Edit
                      </button>

                      <button
                        type="button"
                        disabled={busy || showForm}
                        onClick={() => void handleCancel(reminder)}
                      >
                        {cancellingId === reminder.id
                          ? "Cancelling..."
                          : "Cancel reminder"}
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          <div className="reminder-actions">
            <button
              type="button"
              disabled={offset === 0 || busy || showForm}
              onClick={() => setOffset((value) => Math.max(0, value - 20))}
            >
              Previous
            </button>

            <span>Page {Math.floor(offset / 20) + 1}</span>

            <button
              type="button"
              disabled={reminders.length < 20 || busy || showForm}
              onClick={() => setOffset((value) => value + 20)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
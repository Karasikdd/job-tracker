import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import {
  getNotificationSettings,
  updateNotificationSettings,
} from "../api/notifications";
import { useAuth } from "../auth/AuthProvider";

export function SettingsPage() {
  const { accessToken } = useAuth();

  if (accessToken === null) {
    return (
      <section>
        <h1>Please log in</h1>
        <Link to="/login">Go to login</Link>
      </section>
    );
  }

  return <SettingsContent key={accessToken} token={accessToken} />;
}

function SettingsContent({ token }: { token: string }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [emailEnabled, setEmailEnabled] = useState(false);
  const [savedEmailEnabled, setSavedEmailEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const saveController = useRef<AbortController | null>(null);

  const handleUnauthorized = useCallback(
    (error: unknown): boolean => {
      if (!(error instanceof ApiError) || error.status !== 401) {
        return false;
      }

      logout();
      navigate("/login", {
        replace: true,
        state: {
          from: "/settings",
          message: "Your session has expired. Please log in again.",
        },
      });

      return true;
    },
    [logout, navigate],
  );

  useEffect(() => {
    return () => {
      saveController.current?.abort();
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function load(): Promise<void> {
      setIsLoading(true);
      setLoadError(null);

      try {
        const settings = await getNotificationSettings(
          token,
          controller.signal,
        );

        if (controller.signal.aborted) {
          return;
        }

        setEmailEnabled(settings.email_enabled);
        setSavedEmailEnabled(settings.email_enabled);
      } catch (error) {
        if (controller.signal.aborted || handleUnauthorized(error)) {
          return;
        }

        setLoadError(
          error instanceof ApiError
            ? error.message
            : "Could not load notification settings.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => controller.abort();
  }, [token, revision, handleUnauthorized]);

  async function save(): Promise<void> {
    if (
      isLoading ||
      saveController.current !== null ||
      emailEnabled === savedEmailEnabled
    ) {
      return;
    }

    const controller = new AbortController();
    saveController.current = controller;

    setIsSaving(true);
    setSaveError(null);
    setNotice(null);

    try {
      const settings = await updateNotificationSettings(
        token,
        emailEnabled,
        controller.signal,
      );

      if (controller.signal.aborted) {
        return;
      }

      setEmailEnabled(settings.email_enabled);
      setSavedEmailEnabled(settings.email_enabled);
      setNotice("Notification settings saved.");
    } catch (error) {
      if (controller.signal.aborted || handleUnauthorized(error)) {
        return;
      }

      setSaveError(
        error instanceof ApiError
          ? error.message
          : "Could not save notification settings.",
      );
    } finally {
      if (saveController.current === controller) {
        saveController.current = null;

        if (!controller.signal.aborted) {
          setIsSaving(false);
        }
      }
    }
  }

  const hasChanges = emailEnabled !== savedEmailEnabled;

  return (
    <section>
      <div className="page-heading">
        <div>
          <h1>Settings</h1>
          <p>Manage your notification preferences.</p>
        </div>
      </div>

      {isLoading ? (
        <p role="status">Loading settings...</p>
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
        <form
          className="settings-card"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2>Notifications</h2>

          <fieldset disabled={isSaving}>
            <label className="settings-checkbox">
              <input
                type="checkbox"
                checked={emailEnabled}
                aria-describedby="email-settings-description"
                onChange={(event) => {
                  setEmailEnabled(event.target.checked);
                  setSaveError(null);
                  setNotice(null);
                }}
              />
              <span>Enable email reminders</span>
            </label>

            <p id="email-settings-description">
              Allow email delivery for reminders where you select
              “Also send email”.
            </p>

            <p>
              In-app notifications remain available when email is
              disabled.
            </p>

            <div className="settings-actions">
              <button
                type="submit"
                disabled={!hasChanges || isSaving}
              >
                {isSaving ? "Saving..." : "Save settings"}
              </button>

              <button
                type="button"
                disabled={!hasChanges || isSaving}
                onClick={() => {
                  setEmailEnabled(savedEmailEnabled);
                  setSaveError(null);
                  setNotice(null);
                }}
              >
                Reset changes
              </button>
            </div>
          </fieldset>

          {hasChanges && <p>You have unsaved changes.</p>}
          {notice !== null && <p role="status">{notice}</p>}
          {saveError !== null && <p role="alert">{saveError}</p>}
        </form>
      )}
    </section>
  );
}
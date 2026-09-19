import { useEffect, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from "react-router";

import {
  deleteApplication,
  getApplication,
  updateApplication,
} from "../api/applications";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { ApplicationForm } from "../components/ApplicationForm";
import { ApplicationHistory } from "../components/ApplicationHistory";
import { ErrorMessage } from "../components/ErrorMessage";
import { StatusBadge } from "../components/StatusBadge";
import { ReminderList } from "../components/ReminderList";
import type {
  ApplicationCreate,
  JobApplication,
} from "../types/api";

const dateTimeFormatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return dateTimeFormatter.format(date);
}

function getSafeUrl(value: string | null): string | null {
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);

    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }

    return url.href;
  } catch {
    return null;
  }
}

export function ApplicationPage() {
  const { id } = useParams();

  return <ApplicationDetail key={id ?? ""} id={id} />;
}

function ApplicationDetail({ id }: { id: string | undefined }) {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const applicationId = Number(id);
  const isValidId =
    Number.isSafeInteger(applicationId) && applicationId > 0;

  const [application, setApplication] =
    useState<JobApplication | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [reloadNumber, setReloadNumber] = useState(0);
  const [historyRevision, setHistoryRevision] = useState(0);

  const updateControllerRef = useRef<AbortController | null>(null);
  const deleteControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      updateControllerRef.current?.abort();
      updateControllerRef.current = null;
      deleteControllerRef.current?.abort();
      deleteControllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!isValidId || accessToken === null) {
      setApplication(null);
      setIsLoading(false);
      return;
    }

    const token = accessToken;
    const controller = new AbortController();

    async function loadApplication(): Promise<void> {
      setIsLoading(true);
      setLoadError(null);
      setDeleteError(null);
      setFormError(null);
      setIsEditing(false);
      setApplication(null);

      try {
        const result = await getApplication(
          token,
          applicationId,
          controller.signal,
        );

        if (!controller.signal.aborted) {
          setApplication(result);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          logout();

          navigate("/login", {
            replace: true,
            state: {
              from: location.pathname,
              message: "Your session has expired. Please log in again.",
            },
          });

          return;
        }

        setLoadError(
          error instanceof ApiError
            ? error.message
            : "An unexpected error occurred.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadApplication();

    return () => {
      controller.abort();
    };
  }, [
    accessToken,
    applicationId,
    isValidId,
    location.pathname,
    logout,
    navigate,
    reloadNumber,
  ]);

  async function handleUpdate(
    payload: ApplicationCreate,
  ): Promise<void> {
    if (
      accessToken === null ||
      application === null ||
      updateControllerRef.current !== null
    ) {
      return;
    }

    const token = accessToken;
    const currentApplicationId = application.id;
    const controller = new AbortController();

    updateControllerRef.current = controller;
    setFormError(null);

    try {
      const updatedApplication = await updateApplication(
        token,
        currentApplicationId,
        payload,
        controller.signal,
      );

      if (controller.signal.aborted) {
        return;
      }

      setApplication(updatedApplication);
      setHistoryRevision((current) => current + 1);
      setIsEditing(false);
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        logout();

        navigate("/login", {
          replace: true,
          state: {
            from: location.pathname,
            message: "Your session has expired. Please log in again.",
          },
        });

        return;
      }

      setFormError(
        error instanceof ApiError
          ? error.message
          : "An unexpected error occurred.",
      );
    } finally {
      if (updateControllerRef.current === controller) {
        updateControllerRef.current = null;
      }
    }
  }

  async function handleDelete(): Promise<void> {
    if (
      accessToken === null ||
      application === null ||
      deleteControllerRef.current !== null
    ) {
      return;
    }

    const token = accessToken;
    const currentApplicationId = application.id;

    const confirmed = window.confirm(
      `Delete the application for ${application.position} at ${application.company}?`,
    );

    if (!confirmed) {
      return;
    }

    const controller = new AbortController();
    deleteControllerRef.current = controller;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteApplication(
        token,
        currentApplicationId,
        controller.signal,
      );

      if (!controller.signal.aborted) {
        navigate("/applications", {
          replace: true,
        });
      }
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        logout();

        navigate("/login", {
          replace: true,
          state: {
            from: location.pathname,
            message: "Your session has expired. Please log in again.",
          },
        });

        return;
      }

      setDeleteError(
        error instanceof ApiError
          ? error.message
          : "An unexpected error occurred.",
      );
    } finally {
      if (deleteControllerRef.current === controller) {
        deleteControllerRef.current = null;
        setIsDeleting(false);
      }
    }
  }

  if (!isValidId) {
    return (
      <section>
        <h1>Invalid application ID</h1>
        <p>The application ID must be a positive integer.</p>
        <Link to="/applications">Return to applications</Link>
      </section>
    );
  }

  if (accessToken === null) {
    return (
      <section>
        <h1>Please log in</h1>
        <p>You must be logged in to view this application.</p>
        <Link to="/login">Go to login</Link>
      </section>
    );
  }

  if (isLoading) {
    return <p role="status">Loading application...</p>;
  }

  if (loadError !== null) {
    return (
      <section>
        <h1>Could not load application</h1>

        <ErrorMessage
          message={loadError}
          onRetry={() => setReloadNumber((current) => current + 1)}
        />

        <p>
          <Link to="/applications">Return to applications</Link>
        </p>
      </section>
    );
  }

  if (application === null) {
    return (
      <section>
        <h1>Application not found</h1>
        <Link to="/applications">Return to applications</Link>
      </section>
    );
  }

  if (isEditing) {
    return (
      <section>
        <div className="page-heading">
          <div>
            <h1>Edit application</h1>
            <p>
              {application.position} at {application.company}
            </p>
          </div>
        </div>

        <ApplicationForm
          initialApplication={application}
          submitLabel="Save changes"
          errorMessage={formError}
          onSubmit={handleUpdate}
          onCancel={() => {
            if (updateControllerRef.current !== null) {
              return;
            }

            setFormError(null);
            setIsEditing(false);
          }}
        />
      </section>
    );
  }

  const vacancyUrl = getSafeUrl(application.url);

  return (
    <section>
      <div className="page-heading">
        <div>
          <p>
            <Link to="/applications">← Back to applications</Link>
          </p>

          <h1>{application.position}</h1>
          <p>{application.company}</p>
        </div>

        <div className="detail-actions">
          <button
            type="button"
            onClick={() => {
              setFormError(null);
              setDeleteError(null);
              setIsEditing(true);
            }}
            disabled={isDeleting}
          >
            Edit
          </button>

          <button
            className="danger-button"
            type="button"
            onClick={() => void handleDelete()}
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>

      {deleteError !== null && (
        <p role="alert">{deleteError}</p>
      )}

      <dl className="application-details">
        <div>
          <dt>Status</dt>
          <dd>
            <StatusBadge status={application.status} />
          </dd>
        </div>

        <div>
          <dt>Location</dt>
          <dd>{application.location || "—"}</dd>
        </div>

        <div>
          <dt>Created</dt>
          <dd>{formatDateTime(application.created_at)}</dd>
        </div>

        <div>
          <dt>Updated</dt>
          <dd>{formatDateTime(application.updated_at)}</dd>
        </div>
      </dl>

      {vacancyUrl !== null && (
        <section className="detail-section">
          <h2>Vacancy link</h2>

          <a
            href={vacancyUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open vacancy
          </a>
        </section>
      )}

      <section className="detail-section">
        <h2>Notes</h2>

        {application.notes ? (
          <p className="application-notes">{application.notes}</p>
        ) : (
          <p>No notes added.</p>
        )}
      </section>

      <ApplicationHistory
        applicationId={application.id}
        revision={historyRevision}
      />
      <ReminderList applicationId={application.id} />
    </section>
  );
}
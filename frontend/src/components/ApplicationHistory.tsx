import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";

import { getApplicationHistory } from "../api/applications";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "./ErrorMessage";
import { StatusBadge } from "./StatusBadge";

import type { StatusHistory } from "../types/api";

type ApplicationHistoryProps = {
  applicationId: number;
  revision: number;
};

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

export function ApplicationHistory({
  applicationId,
  revision,
}: ApplicationHistoryProps) {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [history, setHistory] = useState<StatusHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryNumber, setRetryNumber] = useState(0);

  useEffect(() => {
    if (accessToken === null) {
      setHistory([]);
      setIsLoading(false);
      return;
    }

    const token = accessToken;
    const controller = new AbortController();

    async function loadHistory(): Promise<void> {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const result = await getApplicationHistory(
          token,
          applicationId,
          controller.signal,
        );

        if (!controller.signal.aborted) {
          setHistory(result);
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

        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "Could not load status history.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadHistory();

    return () => {
      controller.abort();
    };
  }, [
    accessToken,
    applicationId,
    revision,
    retryNumber,
    location.pathname,
    logout,
    navigate,
  ]);

  return (
    <section className="detail-section">
      <h2>Status history</h2>

      {isLoading ? (
        <p role="status">Loading status history...</p>
      ) : errorMessage !== null ? (
        <ErrorMessage
          message={errorMessage}
          onRetry={() => setRetryNumber((current) => current + 1)}
        />
      ) : history.length === 0 ? (
        <p>No status changes yet.</p>
      ) : (
        <div className="status-history-scroll">
          <table className="status-history-table">
            <caption>Status changes, oldest first</caption>

            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Previous status</th>
                <th scope="col">New status</th>
              </tr>
            </thead>

            <tbody>
              {history.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    <time dateTime={entry.changed_at}>
                      {formatDateTime(entry.changed_at)}
                    </time>
                  </td>

                  <td>
                    <StatusBadge status={entry.old_status} />
                  </td>

                  <td>
                    <StatusBadge status={entry.new_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
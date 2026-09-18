import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router";

import { listApplications } from "../api/applications";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";
import { StatusBadge } from "../components/StatusBadge";

import type {
  ApplicationStatus,
  JobApplication,
} from "../types/api";

const PAGE_SIZE = 20;

const STATUS_OPTIONS: Array<{
  value: "" | ApplicationStatus;
  label: string;
}> = [
  { value: "", label: "All statuses" },
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
];

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
});

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return dateFormatter.format(date);
}

export function ApplicationsPage() {
  const {
    accessToken,
    logout,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const [applications, setApplications] = useState<JobApplication[]>([]);

  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const [status, setStatus] = useState<"" | ApplicationStatus>("");

  const [offset, setOffset] = useState(0);
  const [reloadNumber, setReloadNumber] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadApplications = useCallback(
    async (signal: AbortSignal) => {
      if (accessToken === null) {
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const result = await listApplications(
          accessToken,
          {
            status: status === "" ? undefined : status,
            search: appliedSearch === "" ? undefined : appliedSearch,
            limit: PAGE_SIZE,
            offset,
          },
          signal,
        );

        setApplications(result);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
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

        if (error instanceof ApiError) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("An unexpected error occurred.");
        }
      } finally {
        if (!signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [
      accessToken,
      appliedSearch,
      location.pathname,
      logout,
      navigate,
      offset,
      status,
    ],
  );

  useEffect(() => {
    const controller = new AbortController();

    void loadApplications(controller.signal);

    return () => {
      controller.abort();
    };
  }, [loadApplications, reloadNumber]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setOffset(0);
    setAppliedSearch(searchInput.trim());
  }

  function handleStatusChange(value: "" | ApplicationStatus) {
    setStatus(value);
    setOffset(0);
  }

  function handleClearFilters() {
    setSearchInput("");
    setAppliedSearch("");
    setStatus("");
    setOffset(0);
  }

  function handleRetry() {
    setReloadNumber((current) => current + 1);
  }

  function handlePreviousPage() {
    setOffset((current) => Math.max(0, current - PAGE_SIZE));
  }

  function handleNextPage() {
    setOffset((current) => current + PAGE_SIZE);
  }

  const pageNumber = Math.floor(offset / PAGE_SIZE) + 1;
  const hasActiveFilters = appliedSearch !== "" || status !== "";
  const canGoToNextPage = applications.length === PAGE_SIZE;

  return (
    <section>
      <div className="page-heading">
        <div>
          <h1>Job applications</h1>

          <p>
            Search, filter, and manage your job applications.
          </p>
        </div>

        <Link
          className="button-link"
          to="/applications/new"
        >
          Add application
        </Link>
      </div>

      <form
        className="application-filters"
        onSubmit={handleSearch}
      >
        <div className="form-field filter-search">
          <label htmlFor="application-search">
            Search
          </label>

          <input
            id="application-search"
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Company or position"
            maxLength={200}
          />
        </div>

        <div className="form-field filter-status">
          <label htmlFor="application-status">
            Status
          </label>

          <select
            id="application-status"
            value={status}
            onChange={(event) =>
              handleStatusChange(
                event.target.value as "" | ApplicationStatus,
              )
            }
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-actions">
          <button type="submit" disabled={isLoading}>
            Search
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={handleClearFilters}
            disabled={!hasActiveFilters && searchInput === ""}
          >
            Clear
          </button>
        </div>
      </form>

      {isLoading && (
        <p role="status">Loading applications...</p>
      )}

      {!isLoading && errorMessage !== null && (
        <ErrorMessage
          message={errorMessage}
          onRetry={handleRetry}
        />
      )}

      {!isLoading &&
        errorMessage === null &&
        applications.length === 0 && (
          <div className="empty-state">
            <h2>No applications found</h2>

            {hasActiveFilters ? (
              <>
                <p>
                  No applications match the selected filters.
                </p>

                <button
                  className="secondary-button"
                  type="button"
                  onClick={handleClearFilters}
                >
                  Clear filters
                </button>
              </>
            ) : (
              <p>
                Add your first job application to start tracking it.
              </p>
            )}
          </div>
        )}

      {!isLoading &&
        errorMessage === null &&
        applications.length > 0 && (
          <>
            <div className="table-container">
              <table className="applications-table">
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Position</th>
                    <th scope="col">Status</th>
                    <th scope="col">Location</th>
                    <th scope="col">Created</th>
                    <th scope="col">
                      <span className="visually-hidden">
                        Actions
                      </span>
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {applications.map((application) => (
                    <tr key={application.id}>
                      <td>{application.company}</td>
                      <td>{application.position}</td>

                      <td>
                        <StatusBadge status={application.status} />
                      </td>

                      <td>{application.location ?? "—"}</td>
                      <td>{formatDate(application.created_at)}</td>

                      <td>
                        <Link
                          to={`/applications/${application.id}`}
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <nav
              className="pagination"
              aria-label="Applications pagination"
            >
              <button
                className="secondary-button"
                type="button"
                onClick={handlePreviousPage}
                disabled={offset === 0 || isLoading}
              >
                Previous
              </button>

              <span>Page {pageNumber}</span>

              <button
                className="secondary-button"
                type="button"
                onClick={handleNextPage}
                disabled={!canGoToNextPage || isLoading}
              >
                Next
              </button>
            </nav>
          </>
        )}
    </section>
  );
}
import {
  type FormEvent,
  useState,
} from "react";

import type {
  ApplicationCreate,
  ApplicationStatus,
  JobApplication,
} from "../types/api";

type ApplicationFormProps = {
  initialApplication?: JobApplication;
  submitLabel: string;
  errorMessage: string | null;
  onSubmit: (payload: ApplicationCreate) => Promise<void>;
  onCancel?: () => void;
};

const STATUS_OPTIONS: Array<{
  value: ApplicationStatus;
  label: string;
}> = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
];

function emptyStringToNull(value: string): string | null {
  const normalized = value.trim();
  return normalized === "" ? null : normalized;
}

export function ApplicationForm({
  initialApplication,
  submitLabel,
  errorMessage,
  onSubmit,
  onCancel,
}: ApplicationFormProps) {
  const [company, setCompany] = useState(
    initialApplication?.company ?? "",
  );

  const [position, setPosition] = useState(
    initialApplication?.position ?? "",
  );

  const [status, setStatus] = useState<ApplicationStatus>(
    initialApplication?.status ?? "saved",
  );

  const [url, setUrl] = useState(
    initialApplication?.url ?? "",
  );

  const [location, setLocation] = useState(
    initialApplication?.location ?? "",
  );

  const [notes, setNotes] = useState(
    initialApplication?.notes ?? "",
  );

  const [validationMessage, setValidationMessage] =
    useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setValidationMessage(null);

    const normalizedCompany = company.trim();
    const normalizedPosition = position.trim();

    if (normalizedCompany === "") {
      setValidationMessage("Company is required.");
      return;
    }

    if (normalizedPosition === "") {
      setValidationMessage("Position is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit({
        company: normalizedCompany,
        position: normalizedPosition,
        status,
        url: emptyStringToNull(url),
        location: emptyStringToNull(location),
        notes: emptyStringToNull(notes),
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  const displayedError = validationMessage ?? errorMessage;

  return (
    <form
      className="application-form"
      onSubmit={handleSubmit}
    >
      <div className="form-field">
        <label htmlFor="application-company">
          Company
        </label>

        <input
          id="application-company"
          name="company"
          type="text"
          value={company}
          onChange={(event) => setCompany(event.target.value)}
          minLength={1}
          maxLength={200}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="application-position">
          Position
        </label>

        <input
          id="application-position"
          name="position"
          type="text"
          value={position}
          onChange={(event) => setPosition(event.target.value)}
          minLength={1}
          maxLength={200}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="application-status">
          Status
        </label>

        <select
          id="application-status"
          name="status"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as ApplicationStatus)
          }
          disabled={isSubmitting}
        >
          {STATUS_OPTIONS.map((option) => (
            <option
              key={option.value}
              value={option.value}
            >
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-field">
        <label htmlFor="application-url">
          Vacancy URL
        </label>

        <input
          id="application-url"
          name="url"
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          maxLength={4096}
          placeholder="https://example.com/vacancy"
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="application-location">
          Location
        </label>

        <input
          id="application-location"
          name="location"
          type="text"
          value={location}
          onChange={(event) => setLocation(event.target.value)}
          maxLength={200}
          placeholder="Munich, Berlin, Remote..."
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="application-notes">
          Notes
        </label>

        <textarea
          id="application-notes"
          name="notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          maxLength={10000}
          rows={7}
          disabled={isSubmitting}
        />

        <small>
          {notes.length} / 10000 characters
        </small>
      </div>

      {displayedError !== null && (
        <p className="error-message" role="alert">
          {displayedError}
        </p>
      )}

      <div className="form-actions">
        <button
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Saving..." : submitLabel}
        </button>

        {onCancel !== undefined && (
          <button
            className="secondary-button"
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
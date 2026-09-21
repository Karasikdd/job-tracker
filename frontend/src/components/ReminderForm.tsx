import { useState } from "react";
import type { FormEvent } from "react";

import type {
  Reminder,
  ReminderCreate,
  ReminderKind,
} from "../types/notifications";

type ReminderFormProps = {
  initialReminder: Reminder | null;
  emailEnabled: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: ReminderCreate) => Promise<void>;
  onCancel: () => void;
};

function toLocalInput(value: Date): string {
  const pad = (number: number) => String(number).padStart(2, "0");

  return (
    `${value.getFullYear()}-${pad(value.getMonth() + 1)}-` +
    `${pad(value.getDate())}T${pad(value.getHours())}:` +
    `${pad(value.getMinutes())}`
  );
}

export function ReminderForm({
  initialReminder,
  emailEnabled,
  isSubmitting,
  errorMessage,
  onSubmit,
  onCancel,
}: ReminderFormProps) {
  const [title, setTitle] = useState(initialReminder?.title ?? "");
  const [message, setMessage] = useState(initialReminder?.message ?? "");
  const [kind, setKind] = useState<ReminderKind>(
    initialReminder?.kind ?? "custom",
  );
  const [localTime, setLocalTime] = useState(() =>
    toLocalInput(
      initialReminder
        ? new Date(initialReminder.remind_at)
        : new Date(Date.now() + 60 * 60 * 1000),
    ),
  );
  const [sendEmail, setSendEmail] = useState(
    emailEnabled && (initialReminder?.send_email ?? false),
  );
  const [validationError, setValidationError] = useState<string | null>(
    null,
  );

  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setValidationError(null);

    const normalizedTitle = title.trim();
    const normalizedMessage = message.trim();
    const date = new Date(localTime);

    if (!normalizedTitle || normalizedTitle.length > 200) {
      setValidationError("Enter a title between 1 and 200 characters.");
      return;
    }

    if (normalizedMessage.length > 2000) {
      setValidationError("The message must not exceed 2000 characters.");
      return;
    }

    if (Number.isNaN(date.getTime()) || date.getTime() <= Date.now()) {
      setValidationError("Choose a date and time in the future.");
      return;
    }

    if (toLocalInput(date) !== localTime) {
      setValidationError(
        "This local time is unavailable because of a clock change. Choose another time.",
      );
      return;
    }

    await onSubmit({
      title: normalizedTitle,
      message: normalizedMessage || null,
      kind,
      remind_at: date.toISOString(),
      send_email: emailEnabled && sendEmail,
    });
  }

  return (
    <form className="reminder-form" onSubmit={handleSubmit}>
      <h3>{initialReminder ? "Edit reminder" : "Add reminder"}</h3>

      <fieldset disabled={isSubmitting}>
        <label>
          Type
          <select
            value={kind}
            disabled={initialReminder !== null}
            onChange={(event) =>
              setKind(event.target.value as ReminderKind)
            }
          >
            <option value="interview">Interview</option>
            <option value="follow_up">Follow-up</option>
            <option value="custom">Custom</option>
          </select>
        </label>

        <label>
          Title
          <input
            type="text"
            value={title}
            maxLength={200}
            required
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label>
          Message
          <textarea
            value={message}
            maxLength={2000}
            rows={4}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>

        <label>
          Date and time
          <input
            type="datetime-local"
            value={localTime}
            required
            onChange={(event) => setLocalTime(event.target.value)}
          />
        </label>

        <p>Time zone: {timeZone}</p>

        <label className="reminder-checkbox">
          <input
            type="checkbox"
            checked={emailEnabled && sendEmail}
            disabled={!emailEnabled}
            onChange={(event) => setSendEmail(event.target.checked)}
          />
          Also send email
        </label>

        {!emailEnabled && (
          <p>
            Email is disabled in your account settings. In-app reminders
            are still available.
          </p>
        )}

        {initialReminder?.send_email && !emailEnabled && (
          <p>Saving this form will turn off email for this reminder.</p>
        )}

        <p>Development emails are delivered to local Mailpit.</p>

        <div className="reminder-actions">
          <button type="submit">
            {isSubmitting ? "Saving..." : "Save reminder"}
          </button>
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </fieldset>

      {(validationError ?? errorMessage) && (
        <p role="alert">{validationError ?? errorMessage}</p>
      )}
    </form>
  );
}
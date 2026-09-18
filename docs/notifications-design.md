# Reminders and Notifications Design

## Scope

This document defines the intended behavior of the first version of
reminders, in-app notifications, and optional email delivery.

These rules describe functionality to be implemented. They do not imply
that the functionality is already available.

## Concepts

### Reminder

A reminder is a one-time scheduled action associated with one application.

A user can create multiple reminders for the same application.

Supported kinds:

- interview
- follow_up
- custom

The kind is a label. It does not automatically schedule, reschedule,
or cancel a reminder.

### Notification

A notification is a message created inside the application when a reminder
becomes due.

Each reminder can create at most one notification.

Reading a notification does not change the reminder or application status.

### EmailDelivery

An email delivery records the attempt to send a notification by email.

Email delivery is separate from notification creation. An email delivery
failure must not remove the in-app notification.

## Ownership and Access

Users can only access reminders, notifications, and email preferences
that belong to them.

The backend obtains the user ID from authentication, not from a
user-supplied owner field.

Creating a reminder requires ownership of the associated application.

Requests for another user's application, reminder, or notification
return 404 without exposing its contents.

## Scheduling and Time

The user explicitly selects the reminder date and time.

Creating a reminder or changing its scheduled time requires a future time.
The backend validates this using the server's current time.

The frontend interprets the selected date and time in the user's local
time zone and sends an ISO 8601 timestamp with an explicit UTC offset.

The backend stores absolute timestamps in UTC.

The interface displays timestamps in the user's local time zone.

The current application model has no interview date field. Changing an
application's status to interview does not schedule a reminder.

## Reminder States

A reminder has one of the following states:

- scheduled
- fired
- cancelled

A new reminder starts as scheduled.

Allowed transitions:

- scheduled to fired
- scheduled to cancelled

Only scheduled reminders can be edited or rescheduled.

Editing a fired or cancelled reminder returns 409.

A fired reminder cannot be cancelled. The API returns 409 because its
notification has already been created.

Cancelling an already cancelled reminder succeeds without additional
effects.

A cancelled reminder must not create a notification.

To schedule another action after a reminder has fired or been cancelled,
the user creates a new reminder.

Changing the application status does not automatically cancel reminders,
including transitions to offer or rejected.

## Processing Due Reminders

A scheduled reminder becomes eligible for processing when its scheduled
time is less than or equal to the current server time.

Processing creates an in-app notification and marks the reminder as
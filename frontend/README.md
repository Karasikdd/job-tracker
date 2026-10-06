# Job Tracker Frontend

React and TypeScript interface for Job Tracker.

## Features

- Registration and login
- Application search, filtering and editing
- Status history and statistics
- Reminder creation, editing and cancellation
- Notifications and unread counter
- Email notification preferences

## Development

Requires Node.js 24 and npm.

Start the backend using the instructions in the [project README](../README.md).

From this directory:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

The Vite development server forwards `/api` requests to
http://127.0.0.1:8000.

## Checks

```bash
npm run lint
npm run build
```

## Authentication

The frontend stores the access token in `sessionStorage` and validates it
through `/users/me` after a page reload. Users must sign in again when the
token expires.

## Production

`npm run build` writes the frontend assets to `dist/`.

A production deployment must serve the frontend routes and forward `/api`
requests to the backend. The development proxy is configured in
`vite.config.ts`.
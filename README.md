# Job Tracker API

[![Tests](https://github.com/Karasikdd/job-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/Karasikdd/job-tracker/actions/workflows/tests.yml)

A backend application for tracking job applications, their current statuses,
notes, and status history.

The project demonstrates the development of a REST API with authentication,
relational database persistence, database migrations, automated tests,
Docker containers, and continuous integration.

## Features

- User registration and login
- Password hashing
- JWT-based authentication
- Creation of job applications
- Viewing a user's own applications
- Partial application updates
- Application deletion
- Filtering by application status
- Search by company or position
- Pagination with `limit` and `offset`
- Application status history
- Statistics grouped by status
- Isolation of data between users
- Automatic API documentation
- PostgreSQL persistence
- Alembic database migrations
- Automated tests with pytest
- Docker-based local environment
- Continuous integration with GitHub Actions

## Technology Stack

- Python 3.13
- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic
- PyJWT
- pwdlib with Argon2
- pytest
- Docker and Docker Compose
- GitHub Actions

## Project Structure

```text
job-tracker/
├── .github/
│   └── workflows/
│       └── tests.yml
├── alembic/
│   └── versions/
├── app/
│   ├── routers/
│   │   ├── applications.py
│   │   └── auth.py
│   ├── config.py
│   ├── database.py
│   ├── enums.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── security.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Requirements

For the Docker setup:

- Git
- Docker Desktop
- Docker Compose

For development directly on the host machine:

- Python 3.13
- Git
- Docker Desktop for PostgreSQL

## Clone the Repository

```bash
git clone https://github.com/Karasikdd/job-tracker.git
cd job-tracker
```

## Environment Configuration

Create a local environment file from the provided example:

```bash
cp .env.example .env
```

Generate a random secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value and replace `REPLACE_ME` in `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://jobtracker:local_dev_password@127.0.0.1:5433/jobtracker
TEST_DATABASE_URL=postgresql+psycopg://jobtracker:local_dev_password@127.0.0.1:5434/jobtracker_test
SECRET_KEY=PASTE_THE_GENERATED_VALUE_HERE
```

The `.env` file contains local configuration and must not be committed.

## Run with Docker

Build the API image:

```bash
docker compose build api
```

Start PostgreSQL:

```bash
docker compose up -d db
```

Check the database status:

```bash
docker compose ps
```

Wait until the `db` service is marked as `healthy`.

Apply database migrations:

```bash
docker compose run --rm --no-deps api alembic upgrade head
```

Start the API:

```bash
docker compose up -d api
```

Check the running services:

```bash
docker compose ps
```

View API logs:

```bash
docker compose logs api
```

The application is now available at:

- Health check: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

To stop the application:

```bash
docker compose stop
```

## Test the API Manually

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

### 1. Register a User

Open:

```text
POST /auth/register
```

Use example data:

```json
{
  "email": "owner@example.com",
  "password": "Example-password-123"
}
```

A successful request returns status code `201`.

### 2. Log In

Open:

```text
POST /auth/login
```

Send the same credentials:

```json
{
  "email": "owner@example.com",
  "password": "Example-password-123"
}
```

Copy the returned `access_token`.

### 3. Authorize Swagger UI

Click `Authorize` at the top of Swagger UI.

Paste only the token value into the HTTP Bearer field. Do not add quotation
marks. Swagger UI adds the `Bearer` prefix automatically.

### 4. Create a Job Application

Open:

```text
POST /applications
```

Use:

```json
{
  "company": "Example GmbH",
  "position": "Werkstudent Backend",
  "status": "saved",
  "location": "Munich",
  "notes": "Application prepared"
}
```

Save the returned application `id`.

### 5. Update the Status

Open:

```text
PATCH /applications/{application_id}
```

Enter the application ID and use:

```json
{
  "status": "applied",
  "notes": "CV sent"
}
```

### 6. View Status History

Open:

```text
GET /applications/{application_id}/history
```

The response should contain the transition from `saved` to `applied`.

### 7. View Statistics

Open:

```text
GET /stats
```

The response contains the total number of applications and their distribution
by status.

## Local Development

Create a virtual environment:

```bash
python3.13 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create the local configuration:

```bash
cp .env.example .env
```

Generate a secret key and place it in `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Start the development database:

```bash
docker compose up -d db
```

Wait until the database is healthy:

```bash
docker compose ps
```

Apply migrations:

```bash
alembic upgrade head
```

Start the development server:

```bash
fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Stop the development server with `Control+C`.

## Run Tests

Start the separate test database:

```bash
docker compose --profile test up -d testdb
```

Check its status:

```bash
docker compose --profile test ps
```

Apply migrations to the test database:

```bash
DATABASE_URL=postgresql+psycopg://jobtracker:local_dev_password@127.0.0.1:5434/jobtracker_test alembic upgrade head
```

Run all tests:

```bash
python -m pytest -q
```

Run one test:

```bash
python -m pytest tests/test_api.py::test_filters_pagination_and_stats -q
```

The test database is separate from the normal development database.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check application health |
| `POST` | `/auth/register` | Register a user |
| `POST` | `/auth/login` | Log in and obtain a token |
| `GET` | `/users/me` | Get the authenticated user |
| `POST` | `/applications` | Create an application |
| `GET` | `/applications` | List and filter applications |
| `GET` | `/applications/{id}` | Get one application |
| `PATCH` | `/applications/{id}` | Update an application |
| `DELETE` | `/applications/{id}` | Delete an application |
| `GET` | `/applications/{id}/history` | Get status history |
| `GET` | `/stats` | Get application statistics |

All application, history, and statistics endpoints use the authenticated user's
data. A user cannot access another user's applications.

## Application Statuses

The following statuses are supported:

- `saved`
- `applied`
- `interview`
- `offer`
- `rejected`

## Continuous Integration

GitHub Actions runs automatically on every push and pull request.

The workflow:

1. Starts PostgreSQL 17.
2. Installs Python 3.13.
3. Installs project dependencies.
4. Applies Alembic migrations.
5. Runs the pytest test suite.

The workflow configuration is located at:

```text
.github/workflows/tests.yml
```

## Current Limitations

- Access tokens expire after 30 minutes.
- Refresh tokens are not implemented.
- Tokens cannot currently be revoked before expiration.
- Email confirmation is not implemented.
- Password recovery is not implemented.
- Status transitions are not restricted.
- The project does not have a frontend.
- Automatic job import is not implemented.
- The API is not currently deployed publicly.

## Possible Future Improvements

- Add refresh tokens and explicit logout
- Add a React frontend
- Add reminders for unanswered applications
- Add application deadlines and interviews
- Add CSV import and export
- Deploy the API with HTTPS

## License

This project is currently provided for educational and portfolio purposes.
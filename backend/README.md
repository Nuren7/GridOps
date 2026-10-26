# GridOps Backend

The GridOps backend is a FastAPI service for factory device metadata and sensor
time-series data. SQLAlchemy stores users, devices, and sensor metadata in
PostgreSQL or MySQL. MongoDB stores incoming sensor readings.

## Requirements

- Python 3.12 or later
- A PostgreSQL or MySQL database
- A MongoDB database (MongoDB 5.0 or later for time-series summaries)

Configure these variables in `backend/.env` for local development:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL or MySQL |
| `MONGO_URI` | MongoDB URI, including the database name |
| `JWT_SECRET_KEY` | Secret used to sign JWTs; use at least 32 characters |
| `JWT_ALGORITHM` | JWT algorithm; defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime; defaults to 30 |
| `CORS_ORIGINS` | Optional JSON array of allowed browser origins; defaults to `["*"]` |

For example, use `postgresql://...` or `mysql://...` in `DATABASE_URL`. The
application selects the corresponding asynchronous SQLAlchemy driver. The
MongoDB URI must include a database name.

## Run locally

From the `backend` directory:

```sh
python -m venv .venv
# Activate the virtual environment using your operating system's command.
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health check is available at `/health`, and the OpenAPI UI is available at
`/docs`.

Create the first login user with a password prompt:

```sh
python -m app.create_user --username operator --role operator
```

## API

- `POST /api/v1/auth/token`: OAuth2 password-form login; returns a bearer JWT.
- `POST /api/v1/sensors/data`: stores a timestamped JSON sensor reading in
  MongoDB. At least one numeric measurement is required.
- `GET /api/v1/sensors/summary`: combines SQL sensor/device metadata with
  MongoDB latest readings and the last 60 minutes of temperature/humidity
  aggregates.

Sensor metadata and devices are managed in the SQL database. Sensor reading
payloads can include `sensor_id`, an ISO-8601 `timestamp`, one or more numeric
measurements (`temperature`, `humidity`, `vibration`, or `pressure`), an
optional status, and additional JSON fields.

## Checks

```sh
ruff check app tests
pytest
```

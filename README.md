# FastAPI Boilerplate

A production-ready FastAPI boilerplate with best practices and common configurations.

## Features

- 🚀 **FastAPI** - Modern, fast web framework for building APIs
- 🐘 **PostgreSQL** - Async database support with SQLAlchemy 2.0
- 🔐 **JWT Authentication** - Secure authentication with jose
- 📦 **Docker** - Containerized development and deployment
- 🧪 **Testing** - Pytest with async support and coverage
- 📝 **Alembic** - Database migrations
- 🎨 **Code Quality** - Black, isort, flake8, mypy
- 📚 **API Documentation** - Auto-generated OpenAPI/Swagger docs

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── items.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── item.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── item.py
│   │   └── user.py
│   └── main.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── test_main.py
│   ├── test_users.py
│   └── test_items.py
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (optional)
- PostgreSQL (if not using Docker)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fastapi-app
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   make run
   ```

6. **Access the API**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Development

1. **Build and start containers**
   ```bash
   make docker-up
   ```

2. **View logs**
   ```bash
   make docker-logs
   ```

3. **Stop containers**
   ```bash
   make docker-down
   ```

## Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install production dependencies |
| `make dev` | Install development dependencies |
| `make run` | Run the FastAPI server locally |
| `make test` | Run tests with coverage |
| `make lint` | Run linting checks |
| `make format` | Format code with black and isort |
| `make clean` | Clean up cache files |
| `make docker-build` | Build Docker image |
| `make docker-up` | Start Docker containers |
| `make docker-down` | Stop Docker containers |
| `make migrate` | Run database migrations |

## API Endpoints

### Root
- `GET /` - Welcome message
- `GET /health` - Health check

### Users
- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/{user_id}` - Get a user
- `POST /api/v1/users/` - Create a user
- `PUT /api/v1/users/{user_id}` - Update a user
- `DELETE /api/v1/users/{user_id}` - Delete a user

### Items
- `GET /api/v1/items/` - List all items
- `GET /api/v1/items/{item_id}` - Get an item
- `POST /api/v1/items/` - Create an item
- `PUT /api/v1/items/{item_id}` - Update an item
- `DELETE /api/v1/items/{item_id}` - Delete an item

## Database Migrations

```bash
# Create a new migration
make migrate-create

# Apply migrations
make migrate
```

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_main.py -v

# Run with coverage report
pytest --cov=app --cov-report=html
```

## Code Quality

```bash
# Format code
make format

# Run linting
make lint
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | FastAPI App |
| `DEBUG` | Debug mode | false |
| `DATABASE_URL` | Database connection URL | - |
| `SECRET_KEY` | JWT secret key | - |
| `ALLOWED_ORIGINS` | CORS allowed origins | localhost |

## License

MIT License

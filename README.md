# Matchmaking Backend

Astrological matchmaking API built with Django, MySQL, Redis, and Docker.

## Stack
- Python 3.11 / Django 4.2
- Django REST Framework + JWT auth
- MySQL 8.0
- Redis 7 (caching)
- Nginx (reverse proxy)
- Docker + Docker Compose

## Quick Start

### 1. Clone the repo
git clone <your-repo-url>
cd matchmaking

### 2. Set up environment
cp .env.example .env
# Edit .env and fill in your values

### 3. Start containers
docker-compose up --build -d

### 4. Run migrations
docker exec -it -w /app/matchmaking_project matchmaking_web python manage.py migrate

### 5. Create superuser
docker exec -it -w /app/matchmaking_project matchmaking_web python manage.py createsuperuser

### 6. Access
- API:     http://localhost/api/
- Swagger: http://localhost/swagger/
- Admin:   http://localhost/admin/

## API Endpoints

### Auth
POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/refresh/
POST   /api/auth/logout/
POST   /api/auth/change-password/

### Profile
GET    /api/profiles/me/
POST   /api/profiles/me/
PATCH  /api/profiles/me/
DELETE /api/profiles/me/

### Private Persons
GET    /api/private-persons/
POST   /api/private-persons/
GET    /api/private-persons/{id}/
PATCH  /api/private-persons/{id}/
DELETE /api/private-persons/{id}/

### Compatibility
POST   /api/compatibility/check/
GET    /api/compatibility/history/
GET    /api/compatibility/top_matches/

## Running Tests

### Mocked tests (no API key needed)
docker exec -it -w /app/matchmaking_project matchmaking_web python manage.py test matchmaking.tests -v 2

### Integration tests (requires running containers)
cd matchmaking_project
pytest

## Environment Variables

| Variable | Description |
|----------|-------------|
| SECRET_KEY | Django secret key |
| DEBUG | True/False |
| DB_NAME | MySQL database name |
| DB_USER | MySQL username |
| DB_PASSWORD | MySQL password |
| DB_ROOT_PASSWORD | MySQL root password |
| DB_HOST | MySQL host (use 'db' for Docker) |
| DB_PORT | MySQL port (default 3306) |
| REDIS_URL | Redis connection URL |
| ASTROLOGY_API_URL | Your astrology API base URL |
| ASTROLOGY_API_KEY | Your astrology API key |
| CORS_ALLOWED_ORIGINS | Comma-separated allowed origins |
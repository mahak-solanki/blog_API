# FastAPI Blog API

## Included
- User registration (`username`, `email`, `password`) and password hashing
- JWT access/refresh tokens
- Author, Post, and Comment database models
- Required posts/comments and health/readiness endpoints
- Basic HTML/CSS/JavaScript frontend
- PostgreSQL configuration through environment variables

## Run locally on Windows PowerShell

1. Install Python 3.11+ and PostgreSQL. Create a database named `blogAPI_db` and a database user, or use your own existing PostgreSQL credentials.
2. Open PowerShell in `backend`:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
3. Edit `backend/.env` and set `DATABASE_URL` to your actual PostgreSQL username/password/database. Replace `JWT_SECRET_KEY` with a long random secret.
4. Start API from the `backend` folder:
   ```powershell
   uvicorn app.main:app --reload
   ```
5. Open API docs: http://127.0.0.1:8000/docs
6. In another terminal, open `frontend` and run:
   ```powershell
   py -m http.server 5500
   ```
7. Open http://127.0.0.1:5500

## Endpoints
- `POST /api/register/`
- `POST /api/token/` (JSON: `{"email":"person@example.com","password":"your-password"}`)
- `POST /api/token/refresh/` (JSON: `{"refresh":"...refresh token..."}`)
- `GET /posts/`
- `POST /posts/` (Bearer access token required)
- `GET /posts/{post_id}/comments/`
- `POST /posts/{post_id}/comments/` (Bearer access token required)
- `GET /health/`
- `GET /readiness/`



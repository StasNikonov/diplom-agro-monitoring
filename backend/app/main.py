from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, fields, files, flights, tasks, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed initial admin user if the users table is empty of admins
    from app.database import SessionLocal
    from app.models import User
    from app.auth import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=hash_password("agro2026"),
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title="Agro Monitoring API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(fields.router)
app.include_router(flights.router)
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(users.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}

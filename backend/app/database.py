import os

from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine

from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
)


# =========================================================
# 1. .env 파일 위치
#
# database.py
# backend/app/database.py
#
# .env
# backend/.env
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


ENV_PATH = (
    BASE_DIR
    / ".env"
)


# =========================================================
# 2. .env 파일 읽기
# =========================================================

load_dotenv(
    ENV_PATH
)


# =========================================================
# 3. PostgreSQL 연결 주소 읽기
#
# 실제 비밀번호는 database.py에 존재하지 않는다.
#
# .env의 DATABASE_URL을 읽는다.
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


# =========================================================
# 4. DATABASE_URL이 없으면 서버 실행 중단
#
# 잘못된 설정으로 엉뚱한 DB에 연결되는 것을 방지
# =========================================================

if not DATABASE_URL:

    raise RuntimeError(
        "DATABASE_URL is not configured"
    )


# =========================================================
# 5. SQLAlchemy Engine
# =========================================================

engine = create_engine(
    DATABASE_URL
)


# =========================================================
# 6. DB Session
#
# expire_on_commit=False
#
# commit 후 응답을 만들기 위해
# 불필요하게 DB를 다시 조회하지 않는다.
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


# =========================================================
# 7. SQLAlchemy Base
# =========================================================

Base = declarative_base()


# =========================================================
# 8. FastAPI DB dependency
# =========================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()
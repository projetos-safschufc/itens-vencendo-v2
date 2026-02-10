"""
Base para modelos SQLAlchemy (se necessário para tabelas locais, ex: users).
Views e tabelas do schema gad_dlih_safs são acessadas via raw SQL ou text().
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

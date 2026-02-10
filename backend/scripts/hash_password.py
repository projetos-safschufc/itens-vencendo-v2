"""Gera hash bcrypt para senha (uso em DEMO_USERS). Uso: python -m scripts.hash_password"""
import getpass
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = getpass.getpass("Senha: ") or "admin123"
print(pwd_context.hash(password))

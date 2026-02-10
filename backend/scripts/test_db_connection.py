"""
Testa conexão ao banco powerbi com as credenciais do .env / .env.password.
Uso (a partir da pasta backend):
  python -m scripts.test_db_connection
  python -m scripts.test_db_connection "senha_para_testar"

Se passar uma senha como argumento, usa essa em vez do .env.password (para comparar).
"""
import sys
from pathlib import Path

# Garante que o backend está no path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import psycopg2
from app.config import get_settings


def main():
    settings = get_settings()
    # Senha: da linha de comando (para teste) ou do config
    if len(sys.argv) > 1:
        password = sys.argv[1]
        print("Usando senha passada pela linha de comando (comprimento =", len(password), ")")
    else:
        password = settings.db_password_connection
        print("Usando DB_PASSWORD do .env/.env.password como string (comprimento =", len(password), ")")
    if not password:
        print("ERRO: senha vazia. Verifique .env ou .env.password.")
        sys.exit(1)
    print("Conectando em", settings.db_host, ":", settings.db_port, "db=", settings.db_name, "user=", settings.db_user)
    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=password,
            connect_timeout=10,
        )
        conn.close()
        print("OK: conexão estabelecida.")
    except Exception as e:
        print("FALHA:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

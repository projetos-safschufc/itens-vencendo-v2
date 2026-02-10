"""
Constantes de negócio: listas fixas de almoxarifados UACE e ULOG.
Sempre filtrar por essas listas conforme regra de negócio.
"""
from typing import List

# Almoxarifados UACE (lista fixa – regra de negócio)
UACE_WAREHOUSES: List[str] = [
    "3-UACE HUWC - OPME",
    "4-UACE SATÉLITE - HUWC",
    "18-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE - ANEXO",
    "1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE HUWC",
    "36-UACE - MATERIAIS GERAIS - SATÉLITE HUWC",
    "50-UACE QUARENTENA",
    "3-UACE MEAC - SATÉLITE",
    "1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE MEAC",
    "2-(INATIVO) UACE SATÉLITE - MATERIAIS GERAIS MEAC",
    "16-CENTRAL DE CONSIGNADOS - UACE",
]

# Almoxarifados ULOG (lista fixa – regra de negócio)
ULOG_WAREHOUSES: List[str] = [
    "2-UNIDADE DE LOGÍSTICA",
    "34-UNIDADE DE LOGÍSTICA (ANEXO)",
]

# Única lista de almoxarifados considerados no sistema (ordem para exibição e filtros)
ALL_WAREHOUSES: List[str] = [
    "3-UACE HUWC - OPME",
    "4-UACE SATÉLITE - HUWC",
    "18-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE - ANEXO",
    "1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE HUWC",
    "36-UACE - MATERIAIS GERAIS - SATÉLITE HUWC",
    "2-UNIDADE DE LOGÍSTICA",
    "34-UNIDADE DE LOGÍSTICA (ANEXO)",
    "50-UACE QUARENTENA",
    "3-UACE MEAC - SATÉLITE",
    "1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE MEAC",
    "2-(INATIVO) UACE SATÉLITE - MATERIAIS GERAIS MEAC",
    "16-CENTRAL DE CONSIGNADOS - UACE",
]

# Set para lookup O(1)
UACE_SET = set(UACE_WAREHOUSES)
ULOG_SET = set(ULOG_WAREHOUSES)

# Movimento subtipo para perdas por validade
MOVIMENTO_SUBTIPO_PERDAS_VALIDADE = "PERDAS POR VALIDADE"

# Janela de validade em dias (estoque a vencer)
EXPIRY_WINDOW_DAYS = 180

# Meses para média de consumo (análise preditiva)
CONSUMPTION_AVG_MONTHS = 6

# Ano mínimo para dados de consumo
CONSUMPTION_MIN_YEAR = 2023

# Mapeamento profile_id (ctrl.users) -> role da API. Ajuste conforme tabela ctrl.profiles se existir.
PROFILE_ID_TO_ROLE = {
    1: "admin",
    2: "analyst",
    3: "read_only",
}
DEFAULT_ROLE = "read_only"

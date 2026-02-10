# Relatório / Tela: ANÁLISE PREDITIVA

## Objetivo
Unificar dados de **estoque** e **movimentação** para análise preditiva de validade de materiais, identificando risco de perda por vencimento, quantidade potencialmente perdida e impacto financeiro estimado. Toda a lógica de cálculo é feita **exclusivamente no código da aplicação**; o banco é utilizado **somente em modo leitura**.

## Restrições
- **Nenhuma** criação ou alteração de tabelas, views, índices ou outros objetos no banco.
- Aplicação com **permissão apenas de leitura** no PostgreSQL.
- Dados retornados do banco: apenas dados brutos e agregações mínimas necessárias.

---

## Base de Dados (somente leitura)

| Objeto | Uso |
|--------|-----|
| `gad_dlih_safs.v_df_estoque` | Estoque atual (por lote): material, lote, validade, quantidade, valor unitário/total, almoxarifado, grupo. |
| `gad_dlih_safs.v_df_movimento` | Movimentações para cálculo de consumo (apenas movimentos negativos, últimos 6 meses). |

### Relacionamento
O vínculo entre estoque e movimento é feito pelo **código do material antes do "-"**:
- **Estoque:** `SPLIT_PART(nome_do_material, '-', 1)`
- **Movimento:** `SPLIT_PART(mat_cod_antigo, '-', 1)`

---

## Regras de consolidação

1. **Unidade de análise:** cada **LOTE** (material + lote + validade + almoxarifado).
2. **Consumo:** apenas **movimentos negativos** (saídas) contam como consumo.
3. **Período de consumo:** soma dos **últimos 6 meses** (calendário).
4. **Média diária de consumo:** `consumo_total_6_meses / 180` (dias).
5. **Dados do banco:** somente leitura; agregações mínimas (ex.: soma de consumo por material nos 6 meses).

---

## Campos obtidos do banco (queries read-only)

- hospital (se existir na view)
- almoxarifado
- grupo do material (ex.: `grupo_de_material`)
- material (nome padronizado, ex.: `nome_do_material`)
- lote
- validade
- quantidade disponível (ex.: `saldo`)
- valor unitário
- valor total (quantidade × valor unitário)
- consumo total dos últimos 6 meses (soma de quantidades em valor absoluto dos movimentos negativos, por código de material)

---

## Cálculos na aplicação

| Cálculo | Fórmula |
|---------|--------|
| Dias para vencer | `validade - data_atual` (em dias) |
| Consumo médio diário | `consumo_6_meses / 180` |
| Dias que o estoque cobre | `quantidade_disponível / consumo_médio_diário` (se consumo > 0) |
| Classificação de risco | Ver tabela abaixo |
| Valor estimado de perda | Ver seção "Cálculo de perda estimada" |

### Classificação de risco (regra de negócio)

| Risco | Condição |
|-------|----------|
| **SEM CONSUMO** | Consumo médio diário = 0 |
| **ALTO RISCO** | Estoque **não** cobre os dias até o vencimento (dias de estoque < dias para vencer) |
| **MÉDIO RISCO** | Estoque cobre até **1,5×** os dias até o vencimento |
| **BAIXO RISCO** | Estoque cobre **mais** que 1,5× os dias até o vencimento |

### Cálculo de perda estimada

- **Sem consumo:** considerar **todo o valor do lote** como perda potencial.
- **Com consumo:** sobra estimada no vencimento × valor unitário.  
  - Sobra = `max(0, quantidade_disponível - consumo_médio_diário × dias_para_vencer)`  
  - Perda estimada = sobra × valor unitário  
- **Restrição:** não permitir valores negativos (perda mínima = 0).

---

## Exibição na tela

### Tabela principal (colunas)
- Material  
- Grupo  
- Lote  
- Validade  
- Dias para vencer  
- Quantidade disponível  
- Consumo médio diário  
- Risco de perda (destacado visualmente)  
- Valor estimado de perda (R$)

### Indicadores (cards / resumos)
1. **Valor total em ALTO RISCO** – soma do valor estimado de perda dos lotes classificados como ALTO RISCO.
2. **Quantidade de itens vencendo em até 30 dias** – contagem de lotes com dias para vencer ≤ 30.
3. **Quantidade de materiais sem consumo nos últimos 6 meses** – contagem de materiais (código) com consumo 6m = 0.
4. **Top 10 materiais com maior valor estimado de perda** – agregado por material (soma das perdas por lote), ordenado decrescente, 10 primeiros.

---

## Média dos últimos 6 meses (referência)

- **Cálculo:** média aritmética dos **totais mensais** de consumo dos **6 meses mais recentes** com movimento na view `v_df_movimento` (a partir de 2023).
- **Implementação típica:** subconsulta com `GROUP BY mesano`, `ORDER BY mesano DESC`, `LIMIT 6`; depois `AVG(consumo_mensal)`.
- Na análise preditiva, o consumo usado é a **soma** dos últimos 6 meses (não a média mensal), e a média diária = soma / 180.

---

## Fluxo técnico resumido

1. **Repository:** duas consultas read-only: (a) estoque por lote (v_df_estoque) com filtros; (b) consumo total últimos 6 meses por material (v_df_movimento, apenas quantidades negativas em valor absoluto).
2. **Service:** para cada linha de estoque, obter consumo do material; calcular dias para vencer, consumo médio diário, dias cobertos, risco e perda estimada; montar indicadores (totais e top 10).
3. **API:** expor tabela enriquecida + indicadores; exportação Excel/CSV com as mesmas colunas da tela.
4. **Frontend:** filtros (setor, almoxarifado, grupo, material); 4 cards; tabela com destaque visual para risco; botões de exportação.

Este relatório serve como especificação da tela **ANÁLISE PREDITIVA** e garante lógica clara, auditável e explicável para gestão, sem criar objetos no banco e sem permissões de escrita.

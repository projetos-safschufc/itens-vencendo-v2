# Diagnóstico: coluna MÉDIA DE CONSUMO (Consumo médio/dia) zerada

## Fluxo dos dados

1. **Backend – repositório** (`predictive_repository.get_predictive_raw`):
   - Busca estoque em `gad_dlih_safs.v_df_estoque` (janela 180 dias).
   - Busca consumo em `gad_dlih_safs.v_df_movimento` com os critérios:
     - **movimento_cd = 'RM'**
     - **qtde_orig > 0**
     - **mesano >= 2023-01** e mesano nos últimos 6 meses de calendário
     - **almoxarifado** na lista fixa (ALL_WAREHOUSES)
   - Join por código do material: `TRIM(SPLIT_PART(nome_do_material, '-', 1))` = `TRIM(SPLIT_PART(mat_cod_antigo, '-', 1))`.
   - Consumo = soma de `qtde_orig` (apenas movimentos RM com qtde_orig > 0).

2. **Backend – serviço** (`predictive_service.get_predictive_response`):
   - Para cada linha de estoque, lê `consumption_map.get(material_code, 0.0)`.
   - Calcula `avg_daily_consumption = consumption_6m / 180` e preenche `PredictiveRow.avg_daily_consumption`.

3. **Frontend** (`PredictivePage`):
   - Exibe `r.avg_daily_consumption` na coluna "Consumo médio/dia".

---

## Causas prováveis da não exibição (valores zerados)

### 1. **View de movimento em outro banco ou vazia**
- A API usa **uma única sessão** (banco de analytics/dw). Estoque e consumo são lidos no **mesmo** banco.
- Se `v_df_movimento` existir apenas no SAFS (ou em outro banco), no analytics a view pode não existir ou estar vazia → consumo zerado.
- **O que fazer:** Confirmar se `gad_dlih_safs.v_df_movimento` existe no banco **analytics** (o mesmo de `v_df_estoque`) e se tem linhas na janela dos últimos 6 meses.

### 2. **Query de consumo falhando (nome de coluna ou SQL)**
- A query usa: `data_movimento`, `quantidade`, `mat_cod_antigo`.
- Se a view tiver nomes diferentes (ex.: `data`, `qtd`, `cod_material`), a query quebra, o `except` é acionado e o mapa de consumo fica vazio.
- **O que fazer:** Ver nos logs se aparece `predictive_consumption_neg_failed` ou `predictive_consumption_pos_failed` (e a mensagem de erro). Conferir na view os nomes reais das colunas e ajustar o SQL se necessário.

### 3. **Código do material não casando (join)**
- Estoque: `TRIM(SPLIT_PART(e.nome_do_material, '-', 1))`.
- Movimento: `TRIM(SPLIT_PART(m.mat_cod_antigo, '-', 1))`.
- Se em uma das views o código vier com formato diferente (espaços, hífen, zeros à esquerda), o join não acha par e o consumo fica 0 para esse material.
- **O que fazer:** Ver no log `predictive_consumption_diagnostic`: `stock_codes_sample` e `consumption_keys_sample`. Se os códigos forem diferentes, normalizar (ex.: padding de zeros, ou mesmo expressão nas duas views).

### 4. **Convenção de sinal da quantidade**
- Hoje: primeiro soma **quantidade &lt; 0**; se o total for zero, soma **quantidade &gt; 0**.
- Se no seu sistema “saída” for registrada com outro critério (ex.: tipo de movimento ou coluna específica), pode ser que nem negativos nem positivos sozinhos representem só consumo.
- **O que fazer:** Verificar na view se existe coluna de tipo/natureza (entrada/saída) e, se existir, filtrar consumo só por esse tipo e ajustar a query.

### 5. **Janela de datas sem movimento**
- Janela usada: `data_movimento >= date_trunc('month', CURRENT_DATE) - INTERVAL '6 months'` e `&lt; date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'`, com `EXTRACT(YEAR FROM m.data_movimento) >= 2023`.
- Se não houver movimentos nesse intervalo, a soma será 0.
- **O que fazer:** Rodar no banco algo como:
  - `SELECT COUNT(*), MIN(data_movimento), MAX(data_movimento) FROM gad_dlih_safs.v_df_movimento;`
  - E, para um material que está no estoque, ver se há linhas nessa janela.

---

## Logs de diagnóstico (já no código)

Após as alterações no repositório, o backend passa a registrar:

- **`predictive_consumption_neg_failed`** – falha na query de consumo por quantidade negativa (ex.: coluna inexistente).
- **`predictive_consumption_pos_failed`** – falha no fallback por quantidade positiva.
- **`predictive_consumption_used_positive`** – quando o fallback por positivos foi usado (rows, total, materials).
- **`predictive_consumption_diagnostic`** – a cada chamada:
  - `consumption_rows_neg`: quantidade de linhas retornadas na query de negativos.
  - `consumption_total_neg`: soma total de consumo (negativos).
  - `consumption_map_size`: quantos materiais têm consumo no mapa.
  - `stock_rows`: quantas linhas de estoque.
  - `stock_codes_sample` / `consumption_keys_sample`: amostra de códigos de estoque e de consumo (para comparar formato).
  - `materials_with_consumption`: quantos códigos de estoque têm consumo &gt; 0 no mapa.

Com isso dá para saber se:
- a query de consumo está retornando linhas;
- os códigos de estoque e movimento batem;
- o problema é banco, coluna, join ou janela de datas.

---

## Resumo de verificação rápida

1. Ver logs da API ao abrir/atualizar a tela de Análise Preditiva (buscar por `predictive_consumption_`).
2. Confirmar no banco **analytics** se `gad_dlih_safs.v_df_movimento` existe e tem dados nos últimos 6 meses.
3. Confirmar na view os nomes das colunas: `data_movimento`, `quantidade`, `mat_cod_antigo`.
4. Comparar no log `stock_codes_sample` e `consumption_keys_sample` para ver se o formato do código do material é o mesmo nas duas fontes.

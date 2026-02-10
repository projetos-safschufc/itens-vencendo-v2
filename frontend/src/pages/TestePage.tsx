import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { testeApi } from '../api/endpoints'

export function TestePage() {
  const [materialFilter, setMaterialFilter] = useState('')

  const filters = { material: materialFilter.trim() || undefined }
  const { data, isLoading, error } = useQuery({
    queryKey: ['teste', filters],
    queryFn: () => testeApi.list(filters).then((r) => r.data),
  })

  type TesteRowType = {
    material?: string
    media_ultimos_6_meses?: number
    consumo_m_6?: number
    consumo_m_5?: number
    consumo_m_4?: number
    consumo_m_3?: number
    consumo_m_2?: number
    consumo_m_1?: number
    consumo_mes_atual?: number
  }
  type TesteApiResponse = {
    data: TesteRowType[]
    total_rows: number
    month_labels?: string[]
  }

  const response = data as TesteApiResponse | undefined
  const rows = response?.data ?? []
  const monthLabels: string[] = response?.month_labels ?? []

  const consumptionCols: (keyof TesteRowType)[] = [
    'consumo_m_6', 'consumo_m_5', 'consumo_m_4', 'consumo_m_3',
    'consumo_m_2', 'consumo_m_1', 'consumo_mes_atual',
  ]

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Histórico de Consumo dos Últimos 6 Meses por Material com a Média de Consumo
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Média dos últimos 6 meses de consumo por material (v_df_movimento: RM, qtde_orig &gt; 0, mesano ≥ 2023-01). O mês atual não entra no cálculo.
      </Typography>

      <TextField
        fullWidth
        size="small"
        label="Código (material)"
        value={materialFilter}
        onChange={(e) => setMaterialFilter(e.target.value)}
        placeholder="Buscar por código ou descrição"
        sx={{ maxWidth: 400, mb: 2, display: 'block' }}
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>Erro ao carregar dados.</Alert>}

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
      ) : (
        <Card>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Tabela: Material × Média últimos 6 meses</Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Material</TableCell>
                    {monthLabels.map((label, j) => (
                      <TableCell key={j} align="right">{label}</TableCell>
                    ))}
                    <TableCell align="right">Média últimos 6 meses</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((r: TesteRowType, i: number) => (
                    <TableRow key={i}>
                      <TableCell>{r.material ?? '-'}</TableCell>
                      {consumptionCols.map((col) => (
                        <TableCell key={col} align="right">
                          {r[col] != null && r[col] !== undefined
                            ? Number(r[col]).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                            : '—'}
                        </TableCell>
                      ))}
                      <TableCell align="right">
                        {Number(r.media_ultimos_6_meses ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            {rows.length === 0 && (
              <Typography color="text.secondary" sx={{ py: 2 }}>Nenhum registro de consumo para o material "{materialFilter}" encontrado nos últimos 6 meses.</Typography>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

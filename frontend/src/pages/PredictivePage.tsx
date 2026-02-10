import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  TextField,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Collapse,
  Chip,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import FilterListIcon from '@mui/icons-material/FilterList'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardApi, predictiveApi } from '../api/endpoints'

function formatValidity(iso?: string | null): string {
  if (!iso) return '-'
  const s = String(iso).split('T')[0]
  if (s.length !== 10) return s
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

type RiskKey = 'ALTO RISCO' | 'MÉDIO RISCO' | 'BAIXO RISCO' | 'SEM CONSUMO'

function RiskChip({ risk }: { risk: string }) {
  const colorMap: Record<RiskKey, 'error' | 'warning' | 'success' | 'default'> = {
    'ALTO RISCO': 'error',
    'MÉDIO RISCO': 'warning',
    'BAIXO RISCO': 'success',
    'SEM CONSUMO': 'default',
  }
  const color = colorMap[risk as RiskKey] ?? 'default'
  return <Chip size="small" label={risk} color={color} sx={{ fontWeight: 600 }} />
}

type Row = {
  material_name?: string
  material_code?: string
  material_group?: string
  warehouse?: string
  lote?: string
  validity?: string
  days_until_expiry?: number | null
  quantity?: number
  unit_value?: number
  total_value?: number
  avg_monthly_consumption?: number
  last_consumption_mesano?: string | null
  qtde_ultimo_consumo?: number | null
  risk?: string
  predicted_loss_quantity?: number
  estimated_loss?: number
}

export function PredictivePage() {
  const [filtersOpen, setFiltersOpen] = useState(true)
  const [sector, setSector] = useState('')
  const [warehouse, setWarehouse] = useState('')
  const [materialGroup, setMaterialGroup] = useState('')
  const [materialSearch, setMaterialSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [applied, setApplied] = useState(false)
  const queryClient = useQueryClient()

  const today = new Date()
  const asOfDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const filters = {
    sector: sector || undefined,
    warehouse: warehouse || undefined,
    material_group: materialGroup || undefined,
    material_search: materialSearch || undefined,
    risk: riskFilter || undefined,
    as_of_date: asOfDate,
  }

  const { data: filterOptions } = useQuery({
    queryKey: ['predictive', 'filter-options', sector || ''],
    queryFn: () => dashboardApi.filterOptions(sector ? { sector } : undefined).then((r: { data: { almoxarifados?: string[]; grupos_material?: string[] } }) => r.data),
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['predictive', filters],
    queryFn: () => predictiveApi.query(filters).then((r) => r.data),
    enabled: applied,
  })

  const exportExcel = useMutation({
    mutationFn: () => predictiveApi.exportExcel(filters),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'analise-preditiva.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const exportCsv = useMutation({
    mutationFn: () => predictiveApi.exportCsv(filters),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'analise-preditiva.csv'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const exportPdf = useMutation({
    mutationFn: () => predictiveApi.exportPdf(filters),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'analise-preditiva.pdf'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const rows: Row[] = data?.data ?? []
  const indicators = data?.indicators

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Análise preditiva
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Estoque a vencer (180 dias) por lote + consumo últimos 6 meses (apenas saídas). Risco de perda e valor estimado calculados na aplicação.
      </Typography>

      <Box sx={{ mb: 2 }}>
        <Button startIcon={<FilterListIcon />} onClick={() => setFiltersOpen((o) => !o)}>
          {filtersOpen ? 'Ocultar filtros' : 'Mostrar filtros'}
        </Button>
        <Collapse in={filtersOpen}>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={8} sm={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Setor</InputLabel>
                <Select value={sector} label="Setor" onChange={(e) => { setSector(e.target.value); setWarehouse(''); setMaterialGroup(''); }}>
                  <MenuItem value="">Todos</MenuItem>
                  <MenuItem value="UACE">UACE</MenuItem>
                  <MenuItem value="ULOG">ULOG</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={8} sm={6} md={2.5}>
              <FormControl fullWidth size="small">
                <InputLabel id="predictive-almoxarifado-label" shrink>Almoxarifado</InputLabel>
                <Select
                  labelId="predictive-almoxarifado-label"
                  value={warehouse}
                  label="Almoxarifado"
                  onChange={(e) => setWarehouse(e.target.value)}
                  displayEmpty
                >
                  <MenuItem value="">Todos</MenuItem>
                  {(filterOptions?.almoxarifados ?? []).map((label: string) => (
                    <MenuItem key={label} value={label}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={8} sm={6} md={2.5}>
              <FormControl fullWidth size="small">
                <InputLabel id="predictive-grupo-material-label" shrink>Grupo material</InputLabel>
                <Select
                  labelId="predictive-grupo-material-label"
                  value={materialGroup}
                  label="Grupo material"
                  onChange={(e) => setMaterialGroup(e.target.value)}
                  displayEmpty
                >
                  <MenuItem value="">Todos</MenuItem>
                  {(filterOptions?.grupos_material ?? []).map((label: string) => (
                    <MenuItem key={label} value={label}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={8} sm={6} md={2}>
              <TextField fullWidth size="small" label="Buscar material" value={materialSearch} onChange={(e) => setMaterialSearch(e.target.value)} />
            </Grid>
            <Grid item xs={10} sm={2.5} md={1}>
              <FormControl fullWidth size="small">
                <InputLabel id="filter-risco-label">Risco de Perda</InputLabel>
                <Select
                  labelId="filter-risco-label"
                  value={riskFilter}
                  label="Risco de Perda"
                  onChange={(e) => setRiskFilter(e.target.value)}
                >
                  <MenuItem value="">Todos</MenuItem>
                  <MenuItem value="ALTO RISCO">ALTO RISCO</MenuItem>
                  <MenuItem value="MÉDIO RISCO">MÉDIO RISCO</MenuItem>
                  <MenuItem value="BAIXO RISCO">BAIXO RISCO</MenuItem>
                  <MenuItem value="SEM CONSUMO">SEM CONSUMO</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={8} sm={6} md={2}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={() => { setApplied(true); queryClient.invalidateQueries({ queryKey: ['predictive'] }); refetch(); }}
              >
                Aplicar
              </Button>
            </Grid>
          </Grid>
        </Collapse>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>Erro ao carregar dados.</Alert>}

      {!applied ? (
        <Alert severity="info">Defina os filtros e clique em Aplicar para carregar a análise preditiva.</Alert>
      ) : isLoading ? (
        <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined" sx={{ borderColor: 'error.main', bgcolor: 'action.hover' }}>
                <CardContent>
                  <Typography color="text.secondary" variant="body2">Valor total est. perda (R$)</Typography>
                  <Typography variant="h6" color="error.main">
                    R$ {Number(indicators?.total_high_risk_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="body2">Itens vencendo em até 30 dias</Typography>
                  <Typography variant="h6">{indicators?.count_expiring_30d ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="body2">Materiais sem consumo (6 meses)</Typography>
                  <Typography variant="h6">{indicators?.count_no_consumption ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="body2">Estimativa Percentual de Perda</Typography>
                  <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 600 }}>
                    {Number(indicators?.loss_percentage_180d ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% do estoque que vence em até 180 dias corre o risco de perda
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mb: 2 }} alignItems="center">
            <Grid item xs={12} sm={6} md={4}>
              <Button startIcon={<FileDownloadIcon />} variant="outlined" fullWidth onClick={() => exportExcel.mutate()} disabled={exportExcel.isPending}>
                Exportar Excel
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Button startIcon={<FileDownloadIcon />} variant="outlined" fullWidth onClick={() => exportCsv.mutate()} disabled={exportCsv.isPending}>
                Exportar CSV
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Button startIcon={<FileDownloadIcon />} variant="outlined" fullWidth onClick={() => exportPdf.mutate()} disabled={exportPdf.isPending}>
                Exportar PDF
              </Button>
            </Grid>
          </Grid>

          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Tabela: estoque por lote + risco e perda estimada</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Material</TableCell>
                      <TableCell>Grupo</TableCell>
                      <TableCell>Almoxarifado</TableCell>
                      <TableCell>Lote</TableCell>
                      <TableCell>Validade</TableCell>
                      <TableCell align="right">Dias para vencer</TableCell>
                      <TableCell align="right">Qtd. disponível</TableCell>
                      <TableCell align="right">Valor unit.</TableCell>
                      <TableCell align="right">Valor Total</TableCell>
                      <TableCell align="right">Consumo médio/ último 6 meses</TableCell>
                      <TableCell align="right">Mes/ano último consumo</TableCell>
                      <TableCell align="right">Qtde último consumo</TableCell>
                      <TableCell>Risco de perda</TableCell>
                      <TableCell align="right">Previsão de Perda</TableCell>
                      <TableCell align="right">Valor est. perda (R$)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r: Row, i: number) => (
                      <TableRow key={i}>
                        <TableCell>{r.material_name ?? r.material_code ?? '-'}</TableCell>
                        <TableCell>{r.material_group ?? '-'}</TableCell>
                        <TableCell>{r.warehouse ?? '-'}</TableCell>
                        <TableCell>{r.lote ?? '-'}</TableCell>
                        <TableCell>{formatValidity(r.validity)}</TableCell>
                        <TableCell align="right">{r.days_until_expiry != null ? r.days_until_expiry : '-'}</TableCell>
                        <TableCell align="right">{Number(r.quantity ?? 0).toLocaleString('pt-BR')}</TableCell>
                        <TableCell align="right">R$ {Number(r.unit_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell align="right">R$ {Number(r.total_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell align="right">{Number(r.avg_monthly_consumption ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</TableCell>
                        <TableCell align="right">{r.last_consumption_mesano ?? '-'}</TableCell>
                        <TableCell align="right">{r.qtde_ultimo_consumo != null ? Number(r.qtde_ultimo_consumo).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '-'}</TableCell>
                        <TableCell><RiskChip risk={r.risk ?? 'BAIXO RISCO'} /></TableCell>
                        <TableCell align="right">{Number(r.predicted_loss_quantity ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}</TableCell>
                        <TableCell align="right">R$ {Number(r.estimated_loss ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              {rows.length === 0 && (
                <Typography color="text.secondary" sx={{ py: 2 }}>Nenhum registro para os filtros aplicados.</Typography>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  )
}

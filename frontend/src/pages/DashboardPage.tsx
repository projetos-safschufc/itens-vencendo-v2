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
  TablePagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import TableChartIcon from '@mui/icons-material/TableChart'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { dashboardApi } from '../api/endpoints'

/** Estilo do cabeçalho da tabela "Estoque a vencer": verde em destaque, texto branco. */
const tableHeaderCellSx = { bgcolor: '#2e7d32', color: 'white', fontWeight: 600 }

/** Formata data no formato ISO (YYYY-MM-DD) como DD/MM/AAAA sem alteração de fuso (evita "dia anterior"). */
function formatDateOnly(value: string | null | undefined): string {
  if (value == null) return '-'
  const s = String(value).trim().slice(0, 10)
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : '-'
}

/** Quebra texto longo em várias linhas para rótulos do eixo (ex.: nome do almoxarifado). */
function wrapLabel(text: string, maxCharsPerLine = 28): string[] {
  const words = text.split(/\s+/)
  const lines: string[] = []
  let current = ''
  for (const w of words) {
    const next = current ? `${current} ${w}` : w
    if (next.length <= maxCharsPerLine) {
      current = next
    } else {
      if (current) lines.push(current)
      current = w.length > maxCharsPerLine ? w.slice(0, maxCharsPerLine) : w
    }
  }
  if (current) lines.push(current)
  return lines
}

/** Tick customizado do eixo Y que exibe o nome do almoxarifado por completo (com quebra de linha). */
function WarehouseYAxisTick(props: { x?: number; y?: number; payload?: { value?: string } }) {
  const { x = 0, y = 0, payload } = props
  const text = payload?.value != null ? String(payload.value) : ''
  const lines = wrapLabel(text)
  const lineHeight = 12
  const startY = -(lines.length - 1) * (lineHeight / 2)
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="end" fontSize={10} fill="#37474f">
        {lines.map((line, i) => (
          <tspan key={i} x={0} dy={i === 0 ? startY : lineHeight}>{line}</tspan>
        ))}
      </text>
    </g>
  )
}

/** Formata YYYY-MM para "Mmm/YYYY" (ex.: 2026-02 → Fev/2026). */
function formatMonthLabel(ym: string): string {
  const [y, m] = String(ym).split('-')
  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
  const idx = parseInt(m, 10) - 1
  return idx >= 0 && idx < 12 ? `${monthNames[idx]}/${y}` : ym
}

/** Formata valor em R$ para o eixo Y (ex.: 150000 → "150 mil"). */
function formatAxisCurrency(value: number): string {
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(1).replace('.', ',')} mi`
  if (value >= 1e3) return `R$ ${(value / 1e3).toFixed(0)} mil`
  return `R$ ${value.toFixed(0)}`
}

/** Almoxarifados considerados no sistema – mesma lista do backend (ordem do gráfico). */
const ALMOXARIFADOS_GRAFICO = [
  '3-UACE HUWC - OPME',
  '4-UACE SATÉLITE - HUWC',
  '18-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE - ANEXO',
  '1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE HUWC',
  '36-UACE - MATERIAIS GERAIS - SATÉLITE HUWC',
  '2-UNIDADE DE LOGÍSTICA',
  '34-UNIDADE DE LOGÍSTICA (ANEXO)',
  '50-UACE QUARENTENA',
  '3-UACE MEAC - SATÉLITE',
  '1-UNIDADE DE ALMOXARIFADO E CONTROLE DE ESTOQUE MEAC',
  '2-(INATIVO) UACE SATÉLITE - MATERIAIS GERAIS MEAC',
  '16-CENTRAL DE CONSIGNADOS - UACE',
] as const

export function DashboardPage() {
  const [sector, setSector] = useState<string>('')
  const [warehouse, setWarehouse] = useState<string>('')
  const [materialGroup, setMaterialGroup] = useState<string>('')
  const [expiryFrom, setExpiryFrom] = useState<string>('')
  const [expiryTo, setExpiryTo] = useState<string>('')
  const [materialSearch, setMaterialSearch] = useState<string>('')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(50)

  const filters = {
    sector: sector || undefined,
    warehouse: warehouse || undefined,
    material_group: materialGroup || undefined,
    expiry_from: expiryFrom || undefined,
    expiry_to: expiryTo || undefined,
    material_search: materialSearch || undefined,
    page: page + 1,
    page_size: pageSize,
  }

  const { data: filterOptions } = useQuery({
    queryKey: ['dashboard', 'filter-options', sector || ''],
    queryFn: () => dashboardApi.filterOptions(sector ? { sector } : undefined).then((r) => r.data),
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard', 'stock-expiry', filters],
    queryFn: () => dashboardApi.stockExpiry(filters).then((r) => r.data),
  })

  const warehouseChartData = useMemo(() => {
    if (!data?.charts?.value_by_warehouse?.length) return []
    const allowed = new Set<string>(ALMOXARIFADOS_GRAFICO)
    const filtered = data.charts.value_by_warehouse.filter((d: { label?: string }) => allowed.has(d.label ?? ''))
    const items = [...ALMOXARIFADOS_GRAFICO]
      .map((label) => filtered.find((d: { label?: string }) => d.label === label))
      .filter((d): d is { label: string; value: number } => d != null)
    return items.slice().sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
  }, [data?.charts?.value_by_warehouse])

  const exportPdf = useMutation({
    mutationFn: () =>
      dashboardApi.exportPdf({
        sector: sector || undefined,
        warehouse: warehouse || undefined,
        material_group: materialGroup || undefined,
        expiry_from: expiryFrom || undefined,
        expiry_to: expiryTo || undefined,
        material_search: materialSearch || undefined,
      }),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'dashboard-stock-expiry.pdf'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const exportExcel = useMutation({
    mutationFn: () =>
      dashboardApi.exportExcel({
        sector: sector || undefined,
        warehouse: warehouse || undefined,
        material_group: materialGroup || undefined,
        expiry_from: expiryFrom || undefined,
        expiry_to: expiryTo || undefined,
        material_search: materialSearch || undefined,
      }),
    onSuccess: (res) => {
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'dashboard-stock-expiry.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const metrics = data?.metrics
  const charts = data?.charts
  const rows = data?.data ?? []
  const totalRows = data?.total_rows ?? 0

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Dashboard – Estoque a vencer (180 dias)
      </Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel>Setor</InputLabel>
            <Select value={sector} label="Setor" onChange={(e) => { setSector(e.target.value); setWarehouse('') }}>
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="UACE">UACE</MenuItem>
              <MenuItem value="ULOG">ULOG</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="filter-almoxarifado-label" shrink>Almoxarifado</InputLabel>
            <Select
              labelId="filter-almoxarifado-label"
              value={warehouse}
              label="Almoxarifado"
              onChange={(e) => setWarehouse(e.target.value)}
              displayEmpty
            >
              <MenuItem value="">Todos</MenuItem>
              {(filterOptions?.almoxarifados ?? []).map((label) => (
                <MenuItem key={label} value={label}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="filter-grupo-material-label" shrink>Grupo material</InputLabel>
            <Select
              labelId="filter-grupo-material-label"
              value={materialGroup}
              label="Grupo material"
              onChange={(e) => setMaterialGroup(e.target.value)}
              displayEmpty
            >
              <MenuItem value="">Todos</MenuItem>
              {(filterOptions?.grupos_material ?? []).map((label) => (
                <MenuItem key={label} value={label}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" type="date" label="Validade de" InputLabelProps={{ shrink: true }} value={expiryFrom} onChange={(e) => setExpiryFrom(e.target.value)} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" type="date" label="Validade até" InputLabelProps={{ shrink: true }} value={expiryTo} onChange={(e) => setExpiryTo(e.target.value)} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" label="Buscar material" value={materialSearch} onChange={(e) => setMaterialSearch(e.target.value)} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<RefreshIcon />} variant="outlined" onClick={() => refetch()} fullWidth>
            Atualizar
          </Button>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<PictureAsPdfIcon />} variant="outlined" onClick={() => exportPdf.mutate()} disabled={exportPdf.isPending} fullWidth>
            Exportar PDF
          </Button>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<TableChartIcon />} variant="outlined" onClick={() => exportExcel.mutate()} disabled={exportExcel.isPending} fullWidth>
            Exportar XLSX
          </Button>
        </Grid>
      </Grid>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Erro ao carregar dados. Verifique a conexão e permissões.'}
        </Alert>
      )}

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Valor total</Typography>
                  <Typography variant="h6">R$ {metrics?.total_value?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) ?? '0,00'}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Qtd. itens</Typography>
                  <Typography variant="h6">{metrics?.items_count ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Almoxarifados</Typography>
                  <Typography variant="h6">{metrics?.distinct_warehouses ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary">Próxima validade</Typography>
                  <Typography variant="h6">{formatDateOnly(metrics?.nearest_expiry_date ?? undefined)}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mb: 2 }}>
            {warehouseChartData.length ? (
              <Grid item xs={12} md={4}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Valor por almoxarifado</Typography>
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={warehouseChartData} layout="vertical" margin={{ left: 8, right: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={200}
                        tick={(props) => <WarehouseYAxisTick {...props} />}
                        interval={0}
                      />
                      <Tooltip formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']} />
                      <Bar dataKey="value" fill="#1565c0" name="Valor" barSize={30} radius={[4, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
            {charts?.value_by_expiry_month?.length ? (
              <Grid item xs={12} md={4}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Valor por mês de validade</Typography>
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={charts.value_by_expiry_month} margin={{ top: 8, right: 8, left: 8, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis
                        dataKey="label"
                        tickFormatter={formatMonthLabel}
                        tick={{ fontSize: 11 }}
                        interval={0}
                      />
                      <YAxis tickFormatter={formatAxisCurrency} tick={{ fontSize: 10 }} width={52} />
                      <Tooltip
                        formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']}
                        labelFormatter={(label) => formatMonthLabel(String(label))}
                      />
                      <Bar dataKey="value" fill="#00695c" name="Valor" barSize={78} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
            {charts?.top_material_groups?.length ? (
              <Grid item xs={12} md={4}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Top 10 grupos</Typography>
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={charts.top_material_groups} layout="vertical" margin={{ left: 8, right: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={200}
                        tick={(props) => <WarehouseYAxisTick {...props} />}
                        interval={0}
                      />
                      <Tooltip formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']} />
                      <Bar dataKey="value" fill="#8BC547" name="Valor" barSize={25} radius={[4, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
          </Grid>

          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Tabela de itens</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={tableHeaderCellSx}>Material</TableCell>
                      <TableCell sx={tableHeaderCellSx}>Almoxarifado</TableCell>
                      <TableCell sx={tableHeaderCellSx} align="right">Qtd</TableCell>
                      <TableCell sx={tableHeaderCellSx} align="right">Valor unit.</TableCell>
                      <TableCell sx={tableHeaderCellSx} align="right">Valor total</TableCell>
                      <TableCell sx={tableHeaderCellSx}>Validade</TableCell>
                      <TableCell sx={tableHeaderCellSx} align="right">Dias</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r: { material_code?: string; material_name?: string; warehouse?: string; quantity?: number; unit_value?: number; total_value?: number; expiry_date?: string; days_until_expiry?: number }, i: number) => (
                      <TableRow key={i}>
                        <TableCell>{r.material_name ?? r.material_code ?? '-'}</TableCell>
                        <TableCell>{r.warehouse ?? '-'}</TableCell>
                        <TableCell align="right">{Number(r.quantity ?? 0).toLocaleString('pt-BR')}</TableCell>
                        <TableCell align="right">R$ {Number(r.unit_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell align="right">R$ {Number(r.total_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell>{formatDateOnly(r.expiry_date ?? undefined)}</TableCell>
                        <TableCell align="right">{r.days_until_expiry ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={totalRows}
                page={page}
                onPageChange={(_, p) => setPage(p)}
                rowsPerPage={pageSize}
                onRowsPerPageChange={(e) => { setPageSize(parseInt(e.target.value, 10)); setPage(0); }}
                rowsPerPageOptions={[25, 50, 100]}
                labelRowsPerPage="Linhas:"
              />
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  )
}

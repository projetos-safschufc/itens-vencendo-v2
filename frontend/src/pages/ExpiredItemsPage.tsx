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
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import TableChartIcon from '@mui/icons-material/TableChart'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { useQuery, useMutation } from '@tanstack/react-query'
import { expiredItemsApi } from '../api/endpoints'

/** Formata YYYY-MM-DD para MM/YYYY (ex.: 02/2026) para coluna Mês. */
function formatValidityMMYYYY(iso?: string | null): string {
  if (!iso) return '-'
  const parts = String(iso).split('T')[0].split('-')
  if (parts.length !== 3) return iso
  return `${parts[1]}/${parts[0]}`
}

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 2023 + 1 }, (_, i) => 2023 + i)

export function ExpiredItemsPage() {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [year, setYear] = useState<number | ''>('')
  const [sector, setSector] = useState('')
  const [warehouse, setWarehouse] = useState('')
  const [materialGroup, setMaterialGroup] = useState('')
  const [material, setMaterial] = useState('')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(50)

  const filters = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    year: year !== '' ? Number(year) : undefined,
    sector: sector || undefined,
    warehouse: warehouse || undefined,
    material_group: materialGroup || undefined,
    material: material || undefined,
    page: page + 1,
    page_size: pageSize,
  }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['expired-items', filters],
    queryFn: () => expiredItemsApi.list(filters).then((r) => r.data),
  })

  const { data: filterOpts } = useQuery({
    queryKey: ['expired-items-filter-options', sector],
    queryFn: () => expiredItemsApi.filterOptions({ sector: sector || undefined }).then((r) => r.data),
  })
  const warehouseOptions = filterOpts?.warehouses ?? []
  const materialGroupOptions = filterOpts?.material_groups ?? []

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportCsv = useMutation({
    mutationFn: () =>
      expiredItemsApi.exportCsv({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        year: year !== '' ? Number(year) : undefined,
        sector: sector || undefined,
        warehouse: warehouse || undefined,
        material_group: materialGroup || undefined,
        material: material || undefined,
      }),
    onSuccess: (res: { data: Blob }) => downloadBlob(res.data, 'itens-vencidos.csv'),
  })

  const exportPdf = useMutation({
    mutationFn: () =>
      expiredItemsApi.exportPdf({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        year: year !== '' ? Number(year) : undefined,
        sector: sector || undefined,
        warehouse: warehouse || undefined,
        material_group: materialGroup || undefined,
        material: material || undefined,
      }),
    onSuccess: (res: { data: Blob }) => downloadBlob(res.data, 'itens-vencidos.pdf'),
  })

  const exportExcel = useMutation({
    mutationFn: () =>
      expiredItemsApi.exportExcel({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        year: year !== '' ? Number(year) : undefined,
        sector: sector || undefined,
        warehouse: warehouse || undefined,
        material_group: materialGroup || undefined,
        material: material || undefined,
      }),
    onSuccess: (res: { data: Blob }) => downloadBlob(res.data, 'itens-vencidos.xlsx'),
  })

  const metrics = data?.metrics
  const charts = data?.charts
  const rows = data?.data ?? []
  const totalRows = data?.total_rows ?? 0

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Histórico de itens vencidos</Typography>
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" type="date" label="Validade de" InputLabelProps={{ shrink: true }} value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" type="date" label="Validade até" InputLabelProps={{ shrink: true }} value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="expired-year-label">Ano</InputLabel>
            <Select
              labelId="expired-year-label"
              value={year === '' ? '' : year}
              label="Ano"
              displayEmpty
              onChange={(e) => setYear(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <MenuItem value="">Todos</MenuItem>
              {YEAR_OPTIONS.map((y) => (
                <MenuItem key={y} value={y}>{y}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="expired-sector-label">Setor</InputLabel>
            <Select
              labelId="expired-sector-label"
              value={sector}
              label="Setor"
              onChange={(e) => { setSector(e.target.value); setWarehouse('') }}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="UACE">UACE</MenuItem>
              <MenuItem value="ULOG">ULOG</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="expired-warehouse-label" shrink>Almoxarifado</InputLabel>
            <Select
              labelId="expired-warehouse-label"
              value={warehouse}
              label="Almoxarifado"
              displayEmpty
              onChange={(e) => setWarehouse(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              {warehouseOptions.map((w) => (
                <MenuItem key={w} value={w}>{w}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel id="expired-group-label" shrink>Grupo de material</InputLabel>
            <Select
              labelId="expired-group-label"
              value={materialGroup}
              label="Grupo de material"
              displayEmpty
              onChange={(e) => setMaterialGroup(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              {materialGroupOptions.map((g) => (
                <MenuItem key={g} value={g}>{g}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <TextField fullWidth size="small" label="Material" value={material} onChange={(e) => setMaterial(e.target.value)} placeholder="Buscar por nome/código" />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<RefreshIcon />} variant="contained" onClick={() => refetch()} fullWidth>Atualizar</Button>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<FileDownloadIcon />} variant="outlined" onClick={() => exportCsv.mutate()} disabled={exportCsv.isPending} fullWidth>Exportar CSV</Button>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<PictureAsPdfIcon />} variant="outlined" onClick={() => exportPdf.mutate()} disabled={exportPdf.isPending} fullWidth>Exportar PDF</Button>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <Button startIcon={<TableChartIcon />} variant="outlined" onClick={() => exportExcel.mutate()} disabled={exportExcel.isPending} fullWidth>Exportar XLSX</Button>
        </Grid>
      </Grid>
      {error && <Alert severity="error" sx={{ mb: 2 }}>Erro ao carregar dados.</Alert>}
      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} sm={4}>
              <Card><CardContent>
                <Typography color="text.secondary">Valor total perdido</Typography>
                <Typography variant="h6">R$ {metrics?.total_lost_value?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) ?? '0,00'}</Typography>
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card><CardContent>
                <Typography color="text.secondary">Total itens vencidos</Typography>
                <Typography variant="h6">{metrics?.total_expired_items ?? 0}</Typography>
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card><CardContent>
                <Typography color="text.secondary">Média perda por item</Typography>
                <Typography variant="h6">R$ {metrics?.average_loss_per_item?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) ?? '0,00'}</Typography>
              </CardContent></Card>
            </Grid>
          </Grid>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            {/* Linha 1: Histórico por mês + Perdas por ano (exercício) */}
            {charts?.distinct_materials_per_month?.length ? (
              <Grid item xs={12} md={6}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Histórico de itens vencidos por mês</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart
                      data={charts.distinct_materials_per_month.map((d: { month: string; count: number }) => ({
                        ...d,
                        monthLabel: d.month ? (() => {
                          const [y, m] = String(d.month).split('-')
                          const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                          return `${months[parseInt(m, 10) - 1] || m}/${y}`
                        })() : d.month,
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="monthLabel" />
                      <YAxis allowDecimals={false} />
                      <Tooltip formatter={(v: number) => [v, 'Itens distintos']} labelFormatter={(l) => l} />
                      <Line type="monotone" dataKey="count" stroke="#c62828" name="Itens distintos" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
            {charts?.by_year?.length ? (
              <Grid item xs={12} md={6}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Perdas por ano (exercício)</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={charts.by_year} margin={{ bottom: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="year" />
                      <YAxis tickFormatter={(v) => `R$ ${(v / 1000).toFixed(0)} mil`} />
                      <Tooltip formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']} />
                      <Bar dataKey="value" fill="#00695c" name="Valor" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
            {/* Linha 2: Top 10 grupos + Valor perdido por almoxarifado (lado a lado) */}
            {charts?.by_group?.length ? (
              <Grid item xs={12} md={6}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Top 10 grupos por valor perdido</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={[...(charts.by_group ?? [])].sort((b) => Number(b.value) - Number(b.value))}
                      layout="vertical"
                      margin={{ left: 8, right: 24 }}
                    >
                      {/* Ordem decrescente: sort ascendente no array → no eixo Y o último fica no topo (maior valor) */}
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" tickFormatter={(v) => `R$ ${(v / 1000).toFixed(0)} mil`} />
                      <YAxis type="category" dataKey="label" width={160} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']} />
                      <Bar dataKey="value" fill="#1565c0" name="Valor" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
            {charts?.by_warehouse?.length ? (
              <Grid item xs={12} md={6}>
                <Card><CardContent>
                  <Typography variant="subtitle2" gutterBottom>Valor perdido por almoxarifado</Typography>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={[...(charts.by_warehouse ?? [])].sort((a) => (Number(a.value) - Number(a.value)))}
                      layout="vertical"
                      margin={{ left: 8, right: 24 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" tickFormatter={(v) => `R$ ${(v / 1000).toFixed(0)} mil`} />
                      <YAxis type="category" dataKey="label" width={200} tick={{ fontSize: 9 }} />
                      <Tooltip formatter={(v: number) => ['R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }), 'Valor']} />
                      <Bar dataKey="value" fill="#2e7d32" name="Valor" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent></Card>
              </Grid>
            ) : null}
          </Grid>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Detalhes dos Itens Vencidos</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Material</TableCell>
                      <TableCell>Mês</TableCell>
                      <TableCell align="right">Qtd</TableCell>
                      <TableCell align="right">Valor unit.</TableCell>
                      <TableCell align="right">Valor total</TableCell>
                      <TableCell>Grupo</TableCell>
                      <TableCell>Almoxarifado</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r: {
                      material_code?: string
                      material_name?: string
                      validity?: string
                      quantity?: number
                      unit_value?: number
                      total_value?: number
                      group?: string
                      warehouse?: string
                      status?: string
                    }, i: number) => (
                      <TableRow key={i}>
                        <TableCell>{r.material_name ?? r.material_code ?? '-'}</TableCell>
                        <TableCell>{formatValidityMMYYYY(r.validity)}</TableCell>
                        <TableCell align="right">{Number(r.quantity ?? 0).toLocaleString('pt-BR')}</TableCell>
                        <TableCell align="right">R$ {Number(r.unit_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell align="right">R$ {Number(r.total_value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell>{r.group ?? '-'}</TableCell>
                        <TableCell>{r.warehouse ?? '-'}</TableCell>
                        <TableCell>{r.status ?? 'VENCIDO'}</TableCell>
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

import { api } from './client'

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string; expires_in: number }>(
      '/auth/login',
      { username, password },
      { timeout: 30000 }
    ),
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/auth/refresh', { refresh_token }),
  me: () => api.get<{ id: string; username: string; role: string; full_name: string | null }>('/auth/me'),
  register: (data: { name: string; email: string; password: string; profile_id: number }) =>
    api.post<{ id: string; username: string; role: string; full_name: string | null }>('/auth/register', data),
}

function params(obj: Record<string, string | number | boolean | undefined | null>) {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  })
  return p.toString()
}

export const dashboardApi = {
  filterOptions: (f?: { sector?: string }) =>
    api.get<{ almoxarifados: string[]; grupos_material: string[] }>('/dashboard/filter-options?' + (f ? params(f) : '')),
  stockExpiry: (f: {
    sector?: string
    warehouse?: string
    material_group?: string
    expiry_from?: string
    expiry_to?: string
    material_search?: string
    page?: number
    page_size?: number
  }) => api.get('/dashboard/stock-expiry?' + params(f)),
  metrics: (f: { sector?: string; warehouse?: string; material_group?: string }) =>
    api.get('/dashboard/metrics?' + params(f)),
  charts: (f: { sector?: string; warehouse?: string; material_group?: string }) =>
    api.get('/dashboard/charts?' + params(f)),
  exportPdf: (f: {
    sector?: string
    warehouse?: string
    material_group?: string
    expiry_from?: string
    expiry_to?: string
    material_search?: string
  }) => api.post('/dashboard/export/pdf?' + params(f), {}, { responseType: 'blob' }),
  exportExcel: (f: {
    sector?: string
    warehouse?: string
    material_group?: string
    expiry_from?: string
    expiry_to?: string
    material_search?: string
  }) => api.post('/dashboard/export/excel?' + params(f), {}, { responseType: 'blob' }),
}

export type ExpiredFilters = {
  date_from?: string
  date_to?: string
  year?: number
  sector?: string
  warehouse?: string
  material_group?: string
  material?: string
  page?: number
  page_size?: number
}

export const expiredItemsApi = {
  list: (f: ExpiredFilters) => api.get('/expired-items?' + params(f)),
  filterOptions: (f?: { sector?: string }) =>
    api.get<{ warehouses: string[]; material_groups: string[] }>('/expired-items/filter-options?' + (f ? params(f) : '')),
  metrics: (f: Omit<ExpiredFilters, 'page' | 'page_size'>) => api.get('/expired-items/metrics?' + params(f)),
  charts: (f: Omit<ExpiredFilters, 'page' | 'page_size'>) => api.get('/expired-items/charts?' + params(f)),
  exportCsv: (f: Omit<ExpiredFilters, 'page' | 'page_size'>) =>
    api.post('/expired-items/export/csv?' + params(f), {}, { responseType: 'blob' }),
  exportPdf: (f: Omit<ExpiredFilters, 'page' | 'page_size'>) =>
    api.post('/expired-items/export/pdf?' + params(f), {}, { responseType: 'blob' }),
  exportExcel: (f: Omit<ExpiredFilters, 'page' | 'page_size'>) =>
    api.post('/expired-items/export/excel?' + params(f), {}, { responseType: 'blob' }),
}

export type PredictiveFilters = {
  sector?: string
  warehouse?: string
  material_group?: string
  material_search?: string
  risk?: string
  as_of_date?: string
}

export const predictiveApi = {
  query: (f: PredictiveFilters) =>
    api.post('/predictive/query?' + params(f)),
  exportExcel: (f: PredictiveFilters) =>
    api.post('/predictive/export/excel?' + params(f), {}, { responseType: 'blob' }),
  exportCsv: (f: PredictiveFilters) =>
    api.post('/predictive/export/csv?' + params(f), {}, { responseType: 'blob' }),
  exportPdf: (f: PredictiveFilters) =>
    api.post('/predictive/export/pdf?' + params(f), {}, { responseType: 'blob' }),
}

export const testeApi = {
  list: (f?: { material?: string }) =>
    api.get<{ data: { material: string; media_ultimos_6_meses: number }[]; total_rows: number }>(
      '/teste?' + (f ? params(f) : '')
    ),
}

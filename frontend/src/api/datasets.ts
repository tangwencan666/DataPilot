import { apiRequest } from './client'

export type DatasetStatus = 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED'
export type Dataset = {
  id: string; name: string; original_filename: string; stored_filename: string
  file_type: 'csv' | 'xlsx'; file_size: number; row_count: number; column_count: number
  status: DatasetStatus; created_at: string; updated_at: string; metadata_json: Record<string, unknown>
}
export type ColumnInfo = { name: string; dtype: string; missing: number; unique: number }
export type DatasetPreview = {
  dataset_id: string; filename: string; row_count: number; column_count: number
  columns: ColumnInfo[]; preview_rows: Record<string, unknown>[]; preview_limit: number
}
export type DatasetList = { items: Dataset[]; total: number; page: number; page_size: number }

export function listDatasets(page = 1, pageSize = 20) {
  return apiRequest<DatasetList>(`/datasets?page=${page}&page_size=${pageSize}`)
}
export function getDataset(id: string) { return apiRequest<Dataset>(`/datasets/${id}`) }
export function getDatasetPreview(id: string) { return apiRequest<DatasetPreview>(`/datasets/${id}/preview`) }
export function deleteDataset(id: string) { return apiRequest<void>(`/datasets/${id}`, { method: 'DELETE' }) }
export function uploadDataset(file: File) {
  const form = new FormData(); form.append('file', file)
  return apiRequest<Dataset>('/datasets', { method: 'POST', body: form })
}

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
export type SemanticType = 'NUMERIC' | 'CATEGORICAL' | 'BOOLEAN' | 'DATETIME' | 'TEXT' | 'UNKNOWN'
export type QualityIssue = { code: string; severity: 'INFO' | 'WARNING' | 'ERROR'; title: string; description: string; column: string | null; metric: string; value: number | string }
export type ColumnProfile = {
  name: string; physical_dtype: string; semantic_type: SemanticType; count: number; non_null_count: number
  missing_count: number; missing_ratio: number; unique_count: number; unique_ratio: number
  is_constant: boolean; is_all_missing: boolean; sample_values: unknown[]
  numeric?: Record<string, number | null>; categorical?: { unique_count: number; top_values: TopValue[]; is_high_cardinality: boolean }
  text?: { average_length: number | null; min_length: number | null; max_length: number | null; empty_string_count: number; top_values: TopValue[] }
  datetime?: { min_datetime: string | null; max_datetime: string | null; range_days: number | null }
  boolean?: { true_count: number; false_count: number; true_ratio: number; false_ratio: number }
}
export type TopValue = { value: unknown; count: number; ratio: number }
export type ProfileResult = {
  summary: Record<string, number>; sampling: { is_sampled: boolean; sampled_row_count: number; source_row_count: number; statistics_scope: string }
  columns: ColumnProfile[]; correlations: { column_a: string; column_b: string; correlation: number }[]; issues: QualityIssue[]
}
export type DatasetProfile = { id: string; dataset_id: string; status: 'PENDING' | 'RUNNING' | 'READY' | 'FAILED'; profile_version: number; quality_score: number; generated_at: string | null; error_message: string | null; profile: ProfileResult | null }

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
export function getProfile(id: string) { return apiRequest<DatasetProfile>(`/datasets/${id}/profile`) }
export function generateProfile(id: string) { return apiRequest<DatasetProfile>(`/datasets/${id}/profile`, { method: 'POST' }) }

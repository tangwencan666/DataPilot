import { apiRequest } from './client'

export type QueryMetadata = { id: string; dataset_id: string; question: string; generated_sql: string | null; explanation: string | null; status: string; row_count: number | null; execution_time_ms: number | null; error_code: string | null; error_message: string | null; created_at: string; updated_at: string }
export type QueryResult = { columns: string[]; rows: unknown[][]; row_count: number; truncated: boolean; execution_time_ms: number; sql: string }
export type QueryResponse = { query: QueryMetadata; generation: { sql: string; explanation: string; confidence: number; assumptions: string[] }; result: QueryResult }
export type QueryList = { items: QueryMetadata[]; total: number; page: number; page_size: number }

export function runQuery(datasetId: string, question: string) { return apiRequest<QueryResponse>(`/datasets/${datasetId}/queries`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) }) }
export function listQueries(datasetId: string) { return apiRequest<QueryList>(`/datasets/${datasetId}/queries?page=1&page_size=20`) }
export function getQuery(datasetId: string, queryId: string) { return apiRequest<QueryMetadata>(`/datasets/${datasetId}/queries/${queryId}`) }

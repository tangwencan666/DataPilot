import { apiRequest } from './client'

export type Aggregation = 'sum'|'mean'|'median'|'min'|'max'|'count'|'nunique'|'std'
export type AnalysisOperation =
  | { type:'groupby_aggregate'; group_by:string[]; metrics:{column:string;aggregation:Aggregation}[]; sort:{column:string;direction:'asc'|'desc'}[]; limit:number }
  | { type:'value_counts'; column:string; top_n:number; dropna:boolean }
  | { type:'descriptive_statistics'; columns:string[] }
  | { type:'correlation'; columns:string[]; method:'pearson'|'spearman' }
  | { type:'time_series_aggregate'; datetime_column:string; frequency:'day'|'week'|'month'|'quarter'|'year'; metric:{column:string;aggregation:Aggregation}; group_by:string[] }
export type AnalysisPlan = { operations: AnalysisOperation[] }
export type OperationTrace = { step:number; type:string; duration_ms:number; input_rows:number; output_rows:number }
export type AnalysisResult = { columns:string[]; rows:unknown[][]; row_count:number; truncated:boolean; execution_time_ms:number; operations_executed:OperationTrace[]; warnings:string[]; metadata:Record<string,unknown> }
export type AnalysisRun = { id:string; dataset_id:string; status:string; request_json:Record<string,unknown>; result_summary_json:Record<string,unknown>; operation_count:number; input_row_count:number|null; output_row_count:number|null; execution_time_ms:number|null; error_code:string|null; error_message:string|null; created_at:string; updated_at:string }
export type AnalysisResponse = { analysis:AnalysisRun; result:AnalysisResult }
export type AnalysisList = { items:AnalysisRun[]; total:number; page:number; page_size:number }

export function runAnalysis(datasetId:string,plan:AnalysisPlan){return apiRequest<AnalysisResponse>(`/datasets/${datasetId}/analyses`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(plan)})}
export function listAnalyses(datasetId:string){return apiRequest<AnalysisList>(`/datasets/${datasetId}/analyses?page=1&page_size=20`)}

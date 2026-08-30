import { apiRequest } from './client'
export type ChartType='BAR'|'LINE'|'AREA'|'PIE'|'SCATTER'|'HISTOGRAM'|'BOXPLOT'
export type ChartSpec=Record<string,unknown>&{type:ChartType;title:string}
export type Chart={id:string;dataset_id:string;source_type:'DATASET'|'QUERY'|'ANALYSIS';source_reference_id:string|null;chart_type:ChartType;title:string;spec_json:ChartSpec;option_json:Record<string,unknown>;status:'PENDING'|'GENERATING'|'READY'|'FAILED';source_row_count:number;rendered_point_count:number;sampled:boolean;error_code:string|null;error_message:string|null;created_at:string;updated_at:string}
export type ChartResult={chart_id:string;type:ChartType;title:string;spec:ChartSpec;echarts_option:Record<string,unknown>;source_row_count:number;rendered_point_count:number;sampled:boolean;warnings:string[];generated_at:string}
export type ChartList={items:Chart[];total:number;page:number;page_size:number}
export const listCharts=(datasetId:string)=>apiRequest<ChartList>(`/datasets/${datasetId}/charts`)
export const getChart=(datasetId:string,chartId:string)=>apiRequest<Chart>(`/datasets/${datasetId}/charts/${chartId}`)
export const createChart=(datasetId:string,spec:ChartSpec)=>apiRequest<ChartResult>(`/datasets/${datasetId}/charts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(spec)})
export const deleteChart=(datasetId:string,chartId:string)=>apiRequest<void>(`/datasets/${datasetId}/charts/${chartId}`,{method:'DELETE'})

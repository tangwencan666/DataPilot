import{apiDownload,apiRequest}from'./client'
export type Report={id:string;agent_run_id:string;title:string;status:string;executive_summary:string;report:{title:string;executive_summary:string;sections:{key:string;title:string;content:string}[];key_insights:{id:string;title:string;statement:string;importance:string;confidence:number;evidence_refs:string[]}[];limitations:string[];artifacts:{type:string;id:string;title:string;summary:string}[];source_status:string}|null;insight_count:number;created_at:string}
export const listReports=(d:string)=>apiRequest<{items:Report[];total:number}>(`/datasets/${d}/reports`)
export const createReport=(d:string,r:string)=>apiRequest<Report>(`/datasets/${d}/reports`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent_run_id:r})})
export const deleteReport=(d:string,r:string)=>apiRequest<void>(`/datasets/${d}/reports/${r}`,{method:'DELETE'})
export const downloadReport=(d:string,r:string,f:'markdown'|'html')=>apiDownload(`/datasets/${d}/reports/${r}/export?format=${f}`,`datapilot-report.${f==='markdown'?'md':'html'}`)

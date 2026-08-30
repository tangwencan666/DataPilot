import { ChangeEvent, useCallback, useEffect, useState } from 'react'
import { Dataset, DatasetPreview, deleteDataset, getDataset, getDatasetPreview, listDatasets, uploadDataset } from './api/datasets'

const formatSize = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

export default function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selected, setSelected] = useState<Dataset | null>(null)
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    try { setDatasets((await listDatasets()).items); setError('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : '无法加载数据集') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void refresh() }, [refresh])

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return
    setUploading(true); setError(''); setMessage('')
    try { await uploadDataset(file); setMessage(`${file.name} 上传成功`); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : '上传失败') }
    finally { setUploading(false); event.target.value = '' }
  }

  async function view(dataset: Dataset) {
    setLoading(true); setError('')
    try {
      const [detail, dataPreview] = await Promise.all([getDataset(dataset.id), getDatasetPreview(dataset.id)])
      setSelected(detail); setPreview(dataPreview)
    } catch (reason) { setError(reason instanceof Error ? reason.message : '无法加载详情') }
    finally { setLoading(false) }
  }

  async function remove(dataset: Dataset) {
    if (!window.confirm(`确定删除 ${dataset.name}？此操作会同时删除上传文件。`)) return
    try { await deleteDataset(dataset.id); if (selected?.id === dataset.id) { setSelected(null); setPreview(null) }; await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : '删除失败') }
  }

  return <main className="shell">
    <nav><button className="brand button-reset" onClick={() => { setSelected(null); setPreview(null) }}>DataPilot</button><span className="stage">Stage 2</span></nav>
    {!selected ? <>
      <section className="page-head">
        <div><p className="eyebrow">DATASET MANAGEMENT</p><h1>Datasets</h1><p className="intro">上传并管理 CSV 或 Excel 数据集，查看结构、质量指标和数据样例。</p></div>
        <label className={`upload ${uploading ? 'disabled' : ''}`}><input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={upload} disabled={uploading} />{uploading ? '正在上传…' : 'Upload Dataset'}</label>
      </section>
      {message && <p className="success">{message}</p>}{error && <p className="error">{error}</p>}
      <section className="dataset-list">
        <div className="list-title"><h2>All datasets</h2><span>{datasets.length} items</span></div>
        {loading ? <p className="empty">正在加载…</p> : datasets.length === 0 ? <p className="empty">还没有数据集。上传 CSV 或 XLSX 文件开始使用。</p> :
          <div className="table-wrap"><table><thead><tr><th>名称</th><th>类型</th><th>大小</th><th>规模</th><th>状态</th><th>创建时间</th><th></th></tr></thead><tbody>
            {datasets.map(item => <tr key={item.id}><td><button className="name-link" onClick={() => void view(item)}>{item.name}</button><small>{item.original_filename}</small></td><td><span className="file-type">{item.file_type.toUpperCase()}</span></td><td>{formatSize(item.file_size)}</td><td>{item.row_count} × {item.column_count}</td><td><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span></td><td>{formatDate(item.created_at)}</td><td className="actions"><button onClick={() => void view(item)}>View</button><button className="danger" onClick={() => void remove(item)}>Delete</button></td></tr>)}
          </tbody></table></div>}
      </section>
    </> : <section className="detail">
      <button className="back" onClick={() => { setSelected(null); setPreview(null) }}>← 返回 Datasets</button>
      {error && <p className="error">{error}</p>}
      <header><div><p className="eyebrow">DATASET DETAIL</p><h2>{selected.name}</h2><p>{selected.original_filename}</p></div><span className={`status ${selected.status.toLowerCase()}`}>{selected.status}</span></header>
      <div className="facts"><div><span>File Type</span><strong>{selected.file_type.toUpperCase()}</strong></div><div><span>File Size</span><strong>{formatSize(selected.file_size)}</strong></div><div><span>Rows</span><strong>{selected.row_count}</strong></div><div><span>Columns</span><strong>{selected.column_count}</strong></div><div><span>Created</span><strong>{formatDate(selected.created_at)}</strong></div></div>
      {preview && <><h3>Columns</h3><div className="table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Missing</th><th>Unique</th></tr></thead><tbody>{preview.columns.map(column => <tr key={column.name}><td>{column.name}</td><td>{column.dtype}</td><td>{column.missing}</td><td>{column.unique}</td></tr>)}</tbody></table></div>
      <h3>Data Preview <small>前 {preview.preview_limit} 行以内</small></h3><div className="table-wrap"><table><thead><tr>{preview.columns.map(column => <th key={column.name}>{column.name}</th>)}</tr></thead><tbody>{preview.preview_rows.map((row, index) => <tr key={index}>{preview.columns.map(column => <td key={column.name}>{String(row[column.name] ?? '—')}</td>)}</tr>)}</tbody></table></div></>}
    </section>}
  </main>
}

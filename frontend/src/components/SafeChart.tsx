import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export function SafeChart({option}:{option:Record<string,unknown>}){
  const container=useRef<HTMLDivElement>(null)
  useEffect(()=>{
    if(!container.current)return
    const chart=echarts.init(container.current)
    chart.setOption(option,true)
    const resize=()=>chart.resize(); window.addEventListener('resize',resize)
    return()=>{window.removeEventListener('resize',resize);chart.dispose()}
  },[option])
  return <div ref={container} style={{height:420,width:'100%'}} aria-label="Data visualization" />
}

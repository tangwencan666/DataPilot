from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from app.charts.errors import InvalidColumnError, InvalidColumnTypeError, NoDataError, TooManyPointsError, TooManySeriesError, ChartValidationError
from app.charts.schemas import BarSpec, BoxplotSpec, ChartSpec, HistogramSpec, LineSpec, PieSpec, ScatterSpec
from app.config import Settings
from app.query.executor import json_value

@dataclass
class PreparedChart:
    option: dict[str, Any]; source_count: int; rendered_count: int; sampled: bool; warnings: list[str]

def _column(frame: pd.DataFrame, name: str, numeric: bool=False) -> pd.Series:
    if name not in frame.columns: raise InvalidColumnError(f"Column '{name}' does not exist.")
    series=frame[name]
    if numeric and not pd.api.types.is_numeric_dtype(series): raise InvalidColumnTypeError(f"Column '{name}' must be numeric.")
    return series

def _base(title: str, legend: bool=True) -> dict[str, Any]:
    return {"title":{"text":title,"left":"center"},"tooltip":{"trigger":"axis"},"legend":{"show":legend,"top":30},"grid":{"left":55,"right":30,"top":70,"bottom":70,"containLabel":True}}

def _values(values) -> list[Any]: return [json_value(v) for v in values]

def prepare_chart(frame: pd.DataFrame, spec: ChartSpec, settings: Settings) -> PreparedChart:
    source=len(frame); warnings=[]
    if frame.empty: raise NoDataError("The Dataset contains no rows.")
    if isinstance(spec, BarSpec):
        _column(frame,spec.category); _column(frame,spec.metric, spec.aggregation!="count")
        grouped=frame.groupby(spec.category,dropna=False)[spec.metric].agg(spec.aggregation).reset_index(name="value").sort_values("value",ascending=spec.sort=="asc")
        if len(grouped)>settings.chart_max_categories: raise ChartValidationError("Chart exceeds CHART_MAX_CATEGORIES.")
        grouped=grouped.head(spec.limit); cats=_values(grouped[spec.category].fillna("(null)")); vals=_values(grouped["value"])
        option=_base(spec.title,spec.legend); option.update({"xAxis":{"type":"category","data":cats,"axisLabel":{"rotate":35 if any(len(str(x))>12 for x in cats) else 0}},"yAxis":{"type":"value"},"series":[{"name":spec.metric,"type":"bar","data":vals}]})
        if spec.orientation=="horizontal": option["xAxis"],option["yAxis"]={"type":"value"},{"type":"category","data":cats}; option["series"][0]["data"]=vals
        return PreparedChart(option,source,len(vals),False,warnings)
    if isinstance(spec, LineSpec):
        _column(frame,spec.x); _column(frame,spec.y,spec.aggregation!="count")
        work=frame[[spec.x,spec.y]+([spec.series] if spec.series else [])].copy()
        if spec.frequency:
            dates=pd.to_datetime(work[spec.x],errors="coerce");
            if dates.notna().sum()==0: raise InvalidColumnTypeError(f"Column '{spec.x}' must be datetime for frequency bucketing.")
            freq={"day":"D","week":"W-MON","month":"M","quarter":"Q","year":"Y"}[spec.frequency]; work[spec.x]=dates.dt.to_period(freq).dt.start_time
        keys=[spec.x]+([spec.series] if spec.series else []); grouped=work.dropna(subset=[spec.x]).groupby(keys,dropna=False)[spec.y].agg(spec.aggregation).reset_index(name="value")
        if len(grouped)>settings.chart_max_result_rows: raise TooManyPointsError("Aggregated chart exceeds CHART_MAX_RESULT_ROWS.")
        names=[None] if not spec.series else list(grouped[spec.series].drop_duplicates())
        if len(names)>settings.chart_max_series: raise TooManySeriesError("Chart exceeds CHART_MAX_SERIES.")
        xvals=sorted(grouped[spec.x].drop_duplicates(),reverse=spec.sort=="desc")[:spec.limit]; series=[]
        for name in names:
            part=grouped if name is None else grouped[grouped[spec.series]==name]; mapping={json_value(k):json_value(v) for k,v in zip(part[spec.x],part["value"])}; labels=_values(xvals)
            series.append({"name":spec.y if name is None else str(name),"type":"line","areaStyle":{} if spec.type=="AREA" else None,"data":[mapping.get(label) for label in labels],"connectNulls":False})
        option=_base(spec.title,spec.legend); option.update({"xAxis":{"type":"category","data":_values(xvals),"axisLabel":{"rotate":35}},"yAxis":{"type":"value"},"series":series})
        return PreparedChart(option,source,len(xvals)*len(series),False,warnings)
    if isinstance(spec, PieSpec):
        _column(frame,spec.category); _column(frame,spec.metric,spec.aggregation!="count")
        grouped=frame.groupby(spec.category,dropna=False)[spec.metric].agg(spec.aggregation).reset_index(name="value").sort_values("value",ascending=spec.sort=="asc")
        limit=min(spec.limit,settings.chart_max_pie_slices); head=grouped.head(limit).copy()
        if spec.include_other and len(grouped)>limit: head.loc[len(head)]={spec.category:"Other","value":grouped.iloc[limit:]["value"].sum()}
        data=[{"name":str(json_value(r[spec.category]) or "(null)"),"value":json_value(r["value"])} for _,r in head.iterrows()]
        option=_base(spec.title,spec.legend); option["tooltip"]={"trigger":"item"}; option["series"]=[{"name":spec.metric,"type":"pie","radius":["0%","70%"],"data":data}]
        return PreparedChart(option,source,len(data),False,warnings)
    if isinstance(spec, ScatterSpec):
        _column(frame,spec.x,True); _column(frame,spec.y,True)
        cols=[spec.x,spec.y]+([spec.series] if spec.series else []); clean=frame[cols].dropna(subset=[spec.x,spec.y]); count=len(clean); sampled=count>settings.chart_max_points
        if sampled: clean=clean.sample(settings.chart_max_points,random_state=42).sort_index(); warnings.append(f"Deterministically sampled {settings.chart_max_points} of {count} points.")
        names=[None] if not spec.series else list(clean[spec.series].fillna("(null)").drop_duplicates())
        if len(names)>settings.chart_max_series: raise TooManySeriesError("Chart exceeds CHART_MAX_SERIES.")
        series=[]
        for name in names:
            part=clean if name is None else clean[clean[spec.series].fillna("(null)")==name]; series.append({"name":"Points" if name is None else str(name),"type":"scatter","data":[_values(row) for row in part[[spec.x,spec.y]].to_numpy()]})
        option=_base(spec.title,spec.legend); option.update({"xAxis":{"type":"value","name":spec.x},"yAxis":{"type":"value","name":spec.y},"series":series})
        return PreparedChart(option,count,len(clean),sampled,warnings)
    if isinstance(spec, HistogramSpec):
        if spec.bins>settings.chart_max_histogram_bins: raise ChartValidationError("Histogram exceeds CHART_MAX_HISTOGRAM_BINS.")
        values=_column(frame,spec.column,True).dropna().to_numpy()
        if not len(values): raise NoDataError("No numeric values are available.")
        counts,edges=np.histogram(values,bins=spec.bins); labels=[f"{edges[i]:.4g} – {edges[i+1]:.4g}" for i in range(len(counts))]
        option=_base(spec.title,spec.legend); option.update({"xAxis":{"type":"category","data":labels,"axisLabel":{"rotate":35}},"yAxis":{"type":"value"},"series":[{"name":"Count","type":"bar","data":_values(counts)}]})
        return PreparedChart(option,source,len(counts),False,warnings)
    if isinstance(spec, BoxplotSpec):
        _column(frame,spec.value,True); categories=["All"] if not spec.category else list(_column(frame,spec.category).fillna("(null)").value_counts().head(spec.limit).index)
        if len(categories)>settings.chart_max_categories: raise ChartValidationError("Chart exceeds CHART_MAX_CATEGORIES.")
        boxes=[]; outliers=[]
        for i,category in enumerate(categories):
            values=(frame[spec.value] if not spec.category else frame.loc[frame[spec.category].fillna("(null)")==category,spec.value]).dropna().astype(float)
            if values.empty: boxes.append([None]*5); continue
            q1,median,q3=values.quantile([.25,.5,.75]); iqr=q3-q1; low=max(values.min(),q1-1.5*iqr); high=min(values.max(),q3+1.5*iqr); boxes.append(_values([low,q1,median,q3,high]))
            if spec.show_outliers: outliers.extend([[i,json_value(v)] for v in values[(values<low)|(values>high)]])
        option=_base(spec.title,spec.legend); option.update({"xAxis":{"type":"category","data":_values(categories)},"yAxis":{"type":"value"},"series":[{"name":spec.value,"type":"boxplot","data":boxes},{"name":"Outliers","type":"scatter","data":outliers}]})
        return PreparedChart(option,source,len(boxes)+len(outliers),False,warnings)
    raise ChartValidationError("Unsupported chart type.")

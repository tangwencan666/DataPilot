import pandas as pd
import pytest
from pydantic import TypeAdapter, ValidationError
from app.charts.errors import ChartValidationError, InvalidColumnError, InvalidColumnTypeError, NoDataError, TooManyPointsError, TooManySeriesError
from app.charts.schemas import ChartSpec
from app.charts.transformer import prepare_chart
from app.config import Settings

adapter=TypeAdapter(ChartSpec); settings=Settings()
def spec(payload): return adapter.validate_python(payload)
def frame(): return pd.DataFrame({"region":["N","S","N","S"],"sales":[10,20,30,40],"cost":[2,4,8,16],"date":pd.to_datetime(["2024-01-01","2024-01-15","2024-02-01","2024-02-20"])})

@pytest.mark.parametrize("payload",[
 {"type":"BAR","title":"Bar","category":"region","metric":"sales"},
 {"type":"LINE","title":"Line","x":"date","y":"sales","frequency":"month"},
 {"type":"AREA","title":"Area","x":"date","y":"sales","frequency":"day"},
 {"type":"PIE","title":"Pie","category":"region","metric":"sales"},
 {"type":"SCATTER","title":"Scatter","x":"sales","y":"cost"},
 {"type":"HISTOGRAM","title":"Histogram","column":"sales","bins":5},
 {"type":"BOXPLOT","title":"Box","value":"sales","category":"region"},
])
def test_supported_charts(payload):
    result=prepare_chart(frame(),spec(payload),settings); assert result.rendered_count>0; assert result.option["series"]

def test_bar_aggregation_sort_and_limit():
    result=prepare_chart(frame(),spec({"type":"BAR","title":"x","category":"region","metric":"sales","sort":"desc","limit":1}),settings)
    assert result.option["xAxis"]["data"]==["S"]; assert result.option["series"][0]["data"]==[60]

def test_line_month_and_multi_series():
    result=prepare_chart(frame(),spec({"type":"LINE","title":"x","x":"date","y":"sales","series":"region","frequency":"month"}),settings)
    assert len(result.option["series"])==2; assert len(result.option["xAxis"]["data"])==2

def test_pie_other_slice():
    f=pd.DataFrame({"c":list("abcd"),"v":[4,3,2,1]}); result=prepare_chart(f,spec({"type":"PIE","title":"x","category":"c","metric":"v","limit":2}),settings)
    assert result.option["series"][0]["data"][-1]=={"name":"Other","value":3}

def test_scatter_sampling_is_deterministic():
    f=pd.DataFrame({"x":range(20),"y":range(20)}); limited=Settings(chart_max_points=5)
    a=prepare_chart(f,spec({"type":"SCATTER","title":"x","x":"x","y":"y"}),limited); b=prepare_chart(f,spec({"type":"SCATTER","title":"x","x":"x","y":"y"}),limited)
    assert a.sampled and a.rendered_count==5 and a.option==b.option

def test_histogram_counts():
    result=prepare_chart(frame(),spec({"type":"HISTOGRAM","title":"x","column":"sales","bins":5}),settings)
    assert sum(result.option["series"][0]["data"])==4

def test_boxplot_statistics_and_nulls():
    f=frame(); f.loc[0,"sales"]=None; result=prepare_chart(f,spec({"type":"BOXPLOT","title":"x","value":"sales","category":"region"}),settings)
    assert len(result.option["series"][0]["data"])==2

def test_invalid_column_and_type():
    with pytest.raises(InvalidColumnError): prepare_chart(frame(),spec({"type":"BAR","title":"x","category":"missing","metric":"sales"}),settings)
    with pytest.raises(InvalidColumnTypeError): prepare_chart(frame(),spec({"type":"SCATTER","title":"x","x":"region","y":"sales"}),settings)

def test_empty_data():
    with pytest.raises(NoDataError): prepare_chart(frame().iloc[:0],spec({"type":"BAR","title":"x","category":"region","metric":"sales"}),settings)

def test_too_many_series():
    f=pd.DataFrame({"x":range(21),"y":range(21),"s":[str(x) for x in range(21)]})
    with pytest.raises(TooManySeriesError): prepare_chart(f,spec({"type":"SCATTER","title":"x","x":"x","y":"y","series":"s"}),settings)

def test_category_result_and_configured_bin_limits():
    f=pd.DataFrame({"c":["a","b","c"],"v":[1,2,3]})
    with pytest.raises(ChartValidationError): prepare_chart(f,spec({"type":"BAR","title":"x","category":"c","metric":"v"}),Settings(chart_max_categories=2))
    with pytest.raises(ChartValidationError): prepare_chart(f,spec({"type":"HISTOGRAM","title":"x","column":"v","bins":10}),Settings(chart_max_histogram_bins=5))

def test_aggregated_point_limit():
    with pytest.raises(TooManyPointsError): prepare_chart(frame(),spec({"type":"LINE","title":"x","x":"date","y":"sales","frequency":"day"}),Settings(chart_max_result_rows=2))

@pytest.mark.parametrize("payload",[
 {"type":"HISTOGRAM","title":"x","column":"sales","bins":101},
 {"type":"BAR","title":"x","category":"region","metric":"sales","aggregation":"eval"},
 {"type":"LINE","title":"x","x":"date","y":"sales","frequency":"hour"},
 {"type":"BAR","title":"function(){alert(1)}","category":"region","metric":"sales"},
 {"type":"BAR","title":"x","category":"region","metric":"sales","formatter":"evil"},
 {"type":"BAR","title":"x","category":"region","metric":"sales","options":{"series":[]}},
 {"type":"BAR","title":"x"*201,"category":"region","metric":"sales"},
 {"type":"PIE","title":"x","category":"region","metric":"sales","limit":13},
])
def test_schema_rejects_unsafe_or_invalid(payload):
    with pytest.raises(ValidationError): spec(payload)

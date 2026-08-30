from io import BytesIO

def upload(client, content=b"region,sales,date,cost\nNorth,10,2024-01-01,2\nSouth,20,2024-02-01,4\nNorth,30,2024-02-02,8\n"):
    return client.post("/api/v1/datasets",files={"file":("sales.csv",BytesIO(content),"text/csv")}).json()["id"]

def test_chart_crud_and_persistence(client):
    dataset_id=upload(client); payload={"type":"BAR","title":"Sales","category":"region","metric":"sales","aggregation":"sum"}
    created=client.post(f"/api/v1/datasets/{dataset_id}/charts",json=payload); assert created.status_code==201
    body=created.json(); assert body["echarts_option"]["series"][0]["data"]==[40,20]
    chart_id=body["chart_id"]; listing=client.get(f"/api/v1/datasets/{dataset_id}/charts").json(); assert listing["total"]==1
    detail=client.get(f"/api/v1/datasets/{dataset_id}/charts/{chart_id}"); assert detail.json()["status"]=="READY"
    assert client.delete(f"/api/v1/datasets/{dataset_id}/charts/{chart_id}").status_code==204
    missing=client.get(f"/api/v1/datasets/{dataset_id}/charts/{chart_id}"); assert missing.status_code==404 and missing.json()["code"]=="CHART_NOT_FOUND"

def test_dataset_and_chart_not_found(client):
    payload={"type":"BAR","title":"Sales","category":"region","metric":"sales"}
    assert client.post("/api/v1/datasets/missing/charts",json=payload).status_code==404

def test_invalid_spec_and_column(client):
    dataset_id=upload(client)
    invalid=client.post(f"/api/v1/datasets/{dataset_id}/charts",json={"type":"BAR","title":"x","category":"region","metric":"sales","raw_option":{}})
    assert invalid.status_code==422 and invalid.json()["code"]=="CHART_VALIDATION_FAILED"
    column=client.post(f"/api/v1/datasets/{dataset_id}/charts",json={"type":"SCATTER","title":"x","x":"region","y":"sales"})
    assert column.status_code==422 and column.json()["code"]=="CHART_INVALID_COLUMN_TYPE"

def test_no_data(client):
    dataset_id=upload(client,b"region,sales\n")
    response=client.post(f"/api/v1/datasets/{dataset_id}/charts",json={"type":"BAR","title":"x","category":"region","metric":"sales"})
    assert response.status_code==422 and response.json()["code"]=="CHART_NO_DATA"

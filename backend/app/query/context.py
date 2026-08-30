from app.models import Dataset, DatasetProfile


class DatasetSchemaContextBuilder:
    table_name = "dataset"

    def build(self, dataset: Dataset, profile: DatasetProfile | None) -> dict:
        profile_columns = profile.profile_json.get("columns", []) if profile and profile.profile_json else []
        fallback = dataset.metadata_json.get("columns", [])
        columns = []
        for item in (profile_columns or fallback)[:200]:
            column = {
                "name": item.get("name"),
                "physical_dtype": item.get("physical_dtype", item.get("dtype", "unknown")),
                "semantic_type": item.get("semantic_type", "UNKNOWN"),
                "missing_ratio": item.get("missing_ratio", 0),
                "sample_values": item.get("sample_values", [])[:3],
            }
            if item.get("numeric"):
                column["numeric_range"] = {"min": item["numeric"].get("min"), "max": item["numeric"].get("max")}
            if item.get("categorical"):
                column["top_values"] = [value.get("value") for value in item["categorical"].get("top_values", [])[:5]]
            columns.append(column)
        return {"dataset_name": dataset.name, "table_name": self.table_name, "columns": columns}

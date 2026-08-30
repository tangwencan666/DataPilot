from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd

from app.query.executor import json_value


def test_analysis_serialization_edge_types() -> None:
    assert json_value(float("nan")) is None
    assert json_value(float("inf")) is None
    assert json_value(pd.NA) is None
    assert json_value(pd.NaT) is None
    assert json_value(np.int64(3)) == 3
    assert json_value(np.float64(2.5)) == 2.5
    assert json_value(Decimal("1.25")) == 1.25
    assert json_value(pd.Timestamp("2024-01-01")).startswith("2024-01-01")
    assert json_value(pd.Timedelta("2 days")) == "2 days 00:00:00"

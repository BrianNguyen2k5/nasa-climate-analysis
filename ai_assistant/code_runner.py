from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .code_sanitizer import validate_runner_compatibility


FORBIDDEN_NAMES = {
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
}

FORBIDDEN_ATTR_ROOTS = {"os", "sys", "subprocess", "requests", "socket", "pathlib", "shutil"}


@dataclass
class ExecutionResult:
    ok: bool
    message: str
    fig_json: dict[str, Any] | None = None
    table_preview: list[dict[str, Any]] | None = None
    validation_reason: str | None = None
    validation_detail: str | None = None


def _is_valid_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    return True


def _sequence_has_values(values: Any) -> bool:
    if values is None:
        return False
    if isinstance(values, (str, bytes)):
        return bool(values)
    try:
        return any(_is_valid_value(item) for item in values)
    except TypeError:
        return _is_valid_value(values)


def _figure_has_visible_data(fig: Any) -> bool:
    for trace in getattr(fig, "data", []):
        trace_type = getattr(trace, "type", "")
        if trace_type in {"bar", "scatter", "scattergl", "line"}:
            if _sequence_has_values(getattr(trace, "x", None)) and _sequence_has_values(getattr(trace, "y", None)):
                return True
        elif trace_type in {"pie"}:
            if _sequence_has_values(getattr(trace, "values", None)):
                return True
        else:
            if _sequence_has_values(getattr(trace, "z", None)) or _sequence_has_values(getattr(trace, "y", None)):
                return True
    return False


def validate_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Code phê duyệt không được dùng import.")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ValueError(f"Code phê duyệt không được dùng `{node.id}`.")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in FORBIDDEN_ATTR_ROOTS:
                raise ValueError(f"Code phê duyệt không được truy cập `{node.value.id}`.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr.lower()
            if attr_name in {"to_csv", "to_excel", "to_json", "to_parquet", "to_pickle", "read_csv", "read_excel", "write", "savefig"}:
                raise ValueError("Code phê duyệt không được đọc/ghi file hoặc xuất dữ liệu ra ngoài.")


def _execute_validated_code(
    code: str,
    safe_globals: dict[str, Any],
    safe_locals: dict[str, Any],
) -> None:
    exec(code, safe_globals, safe_locals)


def execute_chart_code(code: str, df: pd.DataFrame) -> ExecutionResult:
    runner_validation = validate_runner_compatibility(code)
    if not runner_validation.valid:
        return ExecutionResult(
            False,
            runner_validation.message,
            validation_reason=runner_validation.reason,
            validation_detail=runner_validation.detail or None,
        )

    try:
        validate_code(code)
        safe_globals = {
            "df": df.copy(),
            "pd": pd,
            "np": np,
            "px": px,
            "go": go,
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "dict": dict,
                "enumerate": enumerate,
                "float": float,
                "int": int,
                "len": len,
                "list": list,
                "max": max,
                "min": min,
                "range": range,
                "round": round,
                "set": set,
                "sorted": sorted,
                "str": str,
                "sum": sum,
                "tuple": tuple,
                "zip": zip,
            },
        }
        safe_locals: dict[str, Any] = {}
        _execute_validated_code(code, safe_globals, safe_locals)
        fig = safe_locals.get("fig") or safe_globals.get("fig")
        if fig is None:
            return ExecutionResult(False, "Code phải tạo biến `fig` là Plotly Figure.")
        if not _figure_has_visible_data(fig):
            return ExecutionResult(False, "Biểu đồ được tạo nhưng không có dữ liệu hiển thị. Hãy kiểm tra lại điều kiện lọc, tên địa điểm/vùng/năm, hoặc cột được dùng để vẽ.")

        table_preview = None
        for value in list(safe_locals.values()) + list(safe_globals.values()):
            if isinstance(value, pd.DataFrame) and value is not df:
                table_preview = json.loads(value.head(20).to_json(orient="records", force_ascii=False))
                break

        return ExecutionResult(
            ok=True,
            message="Thực thi thành công trên dữ liệu local.",
            fig_json=json.loads(fig.to_json()),
            table_preview=table_preview,
        )
    except Exception as error:
        return ExecutionResult(False, str(error))

from __future__ import annotations

import ast
import json
import re
import textwrap
import unicodedata
from dataclasses import dataclass


LOCATION_VALUE_ALIASES = {
    "Buôn Ma Thuột": "Buon Ma Thuot",
    "Buon Ma Thuot": "Buon Ma Thuot",
    "Bu?n Ma Thu?t": "Buon Ma Thuot",
    "TP.Hồ Chí Minh": "Ho Chi Minh City",
    "TP.H? Ch? Minh": "Ho Chi Minh City",
    "TP H? Ch? Minh": "Ho Chi Minh City",
    "TP. Hồ Chí Minh": "Ho Chi Minh City",
    "TP Hồ Chí Minh": "Ho Chi Minh City",
    "Thành phố Hồ Chí Minh": "Ho Chi Minh City",
    "Hồ Chí Minh": "Ho Chi Minh City",
}

INCOMPLETE_AI_EDIT_MESSAGE = (
    "AI không trả về mã Python đầy đủ. Code hiện tại được giữ nguyên, "
    "vui lòng thử lại."
)
UNCHANGED_AI_EDIT_MESSAGE = (
    "AI chưa trả về thay đổi code. Code hiện tại được giữ nguyên."
)
RUNNER_INCOMPATIBLE_MESSAGE = (
    "Code AI trả về sử dụng lệnh không được hỗ trợ trong môi trường local. "
    "Code hiện tại được giữ nguyên."
)
MISSING_FIG_MESSAGE = (
    "Code AI trả về không còn tạo biến biểu đồ fig. "
    "Code hiện tại được giữ nguyên."
)
EDIT_SCOPE_VIOLATION_MESSAGE = (
    "AI đã thay đổi các phần ngoài phạm vi yêu cầu. "
    "Code hiện tại được giữ nguyên."
)

TITLE_ONLY = "TITLE_ONLY"
YEAR_ONLY = "YEAR_ONLY"
LOCATION_ONLY = "LOCATION_ONLY"
CHART_TYPE_ONLY = "CHART_TYPE_ONLY"
LABEL_ONLY = "LABEL_ONLY"
COMPLEX_OR_UNKNOWN = "COMPLEX_OR_UNKNOWN"

RUNNER_ROOT_NAMES = {"df", "pd", "np", "px", "go"}
RUNNER_SAFE_BUILTINS = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "range",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
}
UNSAFE_BUILTINS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
FORBIDDEN_OUTPUT_NAMES = {"display", "print"}
FORBIDDEN_NAMESPACES = {
    "IPython",
    "matplotlib",
    "plt",
    "st",
    "streamlit",
}
CHART_CONSTRUCTORS = {
    "go.Figure",
    "px.bar",
    "px.line",
    "px.scatter",
}
AGGREGATION_METHODS = {"agg", "count", "mean", "sum"}


@dataclass(frozen=True)
class AIEditValidationResult:
    valid: bool
    reason: str
    message: str
    detail: str = ""


def _validation_failure(
    reason: str,
    message: str = INCOMPLETE_AI_EDIT_MESSAGE,
    detail: str = "",
) -> AIEditValidationResult:
    return AIEditValidationResult(False, reason, message, detail)


def _normalized_words(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    normalized = normalized.replace("đ", "d")
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_placeholder(value: str, tree: ast.AST) -> bool:
    normalized = _normalized_words(value)
    placeholder_phrases = (
        r"\brest\s+unchanged\b",
        r"\brest\s+of\s+(?:the\s+)?code\b",
        r"\bsame\s+as\s+above\b",
        r"\bphan\s+con\s+lai\s+giu\s+nguyen\b",
        r"\bgiu\s+nguyen\s+phan\s+con\s+lai\b",
        r"\bcode\s+con\s+lai\b",
        r"\bplaceholder\b",
    )
    if any(re.search(pattern, normalized) for pattern in placeholder_phrases):
        return True
    if any(
        re.fullmatch(r"\s*#\s*(?:\.{3}|…)\s*", line)
        for line in value.splitlines()
    ):
        return True
    return any(
        isinstance(node, ast.Constant) and node.value is Ellipsis
        for node in ast.walk(tree)
    )


def _meaningful_top_level_statements(tree: ast.Module) -> list[ast.stmt]:
    return [
        statement
        for statement in tree.body
        if not isinstance(statement, ast.Pass)
        and not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, (str, type(Ellipsis)))
        )
    ]


def _assigns_name(tree: ast.AST, name: str) -> bool:
    return any(
        isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Store)
        for node in ast.walk(tree)
    )


def validate_ai_edit_candidate(
    source_code: str,
    candidate_code: str,
) -> AIEditValidationResult:
    """Validate that an AI edit is a complete replacement program."""
    source = str(source_code or "").strip()
    candidate = str(candidate_code or "").strip()
    if not candidate:
        return _validation_failure("empty")
    if candidate in {"...", "…"}:
        return _validation_failure("placeholder")

    try:
        candidate_tree = ast.parse(candidate)
    except SyntaxError:
        return _validation_failure("syntax_invalid")

    if _contains_placeholder(candidate, candidate_tree):
        return _validation_failure("placeholder")
    if any(isinstance(node, ast.Pass) for node in ast.walk(candidate_tree)):
        return _validation_failure("placeholder")

    candidate_statements = _meaningful_top_level_statements(candidate_tree)
    if not candidate_statements:
        return _validation_failure("fragment")

    try:
        source_tree = ast.parse(source)
    except SyntaxError:
        source_tree = None

    if source_tree is not None:
        if ast.dump(source_tree, include_attributes=False) == ast.dump(
            candidate_tree,
            include_attributes=False,
        ):
            return _validation_failure("unchanged", UNCHANGED_AI_EDIT_MESSAGE)

        source_statements = _meaningful_top_level_statements(source_tree)
        if len(source_statements) >= 2:
            minimum_statement_count = max(
                2,
                (len(source_statements) * 3 + 4) // 5,
            )
            if len(candidate_statements) < minimum_statement_count:
                return _validation_failure("fragment")

    return AIEditValidationResult(True, "valid", "")


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _root_name(node: ast.AST) -> str:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else ""


def _runner_failure(reason: str, detail: str) -> AIEditValidationResult:
    if reason == "missing_fig":
        return _validation_failure(reason, MISSING_FIG_MESSAGE)

    if reason == "forbidden_output_call":
        if detail.endswith(".show"):
            message = (
                f"Không thể chạy code vì `{detail}()` không được hỗ trợ. "
                "Ứng dụng sẽ tự hiển thị biến `fig`."
            )
        elif detail == "print":
            message = (
                "Không thể chạy code vì `print()` không được hỗ trợ "
                "trong môi trường local."
            )
        elif detail == "display":
            message = (
                "Không thể chạy code vì `display()` không được hỗ trợ. "
                "Ứng dụng sẽ tự hiển thị biến `fig`."
            )
        elif detail.endswith("write_html"):
            message = (
                "Không thể chạy code vì `write_html()` không được hỗ trợ "
                "trong môi trường local."
            )
        else:
            message = RUNNER_INCOMPATIBLE_MESSAGE
    elif reason == "forbidden_namespace":
        namespace = detail.split(".", 1)[0]
        message = (
            f"Không thể chạy code vì namespace `{namespace}` không có "
            "trong runner. Chỉ cần tạo biến `fig`."
        )
    elif reason == "import_not_allowed":
        message = (
            "Không thể chạy code vì `import` không được hỗ trợ. Runner đã "
            "cung cấp sẵn `df`, `pd`, `np`, `px` và `go`."
        )
    elif reason == "unsafe_builtin":
        message = (
            f"Không thể chạy code vì `{detail}()` không được hỗ trợ "
            "trong môi trường local."
        )
    elif reason == "unknown_runtime_name":
        message = (
            f"Không thể chạy code vì `{detail}` không tồn tại trong runner. "
            "Chỉ dùng `df`, `pd`, `np`, `px`, `go` và biến local hợp lệ."
        )
    elif reason == "missing_dataframe":
        message = (
            "Code phải sử dụng DataFrame `df` có sẵn trong môi trường local."
        )
    else:
        message = RUNNER_INCOMPATIBLE_MESSAGE
    return _validation_failure(reason, message, detail)


def _output_call_detail(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        if call.func.id in FORBIDDEN_OUTPUT_NAMES:
            return call.func.id
        return ""
    if isinstance(call.func, ast.Attribute):
        dotted = _dotted_name(call.func)
        if call.func.attr in {"show", "write_html"}:
            return dotted
    return ""


def validate_runner_compatibility(
    candidate_code: str,
    *,
    require_fig: bool = True,
) -> AIEditValidationResult:
    """Validate code against the names and rendering contract of the runner."""
    candidate = _extract_code_payload(str(candidate_code or ""))
    try:
        tree = ast.parse(candidate)
    except SyntaxError:
        return _validation_failure("syntax_invalid")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return _runner_failure("import_not_allowed", "import")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        output_detail = _output_call_detail(node)
        if output_detail:
            return _runner_failure(
                "forbidden_output_call",
                output_detail,
            )
        if isinstance(node.func, ast.Name):
            if node.func.id in UNSAFE_BUILTINS:
                return _runner_failure("unsafe_builtin", node.func.id)
        elif isinstance(node.func, ast.Attribute):
            root = _root_name(node.func)
            if root in FORBIDDEN_NAMESPACES:
                return _runner_failure(
                    "forbidden_namespace",
                    _dotted_name(node.func),
                )

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in FORBIDDEN_NAMESPACES
        ):
            return _runner_failure("forbidden_namespace", node.id)

    if require_fig and not _assigns_name(tree, "fig"):
        return _runner_failure("missing_fig", "fig")
    if require_fig and not any(
        isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id == "df"
        for node in ast.walk(tree)
    ):
        return _runner_failure("missing_dataframe", "df")

    local_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    local_names.update(
        node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)
    )
    local_names.update(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    allowed_names = RUNNER_ROOT_NAMES | RUNNER_SAFE_BUILTINS | local_names
    unknown_names = sorted(
        {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id not in allowed_names
        }
    )
    if unknown_names:
        return _runner_failure("unknown_runtime_name", unknown_names[0])

    return AIEditValidationResult(True, "valid", "")


def _node_columns(node: ast.AST) -> set[str]:
    columns: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Subscript):
            slice_node = child.slice
            if isinstance(slice_node, ast.Constant) and isinstance(
                slice_node.value,
                str,
            ):
                columns.add(slice_node.value)
        elif isinstance(child, ast.Attribute) and child.attr in {
            "location_name",
            "year",
        }:
            columns.add(child.attr)
    return columns


def _canonical_dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


@dataclass(frozen=True)
class CodeStructuralSignature:
    imports: tuple[str, ...]
    chart_constructor: str
    x: str
    y: str
    color: str
    title: str
    labels: str
    accessed_columns: tuple[str, ...]
    year_filters: tuple[str, ...]
    location_filters: tuple[str, ...]
    groupby_calls: tuple[str, ...]
    aggregation_calls: tuple[str, ...]
    assigned_names: tuple[str, ...]
    has_fig: bool
    output_calls: tuple[str, ...]


def extract_code_structural_signature(code: str) -> CodeStructuralSignature:
    tree = ast.parse(str(code or ""))
    imports = tuple(
        sorted(
            _canonical_dump(node)
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        )
    )
    chart_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _dotted_name(node.func) in CHART_CONSTRUCTORS
    ]
    chart_call = chart_calls[0] if chart_calls else None
    chart_keywords = {
        keyword.arg: _canonical_dump(keyword.value)
        for keyword in (chart_call.keywords if chart_call else [])
        if keyword.arg
    }
    chart_data_columns = {
        keyword.value.value
        for keyword in (chart_call.keywords if chart_call else [])
        if keyword.arg in {"x", "y", "color"}
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    }
    filter_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Compare, ast.Call))
    ]
    groupby_calls = tuple(
        sorted(
            _canonical_dump(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _dotted_name(node.func).endswith(".groupby")
        )
    )
    aggregation_calls = tuple(
        sorted(
            _canonical_dump(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in AGGREGATION_METHODS
        )
    )
    output_calls = tuple(
        sorted(
            detail
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            if (detail := _output_call_detail(node))
        )
    )
    assigned_names = tuple(
        sorted(
            {
                node.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Store)
            }
        )
    )
    return CodeStructuralSignature(
        imports=imports,
        chart_constructor=(
            _dotted_name(chart_call.func) if chart_call else ""
        ),
        x=chart_keywords.get("x", ""),
        y=chart_keywords.get("y", ""),
        color=chart_keywords.get("color", ""),
        title=chart_keywords.get("title", ""),
        labels=chart_keywords.get("labels", ""),
        accessed_columns=tuple(
            sorted(_node_columns(tree) | chart_data_columns)
        ),
        year_filters=tuple(
            sorted(
                _canonical_dump(node)
                for node in filter_nodes
                if "year" in _node_columns(node)
            )
        ),
        location_filters=tuple(
            sorted(
                _canonical_dump(node)
                for node in filter_nodes
                if "location_name" in _node_columns(node)
            )
        ),
        groupby_calls=groupby_calls,
        aggregation_calls=aggregation_calls,
        assigned_names=assigned_names,
        has_fig="fig" in assigned_names,
        output_calls=output_calls,
    )


def classify_ai_edit_request(edit_request: str) -> str:
    normalized = _normalized_words(edit_request)
    title_requested = bool(
        re.search(
            r"\b(?:doi|sua|dat)\s+(?:ten\s+bieu\s+do|tieu\s+de|title)\b",
            normalized,
        )
    )
    year_requested = bool(
        re.search(r"\b(?:19|20)\d{2}\b", normalized)
        or re.search(r"\b(?:nam|year|giai\s+doan)\b", normalized)
    )
    location_requested = bool(
        re.search(
            r"\b(?:location_name|dia\s+diem|thanh\s+pho|tinh|"
            r"ha\s+noi|can\s+tho|ho\s+chi\s+minh|hue|da\s+nang)\b",
            normalized,
        )
    )
    chart_type_requested = bool(
        re.search(
            r"\b(?:px\.)?(?:line|bar|scatter)\b",
            normalized,
        )
        or re.search(
            r"\bbieu\s+do\s+(?:duong|cot|phan\s+tan)\b",
            normalized,
        )
    ) and not title_requested
    label_requested = bool(
        re.search(r"\b(?:label|labels|nhan\s+truc|nhan)\b", normalized)
    )

    requested_scopes = [
        scope
        for scope, requested in (
            (TITLE_ONLY, title_requested),
            (YEAR_ONLY, year_requested),
            (LOCATION_ONLY, location_requested),
            (CHART_TYPE_ONLY, chart_type_requested),
            (LABEL_ONLY, label_requested),
        )
        if requested
    ]
    return (
        requested_scopes[0]
        if len(requested_scopes) == 1
        else COMPLEX_OR_UNKNOWN
    )


def _allowed_scope_sentinel() -> ast.Constant:
    return ast.Constant(value="__AI_EDIT_ALLOWED_CHANGE__")


def _is_allowed_scope_sentinel(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and node.value == "__AI_EDIT_ALLOWED_CHANGE__"
    )


class _EditScopeNormalizer(ast.NodeTransformer):
    def __init__(self, scope: str) -> None:
        self.scope = scope

    def _column_is_allowed(self, node: ast.AST) -> bool:
        columns = _node_columns(node)
        if self.scope == YEAR_ONLY:
            return bool(columns) and columns <= {"year"}
        if self.scope == LOCATION_ONLY:
            return bool(columns) and columns <= {"location_name"}
        return False

    def visit_Compare(self, node: ast.Compare):
        if self._column_is_allowed(node):
            return _allowed_scope_sentinel()
        return self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        if self._column_is_allowed(node):
            return _allowed_scope_sentinel()
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if (
            self.scope in {YEAR_ONLY, LOCATION_ONLY}
            and self._column_is_allowed(node)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"between", "isin"}
        ):
            return _allowed_scope_sentinel()

        node = self.generic_visit(node)
        if (
            self.scope == CHART_TYPE_ONLY
            and _dotted_name(node.func) in CHART_CONSTRUCTORS
        ):
            node.func = ast.Name(
                id="__AI_EDIT_CHART_CONSTRUCTOR__",
                ctx=ast.Load(),
            )

        title_allowed = self.scope in {
            TITLE_ONLY,
            YEAR_ONLY,
            LOCATION_ONLY,
        }
        for keyword in node.keywords:
            if title_allowed and keyword.arg in {"title", "title_text"}:
                keyword.value = _allowed_scope_sentinel()
            if self.scope == LABEL_ONLY and keyword.arg in {
                "labels",
                "xaxis_title",
                "yaxis_title",
            }:
                keyword.value = _allowed_scope_sentinel()
        node.keywords.sort(key=lambda keyword: keyword.arg or "")
        return node


def _scope_normalized_dump(code: str, scope: str) -> str:
    tree = ast.parse(str(code or ""))
    normalized = _EditScopeNormalizer(scope).visit(tree)
    ast.fix_missing_locations(normalized)
    return _canonical_dump(normalized)


def validate_ai_edit_scope(
    source_code: str,
    candidate_code: str,
    edit_request: str,
) -> AIEditValidationResult:
    scope = classify_ai_edit_request(edit_request)
    if scope == COMPLEX_OR_UNKNOWN:
        return AIEditValidationResult(True, "valid", "", scope)
    try:
        source_dump = _scope_normalized_dump(source_code, scope)
        candidate_dump = _scope_normalized_dump(candidate_code, scope)
    except SyntaxError:
        return _validation_failure("syntax_invalid")
    if source_dump == candidate_dump:
        return AIEditValidationResult(True, "valid", "", scope)
    scope_labels = {
        TITLE_ONLY: "tiêu đề",
        YEAR_ONLY: "năm",
        LOCATION_ONLY: "địa điểm",
        CHART_TYPE_ONLY: "loại biểu đồ",
        LABEL_ONLY: "nhãn",
    }
    detail = (
        f"Yêu cầu chỉ đổi {scope_labels[scope]} nhưng AI đã thay đổi "
        "logic hoặc cấu trúc khác."
    )
    return _validation_failure(
        "scope_violation",
        EDIT_SCOPE_VIOLATION_MESSAGE + f" {detail}",
        detail,
    )


def validate_ai_edit_for_application(
    source_code: str,
    candidate_code: str,
    edit_request: str,
) -> AIEditValidationResult:
    for validation in (
        validate_ai_edit_candidate(source_code, candidate_code),
        validate_runner_compatibility(candidate_code),
        validate_ai_edit_scope(
            source_code,
            candidate_code,
            edit_request,
        ),
    ):
        if not validation.valid:
            return validation
    return AIEditValidationResult(True, "valid", "")


def _extract_code_payload(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    fence_match = re.search(r"```(?:python|json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fence_match:
        stripped = fence_match.group(1).strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict) and isinstance(parsed.get("code"), str):
            return parsed["code"]
    except Exception:
        pass

    triple_match = re.search(r'"code"\s*:\s*"""(.*?)"""', stripped, re.DOTALL)
    if triple_match:
        return triple_match.group(1).strip()

    quoted_match = re.search(r'"code"\s*:\s*"(.*?)"\s*,\s*"(?:chart_title|suggestions|answer)"', stripped, re.DOTALL)
    if quoted_match:
        try:
            return json.loads('"' + quoted_match.group(1) + '"')
        except Exception:
            return quoted_match.group(1).replace('\\n', '\n')

    code_key_index = stripped.find('"code"')
    if code_key_index >= 0:
        tail = stripped[code_key_index:]
        first_newline = tail.find("\n")
        if first_newline >= 0:
            stripped = tail[first_newline + 1:]

    return stripped


def _normalize_indentation(code: str) -> str:
    dedented = textwrap.dedent(code).strip()
    normalized_lines = []
    for line in dedented.splitlines():
        if re.match(r"^\s+(#|df_|fig\b|[a-zA-Z_]\w*\s*=|[a-zA-Z_]\w*\.)", line):
            normalized_lines.append(line.lstrip())
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def sanitize_generated_code(
    code: str,
    *,
    preserve_imports: bool = False,
) -> str:
    """Return Python-only code allowed by the local runner."""
    if not code:
        return ""

    payload = _extract_code_payload(code)
    cleaned_lines = []
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if re.match(r"^(import|from)\s+", stripped):
            if preserve_imports:
                cleaned_lines.append(line)
            continue
        if stripped in {'"code":', "'code':", "code:", "{", "}"}:
            continue
        if re.match(r'^["\']?(answer|chart_title|suggestions)["\']?\s*:', stripped):
            break
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = cleaned.strip('`').strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.replace('\\n', '\n')
    cleaned = _normalize_indentation(cleaned)
    cleaned = cleaned.replace("location_vn", "location_name")
    for alias, canonical in LOCATION_VALUE_ALIASES.items():
        cleaned = cleaned.replace(alias, canonical)
    cleaned = cleaned.replace("plotly.express.", "px.")
    cleaned = cleaned.replace("plotly.graph_objects.", "go.")
    return cleaned

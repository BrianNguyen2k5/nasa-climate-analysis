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


@dataclass(frozen=True)
class AIEditValidationResult:
    valid: bool
    reason: str
    message: str


def _validation_failure(
    reason: str,
    message: str = INCOMPLETE_AI_EDIT_MESSAGE,
) -> AIEditValidationResult:
    return AIEditValidationResult(False, reason, message)


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

    from .code_runner import validate_code

    try:
        validate_code(candidate)
    except ValueError:
        return _validation_failure("unsafe_or_invalid")

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

        if _assigns_name(source_tree, "fig") and not _assigns_name(
            candidate_tree,
            "fig",
        ):
            return _validation_failure("missing_required_structure")

        source_statements = _meaningful_top_level_statements(source_tree)
        if len(source_statements) >= 2:
            minimum_statement_count = max(
                2,
                (len(source_statements) * 3 + 4) // 5,
            )
            if len(candidate_statements) < minimum_statement_count:
                return _validation_failure("fragment")

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


def sanitize_generated_code(code: str) -> str:
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
            continue
        if stripped in {'"code":', "'code':", "code:", "{", "}"}:
            continue
        if re.match(r'^["\']?(answer|chart_title|suggestions)["\']?\s*:', stripped):
            break
        if stripped in {'",', '],', ']'}:
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

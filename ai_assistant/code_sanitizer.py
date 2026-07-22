from __future__ import annotations

import json
import re
import textwrap


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

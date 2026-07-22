from __future__ import annotations

import re


def apply_simple_code_edit(code: str, instruction: str) -> str:
    """Apply deterministic small edits when the LLM returns text but no code."""
    if not code or not instruction:
        return code

    updated = code
    years = re.findall(r"\b(?:19\d{2}|20\d{2})\b", instruction)
    if len(years) >= 2:
        start_year, end_year = years[0], years[1]
        has_end_filter = re.search(r"df\[['\"]year['\"]\]\s*<=\s*(19\d{2}|20\d{2})", updated)
        updated = re.sub(r"df\[['\"]year['\"]\]\s*>=\s*(19\d{2}|20\d{2})", f"df['year'] >= {start_year}", updated)
        updated = re.sub(r"df\[['\"]year['\"]\]\s*<=\s*(19\d{2}|20\d{2})", f"df['year'] <= {end_year}", updated)
        if not has_end_filter:
            updated = re.sub(
                rf"\(df\['year'\]\s*>=\s*{start_year}\)",
                f"(df['year'] >= {start_year}) & (df['year'] <= {end_year})",
                updated,
                count=1,
            )
        updated = re.sub(r"(19\d{2}|20\d{2})\s*[-–]\s*(19\d{2}|20\d{2})", f"{start_year}-{end_year}", updated)

    return updated



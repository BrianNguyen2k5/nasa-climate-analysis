from __future__ import annotations

import base64
import math
from typing import Any

import numpy as np


def _as_list(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, dict) and "bdata" in values:
        try:
            dtype = np.dtype(values.get("dtype", "f8"))
            raw = base64.b64decode(values["bdata"])
            return np.frombuffer(raw, dtype=dtype).tolist()
        except Exception:
            return []
    if isinstance(values, list):
        return values
    try:
        return list(values)
    except TypeError:
        return [values]


def _valid_numbers(values: Any) -> list[float]:
    numbers: list[float] = []
    for value in _as_list(values):
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            numbers.append(number)
    return numbers


def _format_number(value: float) -> str:
    return f"{value:.2f}"


def summarize_chart(fig_json: dict[str, Any]) -> str:
    data = fig_json.get("data", []) if isinstance(fig_json, dict) else []
    layout = fig_json.get("layout", {}) if isinstance(fig_json, dict) else {}
    title_obj = layout.get("title", {}) if isinstance(layout, dict) else {}
    title = title_obj.get("text") if isinstance(title_obj, dict) else None

    if not data:
        return "Biểu đồ chưa có dữ liệu để kết luận."

    lines = []
    if title:
        lines.append(f"Biểu đồ '{title}' cho thấy:")
    else:
        lines.append("Biểu đồ cho thấy:")

    means: list[tuple[str, float]] = []
    trend_counts = {"tăng": 0, "giảm": 0, "gần như không đổi": 0}
    for index, trace in enumerate(data, start=1):
        if not isinstance(trace, dict):
            continue
        name = trace.get("name") or f"Chuỗi {index}"
        y_values = _valid_numbers(trace.get("y") or trace.get("values"))
        x_values = _as_list(trace.get("x") or trace.get("labels"))
        if not y_values:
            continue

        mean_value = sum(y_values) / len(y_values)
        min_value = min(y_values)
        max_value = max(y_values)
        first_value = y_values[0]
        last_value = y_values[-1]
        trend = "tăng" if last_value > first_value else "giảm" if last_value < first_value else "gần như không đổi"
        means.append((name, mean_value))
        trend_counts[trend] += 1

        detail = (
            f"- {name}: trung bình {_format_number(mean_value)}, "
            f"dao động từ {_format_number(min_value)} đến {_format_number(max_value)}, "
            f"xu hướng đầu-cuối {trend} ({_format_number(first_value)} -> {_format_number(last_value)})."
        )
        if x_values and len(x_values) == len(y_values):
            max_index = y_values.index(max_value)
            min_index = y_values.index(min_value)
            detail += f" Cao nhất tại {x_values[max_index]}, thấp nhất tại {x_values[min_index]}."
        lines.append(detail)

    if len(lines) == 1:
        return "Biểu đồ được tạo nhưng chưa có chuỗi số liệu đủ rõ để kết luận tự động."

    if len(means) >= 2:
        highest = max(means, key=lambda item: item[1])
        lowest = min(means, key=lambda item: item[1])
        spread = highest[1] - lowest[1]
        dominant_trend = max(trend_counts.items(), key=lambda item: item[1])[0]
        lines.append(
            f"Nhìn chung, {highest[0]} có mức trung bình cao nhất ({_format_number(highest[1])}), "
            f"còn {lowest[0]} thấp nhất ({_format_number(lowest[1])})."
        )
        lines.append(
            "\n**Kết luận chính:** "
            f"Biểu đồ cho thấy khác biệt nhiệt độ giữa các địa điểm là đáng chú ý, "
            f"với chênh lệch trung bình khoảng {_format_number(spread)}°C giữa nơi cao nhất và thấp nhất. "
            f"Xu hướng đầu-cuối phổ biến là {dominant_trend}; vì vậy có thể xem {highest[0]} là khu vực nổi bật về nền nhiệt cao, "
            f"trong khi {lowest[0]} đại diện cho nền nhiệt thấp hơn trong nhóm so sánh."
        )
    elif len(means) == 1:
        only = means[0]
        lines.append(
            "\n**Kết luận chính:** "
            f"Chuỗi {only[0]} có mức trung bình {_format_number(only[1])}. "
            "Cần so sánh thêm với địa điểm hoặc giai đoạn khác để rút ra kết luận đối chiếu rõ hơn."
        )

    return "\n".join(lines)

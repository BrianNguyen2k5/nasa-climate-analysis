from __future__ import annotations

import copy
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from ai_assistant.code_runner import execute_chart_code
from ai_assistant.code_sanitizer import (
    CHART_TYPE_ONLY,
    COMPLEX_OR_UNKNOWN,
    LABEL_ONLY,
    LOCATION_ONLY,
    TITLE_ONLY,
    YEAR_ONLY,
    classify_ai_edit_request,
    extract_code_structural_signature,
    sanitize_generated_code,
    validate_ai_edit_for_application,
    validate_ai_edit_scope,
    validate_runner_compatibility,
)
from ai_assistant.conversation_state import (
    PENDING_APPROVAL,
    SUCCESS,
    apply_ai_edit_response,
    create_code_proposal_message,
)
from ai_assistant.models import AIResponse
from tabs import tab_6_ai_assistant as ai_tab


SOURCE = """\
df_filtered = df[
    (df["year"] == 2015)
    & (df["location_name"].isin(["Hà Nội", "Ho Chi Minh City"]))
]
fig = px.line(
    df_filtered,
    x="date",
    y="T2M",
    color="location_name",
    title="Nhiệt độ trung bình năm 2015",
    labels={
        "date": "Ngày",
        "T2M": "Nhiệt độ trung bình",
        "location_name": "Địa điểm",
    },
)
"""


def changed_title(source: str = SOURCE) -> str:
    return source.replace(
        "Nhiệt độ trung bình năm 2015",
        "Xu hướng nhiệt độ trung bình",
    )


class RunnerCompatibilityTests(unittest.TestCase):
    def assert_reason(self, code: str, reason: str) -> None:
        result = validate_runner_compatibility(code)
        self.assertFalse(result.valid, result)
        self.assertEqual(result.reason, reason)

    def test_01_full_plotly_code_is_valid(self) -> None:
        code = SOURCE + '\nfig.update_layout(hovermode="x unified")\n'

        result = validate_runner_compatibility(code)

        self.assertTrue(result.valid)

    def test_02_output_calls_are_rejected(self) -> None:
        cases = {
            "print": SOURCE + "\nprint(fig)\n",
            "display": SOURCE + "\ndisplay(fig)\n",
            "fig.show": SOURCE + "\nfig.show()\n",
            "st.pyplot": SOURCE + "\nst.pyplot(fig)\n",
            "st.plotly_chart": SOURCE + "\nst.plotly_chart(fig)\n",
            "plt.show": SOURCE + "\nplt.show()\n",
            "streamlit.write": SOURCE + "\nstreamlit.write(fig)\n",
            "matplotlib.show": SOURCE + "\nmatplotlib.pyplot.show()\n",
            "IPython.display": SOURCE + "\nIPython.display.display(fig)\n",
            "write_html": SOURCE + '\nfig.write_html("chart.html")\n',
        }

        for detail, code in cases.items():
            with self.subTest(detail=detail):
                result = validate_runner_compatibility(code)
                self.assertFalse(result.valid)
                self.assertIn(
                    result.reason,
                    {"forbidden_namespace", "forbidden_output_call"},
                )
                self.assertIn(detail.split(".")[0], result.message)

    def test_03_import_is_rejected(self) -> None:
        self.assert_reason(
            "import streamlit as st\n" + SOURCE,
            "import_not_allowed",
        )

    def test_04_px_line_and_go_figure_are_valid(self) -> None:
        go_code = """\
df_chart = df.groupby("year")["T2M"].mean().reset_index()
fig = go.Figure(
    data=[go.Bar(x=df_chart["year"], y=df_chart["T2M"])]
)
fig.update_layout(title="Nhiệt độ")
"""

        self.assertTrue(validate_runner_compatibility(SOURCE).valid)
        self.assertTrue(validate_runner_compatibility(go_code).valid)

    def test_05_missing_fig_is_rejected(self) -> None:
        self.assert_reason(
            'df_filtered = df[df["year"] == 2015]',
            "missing_fig",
        )

    def test_06_unknown_runtime_root_is_rejected(self) -> None:
        self.assert_reason(
            'fig = sns.lineplot(data=df, x="date", y="T2M")',
            "unknown_runtime_name",
        )

    def test_07_unsafe_builtins_are_rejected(self) -> None:
        for builtin_call in (
            'open("file.txt")',
            'eval("1 + 1")',
            'exec("x = 1")',
            'compile("x = 1", "x.py", "exec")',
            "input()",
            '__import__("os")',
        ):
            with self.subTest(call=builtin_call):
                result = validate_runner_compatibility(
                    SOURCE + f"\nvalue = {builtin_call}\n"
                )
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "unsafe_builtin")

    def test_07b_code_must_use_runner_dataframe(self) -> None:
        result = validate_runner_compatibility(
            "fig = go.Figure(data=[go.Bar(x=[1], y=[2])])"
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_dataframe")


class EditScopeTests(unittest.TestCase):
    def test_08_request_classification(self) -> None:
        cases = {
            "Đổi tên biểu đồ thành Xu hướng nhiệt độ": TITLE_ONLY,
            "Đổi năm 2015 thành 2025": YEAR_ONLY,
            "Đổi 'Hà Nội' thành 'Ha Noi'": LOCATION_ONLY,
            "Đổi biểu đồ đường thành biểu đồ cột": CHART_TYPE_ONLY,
            "Sửa labels của biểu đồ": LABEL_ONLY,
            "Đổi năm và đổi tên biểu đồ": COMPLEX_OR_UNKNOWN,
            "Làm biểu đồ tốt hơn": COMPLEX_OR_UNKNOWN,
        }

        for request, expected in cases.items():
            with self.subTest(request=request):
                self.assertEqual(classify_ai_edit_request(request), expected)

    def test_09_structural_signature_extracts_required_components(self) -> None:
        signature = extract_code_structural_signature(SOURCE)

        self.assertEqual(signature.chart_constructor, "px.line")
        self.assertIn("T2M", signature.accessed_columns)
        self.assertIn("year", signature.accessed_columns)
        self.assertIn("location_name", signature.accessed_columns)
        self.assertTrue(signature.year_filters)
        self.assertTrue(signature.location_filters)
        self.assertEqual(signature.assigned_names, ("df_filtered", "fig"))
        self.assertTrue(signature.has_fig)
        self.assertEqual(signature.output_calls, ())

    def test_10_title_only_allows_only_title_and_formatting(self) -> None:
        title_only = changed_title()
        reformatted = """\
df_filtered=df[(df["year"]==2015)&(df["location_name"].isin(
    ["Hà Nội","Ho Chi Minh City"]
))]
fig=px.line(
    df_filtered,
    labels={"date":"Ngày","T2M":"Nhiệt độ trung bình","location_name":"Địa điểm"},
    title="Xu hướng nhiệt độ trung bình",
    color="location_name",
    y="T2M",
    x="date",
)
"""

        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                title_only,
                "Đổi tên biểu đồ thành 'Xu hướng nhiệt độ trung bình'.",
            ).valid
        )
        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                reformatted,
                "Đổi tên biểu đồ thành 'Xu hướng nhiệt độ trung bình'.",
            ).valid
        )

    def test_11_title_only_rejects_unrequested_semantic_changes(self) -> None:
        candidates = {
            "groupby": changed_title().replace(
                "fig = px.line(",
                'df_filtered = df_filtered.groupby("date")["T2M"].mean().reset_index()\n'
                "fig = px.line(",
            ),
            "chart_type": changed_title().replace("px.line(", "px.scatter("),
            "filter": changed_title().replace(
                '    & (df["location_name"].isin(["Hà Nội", "Ho Chi Minh City"]))\n',
                "",
            ),
            "metric": changed_title().replace('y="T2M"', 'y="T2M_MAX"'),
        }

        for change, candidate in candidates.items():
            with self.subTest(change=change):
                result = validate_ai_edit_scope(
                    SOURCE,
                    candidate,
                    "Đổi tên biểu đồ thành 'Xu hướng nhiệt độ trung bình'.",
                )
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "scope_violation")

    def test_12_year_only_allows_single_year_and_range_changes(self) -> None:
        single_year = SOURCE.replace("2015", "2025")
        year_range = SOURCE.replace(
            'df["year"] == 2015',
            '(df["year"] >= 2015) & (df["year"] <= 2025)',
        ).replace(
            "Nhiệt độ trung bình năm 2015",
            "Nhiệt độ trung bình 2015-2025",
        )

        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                single_year,
                "Đổi năm 2015 thành 2025.",
            ).valid
        )
        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                year_range,
                "Lọc từ năm 2015 đến 2025.",
            ).valid
        )

    def test_13_year_only_rejects_chart_type_change(self) -> None:
        candidate = SOURCE.replace("2015", "2025").replace(
            "px.line(",
            "px.bar(",
        )

        result = validate_ai_edit_scope(
            SOURCE,
            candidate,
            "Đổi năm 2015 thành 2025.",
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "scope_violation")

    def test_14_location_only_allows_literal_but_not_groupby(self) -> None:
        location_only = SOURCE.replace("Hà Nội", "Ha Noi")
        extra_groupby = location_only.replace(
            "fig = px.line(",
            'df_filtered = df_filtered.groupby("date")["T2M"].mean().reset_index()\n'
            "fig = px.line(",
        )

        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                location_only,
                "Đổi 'Hà Nội' thành 'Ha Noi'.",
            ).valid
        )
        result = validate_ai_edit_scope(
            SOURCE,
            extra_groupby,
            "Đổi 'Hà Nội' thành 'Ha Noi'.",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "scope_violation")

    def test_15_chart_type_only_allows_constructor_not_metric(self) -> None:
        chart_type_only = SOURCE.replace("px.line(", "px.bar(")
        changed_metric = chart_type_only.replace('y="T2M"', 'y="T2M_MAX"')

        self.assertTrue(
            validate_ai_edit_scope(
                SOURCE,
                chart_type_only,
                "Đổi biểu đồ đường thành biểu đồ cột.",
            ).valid
        )
        result = validate_ai_edit_scope(
            SOURCE,
            changed_metric,
            "Đổi biểu đồ đường thành biểu đồ cột.",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "scope_violation")

    def test_16_label_only_preserves_data_pipeline(self) -> None:
        candidate = SOURCE.replace(
            '"T2M": "Nhiệt độ trung bình"',
            '"T2M": "Nhiệt độ (°C)"',
        )

        result = validate_ai_edit_scope(
            SOURCE,
            candidate,
            "Sửa labels thành Nhiệt độ (°C).",
        )

        self.assertTrue(result.valid)

    def test_17_complex_request_is_not_over_restricted(self) -> None:
        candidate = SOURCE.replace("2015", "2025").replace(
            "Nhiệt độ trung bình năm 2025",
            "Xu hướng nhiệt độ 2025",
        )

        result = validate_ai_edit_scope(
            SOURCE,
            candidate,
            "Đổi năm 2015 thành 2025 và đổi tên biểu đồ.",
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.detail, COMPLEX_OR_UNKNOWN)


class StateAndUIIntegrityTests(unittest.TestCase):
    @staticmethod
    def proposal() -> dict:
        proposal = create_code_proposal_message("Code ban đầu", SOURCE)
        proposal.update(
            {
                "status": SUCCESS,
                "result": {"old": True},
                "error": "old error",
                "executed_code": SOURCE,
                "revision": 4,
                "edit_history": [{"answer": "old"}],
            }
        )
        return proposal

    def test_18_runner_and_scope_failures_do_not_mutate_state(self) -> None:
        cases = (
            (
                changed_title() + "\nprint(fig)\n",
                "Đổi tên biểu đồ.",
            ),
            (
                changed_title().replace("px.line(", "px.scatter("),
                "Đổi tên biểu đồ.",
            ),
        )

        for candidate, request in cases:
            with self.subTest(request=request):
                proposal = self.proposal()
                before = copy.deepcopy(proposal)
                _, applied = apply_ai_edit_response(
                    [proposal],
                    proposal["id"],
                    candidate,
                    edit_instruction=request,
                    edit_answer="Đã sửa.",
                    source_code=SOURCE,
                )
                self.assertFalse(applied)
                self.assertEqual(proposal, before)

    def test_19_valid_title_edit_updates_once(self) -> None:
        proposal = self.proposal()

        updated, applied = apply_ai_edit_response(
            [proposal],
            proposal["id"],
            changed_title(),
            edit_instruction="Đổi tên biểu đồ.",
            edit_answer="Đã đổi tiêu đề.",
            source_code=SOURCE,
        )

        self.assertTrue(applied)
        self.assertEqual(updated["revision"], 5)
        self.assertEqual(updated["status"], PENDING_APPROVAL)
        self.assertIsNone(updated["result"])
        self.assertIsNone(updated["error"])
        self.assertIsNone(updated["executed_code"])

    def test_20_application_validation_order(self) -> None:
        runner_failure = validate_ai_edit_for_application(
            SOURCE,
            changed_title() + "\nprint(fig)\n",
            "Đổi tên biểu đồ.",
        )
        scope_failure = validate_ai_edit_for_application(
            SOURCE,
            changed_title().replace("px.line(", "px.scatter("),
            "Đổi tên biểu đồ.",
        )

        self.assertEqual(runner_failure.reason, "forbidden_output_call")
        self.assertEqual(scope_failure.reason, "scope_violation")


class _FakeStreamlit:
    def __init__(
        self,
        proposal: dict,
        editor_code: str,
        instruction: str,
    ) -> None:
        self.session_state = SimpleNamespace(ai_messages=[proposal])
        self.editor_code = editor_code
        self.instruction = instruction
        self.warnings: list[str] = []
        self.rerun = Mock()

    @staticmethod
    def markdown(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def caption(*_args, **_kwargs) -> None:
        return None

    def text_area(self, *_args, **_kwargs) -> str:
        return self.editor_code

    def text_input(self, *_args, **_kwargs) -> str:
        return self.instruction

    @staticmethod
    def columns(spec):
        return [nullcontext() for _ in spec]

    @staticmethod
    def spinner(*_args, **_kwargs):
        return nullcontext()

    @staticmethod
    def button(label, *_args, **_kwargs) -> bool:
        return label == "Nhờ AI sửa code"

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class UIFlowTests(unittest.TestCase):
    def run_edit(
        self,
        *,
        editor_code: str,
        instruction: str,
        response_code: str,
    ):
        proposal = create_code_proposal_message("Code ban đầu", SOURCE)
        fake_st = _FakeStreamlit(proposal, editor_code, instruction)
        persist = Mock()
        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(
                ai_tab,
                "ask_groq",
                return_value=AIResponse(
                    answer="Đã sửa.",
                    code=response_code,
                ),
            ),
            patch.object(ai_tab, "_persist_active_messages", persist),
        ):
            ai_tab._render_code_review(
                proposal["id"],
                None,
                SimpleNamespace(),
                "dataset context",
            )
        return proposal, fake_st, persist

    def test_21_invalid_runner_and_scope_have_no_persist_or_rerun(self) -> None:
        cases = (
            changed_title() + "\nprint(fig)\n",
            changed_title().replace("px.line(", "px.scatter("),
            "import streamlit as st\n" + changed_title(),
        )
        for candidate in cases:
            with self.subTest(candidate=candidate[-40:]):
                proposal, fake_st, persist = self.run_edit(
                    editor_code=SOURCE,
                    instruction="Đổi tên biểu đồ.",
                    response_code=candidate,
                )
                self.assertEqual(proposal["revision"], 1)
                self.assertEqual(proposal["current_code"], SOURCE)
                persist.assert_not_called()
                fake_st.rerun.assert_not_called()
                self.assertEqual(len(fake_st.warnings), 1)

    def test_22_valid_title_edit_persists_and_reruns_once(self) -> None:
        proposal, fake_st, persist = self.run_edit(
            editor_code=SOURCE,
            instruction="Đổi tên biểu đồ.",
            response_code=changed_title(),
        )

        self.assertEqual(proposal["revision"], 2)
        self.assertEqual(
            proposal["current_code"],
            sanitize_generated_code(changed_title()),
        )
        persist.assert_called_once()
        fake_st.rerun.assert_called_once()
        self.assertEqual(fake_st.warnings, [])

    def test_23_manual_editor_source_is_preserved(self) -> None:
        manual_source = SOURCE.replace(
            "df_filtered =",
            "# MANUAL MARKER\ndf_filtered =",
        )
        candidate = changed_title(manual_source)

        proposal, fake_st, persist = self.run_edit(
            editor_code=manual_source,
            instruction="Đổi tên biểu đồ.",
            response_code=candidate,
        )

        self.assertIn("# MANUAL MARKER", proposal["current_code"])
        self.assertIn('df["year"] == 2015', proposal["current_code"])
        self.assertEqual(proposal["revision"], 2)
        persist.assert_called_once()
        fake_st.rerun.assert_called_once()

    def test_24_valid_edit_executes_without_output_calls(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2015-01-01", "2015-01-02"],
                "year": [2015, 2015],
                "location_name": ["Hà Nội", "Ho Chi Minh City"],
                "T2M": [20.0, 28.0],
            }
        )
        code = sanitize_generated_code(changed_title())

        result = execute_chart_code(code, df)

        self.assertTrue(result.ok, result.message)
        self.assertIsNotNone(result.fig_json)


if __name__ == "__main__":
    unittest.main()

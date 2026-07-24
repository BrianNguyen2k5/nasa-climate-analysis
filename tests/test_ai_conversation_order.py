from __future__ import annotations

import copy
import inspect
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_assistant.conversation_state import (
    FAILED,
    PENDING_APPROVAL,
    SUCCESS,
    create_code_proposal_message,
)
from ai_assistant.conversation_view import (
    build_answer_number_map,
    build_conversation_turns,
    find_latest_assistant_answer_id,
    should_expand_message,
    sort_turns_newest_first,
)
from tabs import tab_6_ai_assistant as ai_tab


def message(
    message_id: str,
    role: str,
    content: str,
    request_id: str | None = None,
) -> dict:
    result = {
        "id": message_id,
        "role": role,
        "kind": "text",
        "content": content,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    if request_id is not None:
        result["request_id"] = request_id
    return result


def complete_turn(name: str) -> list[dict]:
    return [
        message(f"user-{name}", "user", f"Prompt {name}", name),
        message(f"answer-{name}", "assistant", f"Answer {name}", name),
    ]


class ConversationGroupingTests(unittest.TestCase):
    def test_01_complete_requests_display_newest_first(self) -> None:
        messages = complete_turn("A") + complete_turn("B") + complete_turn("C")

        turns = sort_turns_newest_first(
            build_conversation_turns(messages)
        )

        self.assertEqual(
            [turn.request_id for turn in turns],
            ["C", "B", "A"],
        )
        for turn in turns:
            self.assertEqual(
                [item["role"] for item in turn.messages],
                ["user", "assistant"],
            )

    def test_02_same_request_id_and_legacy_duplicates_stay_together(
        self,
    ) -> None:
        messages = [
            message("u-a", "user", "Prompt", "A"),
            message("a-a-1", "assistant", "Answer 1", "A"),
            message("a-a-2", "assistant", "Answer 2", "A"),
        ]

        turns = build_conversation_turns(messages)

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].request_id, "A")
        self.assertEqual(
            [item["id"] for item in turns[0].messages],
            ["u-a", "a-a-1", "a-a-2"],
        )
        self.assertEqual(turns[0].original_indexes, (0, 1, 2))

    def test_03_legacy_messages_group_by_adjacency(self) -> None:
        messages = [
            message("orphan", "assistant", "Orphan"),
            message("u-a", "user", "Prompt A"),
            message("a-a-1", "assistant", "Answer A1"),
            message("a-a-2", "assistant", "Answer A2"),
            message("u-b", "user", "Prompt B"),
            message("a-b", "assistant", "Answer B"),
        ]

        turns = build_conversation_turns(messages)

        self.assertEqual(len(turns), 3)
        self.assertEqual(
            [[item["id"] for item in turn.messages] for turn in turns],
            [
                ["orphan"],
                ["u-a", "a-a-1", "a-a-2"],
                ["u-b", "a-b"],
            ],
        )

    def test_04_missing_request_id_can_follow_request_group(self) -> None:
        messages = [
            message("u-a", "user", "Prompt A", "A"),
            message("a-a", "assistant", "Legacy answer without ID"),
        ]

        turns = build_conversation_turns(messages)

        self.assertEqual(len(turns), 1)
        self.assertEqual(
            [item["id"] for item in turns[0].messages],
            ["u-a", "a-a"],
        )

    def test_05_latest_index_wins_when_timestamps_are_equal(self) -> None:
        messages = complete_turn("A") + complete_turn("B")

        first = sort_turns_newest_first(
            build_conversation_turns(messages)
        )
        second = sort_turns_newest_first(
            build_conversation_turns(messages)
        )

        self.assertEqual(
            [turn.request_id for turn in first],
            ["B", "A"],
        )
        self.assertEqual(first, second)

    def test_06_grouping_and_sorting_do_not_mutate_input(self) -> None:
        messages = complete_turn("A") + complete_turn("B")
        before = copy.deepcopy(messages)

        turns = build_conversation_turns(messages)
        sort_turns_newest_first(turns)

        self.assertEqual(messages, before)
        self.assertEqual(
            [item["id"] for item in messages],
            ["user-A", "answer-A", "user-B", "answer-B"],
        )

    def test_07_empty_history_is_safe(self) -> None:
        self.assertEqual(build_conversation_turns([]), [])
        self.assertEqual(sort_turns_newest_first([]), [])
        self.assertIsNone(find_latest_assistant_answer_id([]))


class AnswerNumberAndExpansionTests(unittest.TestCase):
    def test_08_answer_numbers_follow_original_chronology(self) -> None:
        messages = complete_turn("A") + complete_turn("B") + complete_turn("C")

        numbers = build_answer_number_map(messages)
        display = sort_turns_newest_first(
            build_conversation_turns(messages)
        )
        display_numbers = [
            numbers[item["id"]]
            for turn in display
            for item in turn.messages
            if item["role"] == "assistant"
        ]

        self.assertEqual(display_numbers, [3, 2, 1])

    def test_09_code_proposal_and_duplicate_answers_keep_stable_numbers(
        self,
    ) -> None:
        proposal = create_code_proposal_message(
            "Code",
            "fig = px.line(df, x='year', y='T2M')",
        )
        proposal.update({"id": "proposal", "request_id": "B"})
        messages = (
            complete_turn("A")
            + [message("u-b", "user", "Prompt B", "B"), proposal]
            + [
                message("u-c", "user", "Prompt C", "C"),
                message("a-c-1", "assistant", "Answer C1", "C"),
                message("a-c-2", "assistant", "Answer C2", "C"),
            ]
        )

        numbers = build_answer_number_map(messages)

        self.assertEqual(numbers["answer-A"], 1)
        self.assertEqual(numbers["proposal"], 2)
        self.assertEqual(numbers["a-c-1"], 3)
        self.assertEqual(numbers["a-c-2"], 4)

    def test_10_latest_answer_and_old_text_expansion(self) -> None:
        messages = complete_turn("A") + complete_turn("B")
        latest_id = find_latest_assistant_answer_id(messages)

        self.assertEqual(latest_id, "answer-B")
        self.assertTrue(should_expand_message(messages[-1], latest_id))
        self.assertFalse(should_expand_message(messages[1], latest_id))

    def test_11_pending_and_failed_proposals_stay_open(self) -> None:
        pending = create_code_proposal_message(
            "Pending",
            "fig = px.line(df, x='year', y='T2M')",
        )
        failed = create_code_proposal_message(
            "Failed",
            "fig = px.line(df, x='year', y='T2M')",
        )
        failed["status"] = FAILED

        self.assertTrue(should_expand_message(pending, "newer-answer"))
        self.assertTrue(should_expand_message(failed, "newer-answer"))

    def test_12_success_proposal_opens_only_when_latest(self) -> None:
        proposal = create_code_proposal_message(
            "Success",
            "fig = px.line(df, x='year', y='T2M')",
        )
        proposal["status"] = SUCCESS

        self.assertTrue(
            should_expand_message(proposal, str(proposal["id"]))
        )
        self.assertFalse(
            should_expand_message(proposal, "newer-answer")
        )

    def test_13_adding_answer_changes_latest_without_mutation(self) -> None:
        messages = complete_turn("A")
        before = copy.deepcopy(messages)
        first_latest = find_latest_assistant_answer_id(messages)
        messages = messages + complete_turn("B")
        second_latest = find_latest_assistant_answer_id(messages)

        self.assertEqual(first_latest, "answer-A")
        self.assertEqual(second_latest, "answer-B")
        self.assertEqual(before, complete_turn("A"))

    def test_14_rerun_helpers_are_deterministic_and_side_effect_free(
        self,
    ) -> None:
        messages = complete_turn("A") + complete_turn("B")
        before = copy.deepcopy(messages)

        first = (
            sort_turns_newest_first(build_conversation_turns(messages)),
            build_answer_number_map(messages),
            find_latest_assistant_answer_id(messages),
        )
        second = (
            sort_turns_newest_first(build_conversation_turns(messages)),
            build_answer_number_map(messages),
            find_latest_assistant_answer_id(messages),
        )

        self.assertEqual(first, second)
        self.assertEqual(messages, before)


class _RenderStreamlit:
    def __init__(self, messages: list[dict]) -> None:
        self.session_state = SimpleNamespace(ai_messages=messages)
        self.events: list[tuple] = []
        self.current_role = ""

    @contextmanager
    def chat_message(self, role: str):
        previous_role = self.current_role
        self.current_role = role
        self.events.append(("chat", role))
        yield
        self.current_role = previous_role

    def markdown(self, content: str) -> None:
        self.events.append(("markdown", self.current_role, content))


class ConversationRenderTests(unittest.TestCase):
    def render(self, messages: list[dict]):
        fake_st = _RenderStreamlit(messages)
        answers: list[tuple] = []
        proposals: list[tuple] = []

        def render_answer(message, label, *, expanded=False):
            answers.append((message["id"], label, expanded))

        def render_proposal(
            message,
            number,
            latest_answer_id,
            *_args,
        ):
            proposals.append(
                (
                    message["id"],
                    number,
                    should_expand_message(message, latest_answer_id),
                )
            )

        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(
                ai_tab,
                "_render_ai_response_detail",
                side_effect=render_answer,
            ),
            patch.object(
                ai_tab,
                "_render_code_proposal",
                side_effect=render_proposal,
            ),
        ):
            ai_tab._render_messages(None, SimpleNamespace(), "")
        return fake_st, answers, proposals

    def test_15_workspace_renders_newest_request_first(self) -> None:
        messages = complete_turn("A") + complete_turn("B") + complete_turn("C")

        fake_st, answers, _proposals = self.render(messages)

        user_prompts = [
            event[2]
            for event in fake_st.events
            if event[:2] == ("markdown", "user")
        ]
        self.assertEqual(user_prompts, ["Prompt C", "Prompt B", "Prompt A"])
        self.assertEqual(
            answers,
            [
                ("answer-C", "Xem câu trả lời AI #3", True),
                ("answer-B", "Xem câu trả lời AI #2", False),
                ("answer-A", "Xem câu trả lời AI #1", False),
            ],
        )

    def test_16_user_stays_immediately_before_matching_answer(self) -> None:
        messages = complete_turn("A") + complete_turn("B")

        fake_st, answers, _proposals = self.render(messages)

        self.assertEqual(
            fake_st.events,
            [
                ("chat", "user"),
                ("markdown", "user", "Prompt B"),
                ("chat", "assistant"),
                ("chat", "user"),
                ("markdown", "user", "Prompt A"),
                ("chat", "assistant"),
            ],
        )
        self.assertEqual(
            [item[0] for item in answers],
            ["answer-B", "answer-A"],
        )

    def test_17_unanswered_user_is_first_without_stealing_answer(
        self,
    ) -> None:
        messages = complete_turn("A") + [
            message("user-B", "user", "Prompt B", "B")
        ]

        fake_st, answers, _proposals = self.render(messages)

        self.assertEqual(
            fake_st.events[1],
            ("markdown", "user", "Prompt B"),
        )
        self.assertEqual(
            answers,
            [("answer-A", "Xem câu trả lời AI #1", True)],
        )

    def test_18_pending_old_proposal_remains_open(self) -> None:
        proposal = create_code_proposal_message(
            "Pending",
            "fig = px.line(df, x='year', y='T2M')",
        )
        proposal.update({"id": "proposal-A", "request_id": "A"})
        messages = [
            message("user-A", "user", "Prompt A", "A"),
            proposal,
        ] + complete_turn("B")

        _fake_st, answers, proposals = self.render(messages)

        self.assertEqual(
            answers,
            [("answer-B", "Xem câu trả lời AI #2", True)],
        )
        self.assertEqual(proposals, [("proposal-A", 1, True)])

    def test_19_render_is_side_effect_free(self) -> None:
        proposal = create_code_proposal_message(
            "Pending",
            "fig = px.line(df, x='year', y='T2M')",
        )
        proposal.update(
            {
                "id": "proposal-A",
                "request_id": "A",
                "revision": 7,
                "result": {"old": True},
                "error": "old",
            }
        )
        messages = [
            message("user-A", "user", "Prompt A", "A"),
            proposal,
        ]
        before = copy.deepcopy(messages)
        persist = Mock()
        model = Mock()
        execute = Mock()

        with (
            patch.object(ai_tab, "_persist_active_messages", persist),
            patch.object(ai_tab, "ask_groq", model),
            patch.object(ai_tab, "execute_chart_code", execute),
        ):
            self.render(messages)
            self.render(messages)

        self.assertEqual(messages, before)
        persist.assert_not_called()
        model.assert_not_called()
        execute.assert_not_called()

    def test_20_editor_widget_key_remains_message_id_plus_revision(
        self,
    ) -> None:
        source = inspect.getsource(ai_tab._render_code_review)

        self.assertIn(
            'f"ai_code_editor_{message_id}_{revision}"',
            source,
        )
        self.assertIn(
            'f"ai_run_code_{message_id}_{revision}"',
            source,
        )
        self.assertIn(
            'f"ai_request_fix_{message_id}_{revision}"',
            source,
        )

    def test_21_empty_workspace_does_not_crash(self) -> None:
        fake_st, answers, proposals = self.render([])

        self.assertEqual(fake_st.events, [])
        self.assertEqual(answers, [])
        self.assertEqual(proposals, [])


if __name__ == "__main__":
    unittest.main()

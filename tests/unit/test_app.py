"""Unit tests for the Chainlit app module."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app import (
    _PROFILE_TO_TASK_TYPE,
    _extract_step_summary,
    _handle_chat_message,
    _send_recommendations,
    _send_results,
    auth_callback,
    chat_profiles,
    on_chat_start,
    on_message,
    on_settings_update,
)
from src.evaluator import TaskType

# ---------------------------------------------------------------------------
# Async iterator helper for mocking llm.astream()
# ---------------------------------------------------------------------------

class MockAsyncIterator:
    """Async iterator that yields pre-defined chunks for testing astream()."""

    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks
        self._index = 0

    def __aiter__(self) -> AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


class TestAuthCallback:
    @pytest.mark.asyncio
    async def test_accepts_valid_credentials(self):
        with patch("src.app.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                auth_enabled=True,
                auth_admin_email="admin@test.dev",
                auth_admin_password="secret123",
            )
            result = await auth_callback("admin@test.dev", "secret123")
            assert result is not None
            assert result.identifier == "admin@test.dev"
            assert result.metadata["role"] == "admin"

    @pytest.mark.asyncio
    async def test_rejects_wrong_password(self):
        with patch("src.app.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                auth_enabled=True,
                auth_admin_email="admin@test.dev",
                auth_admin_password="secret123",
            )
            result = await auth_callback("admin@test.dev", "wrong")
            assert result is None

    @pytest.mark.asyncio
    async def test_rejects_wrong_email(self):
        with patch("src.app.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                auth_enabled=True,
                auth_admin_email="admin@test.dev",
                auth_admin_password="secret123",
            )
            result = await auth_callback("other@test.dev", "secret123")
            assert result is None

    @pytest.mark.asyncio
    async def test_accepts_any_username_when_auth_disabled(self):
        with patch("src.app.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(auth_enabled=False)
            result = await auth_callback("anyone", "")
            assert result is not None
            assert result.identifier == "anyone"


class TestExtractStepSummary:
    def test_route_input_mode(self):
        mode = MagicMock()
        mode.value = "prompt"
        result = _extract_step_summary("route_input", {"mode": mode})
        assert "Prompt" in result

    def test_route_input_with_phase(self):
        mode = MagicMock()
        mode.value = "prompt"
        phase = MagicMock()
        phase.value = "full"
        result = _extract_step_summary("route_input", {"mode": mode, "eval_phase": phase})
        assert "Prompt" in result
        assert "Full" in result

    def test_score_prompt(self):
        result = _extract_step_summary("score_prompt", {"overall_score": 75, "grade": "Good"})
        assert "75/100" in result

    def test_build_report(self):
        result = _extract_step_summary("build_report", {})
        assert result == "Report assembled"

    def test_unknown_node(self):
        result = _extract_step_summary("unknown_node", {"data": "value"})
        assert result is None

    def test_non_dict_state(self):
        result = _extract_step_summary("route_input", "not a dict")
        assert result is None


class TestSendRecommendations:
    @pytest.mark.asyncio
    async def test_sends_recommendations_when_similar_exist(self):
        similar = [
            {
                "input_text": "Write about cats for pet owners in a blog format",
                "rewritten_prompt": "As a pet expert...",
                "overall_score": 72,
                "grade": "Good",
                "distance": 0.15,
            },
        ]
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls, \
             patch("chainlit.File") as mock_file_cls, \
             patch("src.ui.results_display.generate_similarity_report", return_value="<html></html>"):
            await _send_recommendations({"similar_evaluations": similar})

            mock_message_cls.assert_called_once()
            call_kwargs = mock_message_cls.call_args[1]
            content = call_kwargs["content"]
            assert "Similar Past Evaluations" in content
            assert "Good" in content
            assert "72/100" in content
            mock_msg.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_recommendations_when_empty(self):
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            await _send_recommendations({"similar_evaluations": []})
            mock_message_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_recommendations_when_none(self):
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            await _send_recommendations({})
            mock_message_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_shows_max_three_recommendations(self):
        similar = [
            {
                "input_text": f"Prompt {i}",
                "rewritten_prompt": None,
                "overall_score": 50 + i * 10,
                "grade": "Good",
                "distance": 0.1 * i,
            }
            for i in range(5)
        ]
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            await _send_recommendations({"similar_evaluations": similar})

            content = mock_message_cls.call_args[1]["content"]
            # Should show max 3 items (numbered 1, 2, 3)
            assert "**1." in content
            assert "**2." in content
            assert "**3." in content

    @pytest.mark.asyncio
    async def test_attaches_html_file_when_rewritten_prompt_exists(self):
        similar = [
            {
                "input_text": "Write about dogs",
                "rewritten_prompt": "As a vet, write a detailed...",
                "overall_score": 72,
                "grade": "Good",
                "distance": 0.15,
            },
        ]
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls, \
             patch("chainlit.File") as mock_file_cls, \
             patch("src.ui.results_display.generate_similarity_report", return_value="<html></html>"):
            await _send_recommendations({"similar_evaluations": similar})

            # cl.File should be called once (one evaluation with rewritten_prompt)
            mock_file_cls.assert_called_once()
            file_call = mock_file_cls.call_args
            filename = file_call[1]["name"]
            assert filename.startswith("past-eval-1-")
            assert filename.endswith(".html")

            # Message should have elements
            call_kwargs = mock_message_cls.call_args[1]
            assert "elements" in call_kwargs
            assert len(call_kwargs["elements"]) == 1

            # Content should reference the file, not "Optimized version available"
            content = call_kwargs["content"]
            assert "Optimized version available" not in content
            assert "past-eval-1-" in content

    @pytest.mark.asyncio
    async def test_no_file_when_no_rewritten_prompt(self):
        similar = [
            {
                "input_text": "Write about dogs",
                "rewritten_prompt": None,
                "overall_score": 50,
                "grade": "Needs Work",
                "distance": 0.20,
            },
        ]
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            await _send_recommendations({"similar_evaluations": similar})

            call_kwargs = mock_message_cls.call_args[1]
            # No elements key when no files
            assert "elements" not in call_kwargs

    @pytest.mark.asyncio
    async def test_multiple_files_for_multiple_rewritten_prompts(self):
        similar = [
            {
                "input_text": "Prompt 1",
                "rewritten_prompt": "Rewritten 1",
                "overall_score": 72,
                "grade": "Good",
                "distance": 0.10,
            },
            {
                "input_text": "Prompt 2",
                "rewritten_prompt": None,
                "overall_score": 50,
                "grade": "Needs Work",
                "distance": 0.20,
            },
            {
                "input_text": "Prompt 3",
                "rewritten_prompt": "Rewritten 3",
                "overall_score": 88,
                "grade": "Excellent",
                "distance": 0.25,
            },
        ]
        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls, \
             patch("chainlit.File") as mock_file_cls, \
             patch("src.ui.results_display.generate_similarity_report", return_value="<html></html>"):
            await _send_recommendations({"similar_evaluations": similar})

            # 2 files (items 1 and 3 have rewritten_prompt)
            assert mock_file_cls.call_count == 2
            call_kwargs = mock_message_cls.call_args[1]
            assert len(call_kwargs["elements"]) == 2


class TestChatProfiles:
    @pytest.mark.asyncio
    async def test_returns_seven_profiles(self):
        profiles = await chat_profiles()
        assert len(profiles) == 7
        names = [p.name for p in profiles]
        assert "General Task Prompts" in names
        assert "Email Creation Prompts" in names
        assert "Summarization Prompts" in names
        assert "Coding Task Prompts" in names
        assert "Exam Interview Agent Prompts" in names
        assert "LinkedIn Professional Post Prompts" in names
        assert "Test your optimized prompts" in names

    @pytest.mark.asyncio
    async def test_general_task_is_default(self):
        profiles = await chat_profiles()
        general = [p for p in profiles if p.name == "General Task Prompts"][0]
        assert general.default is True

    def test_profile_to_task_type_mapping(self):
        assert _PROFILE_TO_TASK_TYPE["General Task Prompts"] == TaskType.GENERAL
        assert _PROFILE_TO_TASK_TYPE["Email Creation Prompts"] == TaskType.EMAIL_WRITING
        assert _PROFILE_TO_TASK_TYPE["Summarization Prompts"] == TaskType.SUMMARIZATION


class TestOnChatStartTaskType:
    @pytest.mark.asyncio
    async def test_general_profile_sets_general_task_type(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            assert session_store["task_type"] == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_email_profile_sets_email_task_type(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Email Creation Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            assert session_store["task_type"] == TaskType.EMAIL_WRITING

    @pytest.mark.asyncio
    async def test_email_profile_welcome_mentions_email_criteria(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Email Creation Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "Email Creation Prompts" in content
            assert "Tone" in content or "tone" in content

    @pytest.mark.asyncio
    async def test_summarization_profile_sets_summarization_task_type(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Summarization Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            assert session_store["task_type"] == TaskType.SUMMARIZATION

    @pytest.mark.asyncio
    async def test_summarization_profile_welcome_mentions_summarization_criteria(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Summarization Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "Summarization Prompts" in content
            assert "source fidelity" in content.lower() or "information accuracy" in content.lower()

    @pytest.mark.asyncio
    async def test_general_profile_welcome_mentions_tcrei(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "General Task Prompts" in content
            assert "T.C.R.E.I." in content


class TestSendResultsDynamicFilename:
    @staticmethod
    def _make_mock_report():
        """Create a mock report with all required attributes."""
        mock_report = MagicMock()
        mock_report.structure_result = None
        mock_report.output_result = None
        mock_report.optimized_output_result = None
        mock_report.execution_count = 2
        mock_report.strategy_used = "enhanced (CoT+ToT+Meta)"
        mock_report.meta_assessment = None
        mock_report.tot_branches_data = None
        return mock_report

    @pytest.mark.asyncio
    async def test_dynamic_filename_is_short_uuid_based(self):
        mock_report = self._make_mock_report()

        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg), \
             patch("chainlit.File") as mock_file_cls, \
             patch("src.ui.results_display.generate_audit_report", return_value="<html></html>"):
            final_state = {
                "full_report": mock_report,
                "user_id": "admin@test.dev",
                "session_id": "abc12345-longer-id",
            }
            await _send_results(final_state)

            file_call = mock_file_cls.call_args
            filename = file_call[1]["name"] if "name" in file_call[1] else file_call[0][0]
            assert filename.startswith("audit-")
            assert filename.endswith(".html")
            # 8 hex chars between prefix and suffix: audit-XXXXXXXX.html
            hex_part = filename[len("audit-"):-len(".html")]
            assert len(hex_part) == 8
            assert all(c in "0123456789abcdef" for c in hex_part)

    @pytest.mark.asyncio
    async def test_dynamic_filename_defaults_for_missing_ids(self):
        mock_report = self._make_mock_report()

        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg), \
             patch("chainlit.File") as mock_file_cls, \
             patch("src.ui.results_display.generate_audit_report", return_value="<html></html>"):
            final_state = {
                "full_report": mock_report,
                # user_id and session_id not provided
            }
            await _send_results(final_state)

            file_call = mock_file_cls.call_args
            filename = file_call[1]["name"] if "name" in file_call[1] else file_call[0][0]
            # Same short UUID format regardless of missing IDs
            assert filename.startswith("audit-")
            assert filename.endswith(".html")

    @pytest.mark.asyncio
    async def test_dynamic_filename_unique_per_call(self):
        mock_report = self._make_mock_report()

        filenames = []
        for _ in range(2):
            mock_msg = AsyncMock()
            with patch("chainlit.Message", return_value=mock_msg), \
                 patch("chainlit.File") as mock_file_cls, \
                 patch("src.ui.results_display.generate_audit_report", return_value="<html></html>"):
                final_state = {
                    "full_report": mock_report,
                    "user_id": "user@special!chars.dev",
                    "session_id": "sess-1234",
                }
                await _send_results(final_state)

                file_call = mock_file_cls.call_args
                filename = file_call[1]["name"] if "name" in file_call[1] else file_call[0][0]
                filenames.append(filename)

        # Each call produces a unique filename
        assert filenames[0] != filenames[1]
        # No special chars leak into the filename
        for fn in filenames:
            assert "@" not in fn
            assert "!" not in fn

    @pytest.mark.asyncio
    async def test_summary_message_references_dynamic_filename(self):
        mock_report = self._make_mock_report()

        mock_msg = AsyncMock()
        with patch("chainlit.Message", return_value=mock_msg) as mock_message_cls, \
             patch("chainlit.File"), \
             patch("src.ui.results_display.generate_audit_report", return_value="<html></html>"):
            final_state = {
                "full_report": mock_report,
                "user_id": "testuser",
                "session_id": "abcd1234",
            }
            await _send_results(final_state)

            content = mock_message_cls.call_args[1]["content"]
            # Should reference the short UUID-based filename
            assert "audit-" in content
            assert ".html" in content


class TestOnChatStartLLMProvider:
    @pytest.mark.asyncio
    async def test_default_llm_provider_is_google(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            assert session_store["llm_provider"] == "google"

    @pytest.mark.asyncio
    async def test_welcome_message_shows_llm_provider(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "LLM Evaluator" in content
            assert "Gemini" in content

    @pytest.mark.asyncio
    async def test_label_map_stored_in_session(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            label_map = session_store.get("_llm_label_map", {})
            assert "google" in label_map.values()
            assert "anthropic" in label_map.values()


class TestOnSettingsUpdate:
    @pytest.mark.asyncio
    async def test_updates_provider_to_anthropic(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "_llm_label_map": {
                    "Google Gemini (gemini-2.5-flash)": "google",
                    "Anthropic Claude (claude-sonnet-4-20250514)": "anthropic",
                },
            }.get(k, d))

            await on_settings_update({"llm_provider": "Anthropic Claude (claude-sonnet-4-20250514)"})

            assert session_store["llm_provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_updates_provider_to_google(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "_llm_label_map": {
                    "Google Gemini (gemini-2.5-flash)": "google",
                    "Anthropic Claude (claude-sonnet-4-20250514)": "anthropic",
                },
            }.get(k, d))

            await on_settings_update({"llm_provider": "Google Gemini (gemini-2.5-flash)"})

            assert session_store["llm_provider"] == "google"

    @pytest.mark.asyncio
    async def test_sends_confirmation_message(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "_llm_label_map": {
                    "Google Gemini (gemini-2.5-flash)": "google",
                },
            }.get(k, d))

            await on_settings_update({"llm_provider": "Google Gemini (gemini-2.5-flash)"})

            content = mock_message_cls.call_args[1]["content"]
            assert "switched" in content.lower()
            assert "Google Gemini" in content

    @pytest.mark.asyncio
    async def test_defaults_to_google_for_unknown_label(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "_llm_label_map": {},
            }.get(k, d))

            await on_settings_update({"llm_provider": "Unknown Provider"})

            assert session_store["llm_provider"] == "google"

    @pytest.mark.asyncio
    async def test_chat_mode_updates_chat_provider(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg):
            session_store: dict = {}
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "_llm_label_map": {
                    "Google Gemini (gemini-2.5-flash)": "google",
                    "Anthropic Claude (claude-sonnet-4-20250514)": "anthropic",
                },
                "profile_mode": "chat",
            }.get(k, d))

            await on_settings_update({"llm_provider": "Anthropic Claude (claude-sonnet-4-20250514)"})

            assert session_store["chat_provider"] == "anthropic"
            assert "llm_provider" not in session_store


class TestWelcomeMessageExample:
    @pytest.mark.asyncio
    async def test_general_welcome_includes_general_example(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "Example Prompt" in content
            assert "Veterinarian Blog Article" in content
            assert "```" in content

    @pytest.mark.asyncio
    async def test_email_welcome_includes_email_example(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Email Creation Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "Follow-Up Email" in content

    @pytest.mark.asyncio
    async def test_summarization_welcome_includes_summarization_example(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "Summarization Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "Research Paper" in content

    @pytest.mark.asyncio
    async def test_welcome_includes_tcrei_dimensions(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "**[T] Task**" in content
            assert "**[C] Context**" in content
            assert "**[R] References**" in content
            assert "**[E/I] Constraints**" in content

    @pytest.mark.asyncio
    async def test_welcome_includes_estimated_score(self):
        mock_msg = AsyncMock()
        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg) as mock_message_cls:
            mock_session.set = MagicMock()
            mock_session.get = MagicMock(side_effect=lambda k, d=None: {
                "chat_profile": "General Task Prompts",
                "user": None,
            }.get(k, d))

            await on_chat_start()

            content = mock_message_cls.call_args[1]["content"]
            assert "88/100" in content


# ---------------------------------------------------------------------------
# _handle_chat_message streaming tests
# ---------------------------------------------------------------------------


class TestHandleChatMessageStreaming:
    """Tests for the streaming chat handler."""

    @pytest.mark.asyncio
    async def test_text_only_streaming(self):
        """Streaming with text-only chunks shows status then streams response."""
        chunk1 = MagicMock()
        chunk1.content = "Hello "
        chunk2 = MagicMock()
        chunk2.content = "world!"

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=MockAsyncIterator([chunk1, chunk2]))

        # Track all cl.Message instances created
        created_msgs: list[AsyncMock] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            created_msgs.append(m)
            return m

        mock_step = AsyncMock()

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("chainlit.Step", return_value=mock_step), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            session_store: dict = {"chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("Hi there")

            # First message is the status "thinking...", second is the streamed response
            assert len(created_msgs) >= 2
            status_msg = created_msgs[0]
            response_msg = created_msgs[1]
            assert "thinking" in status_msg.content.lower()
            # Status removed, response streamed
            status_msg.remove.assert_called()
            assert response_msg.stream_token.call_count == 2
            # Chat history should be updated
            assert len(session_store["chat_history"]) == 2

    @pytest.mark.asyncio
    async def test_thinking_and_text_streaming(self):
        """Streaming with thinking + text chunks creates Step and Message."""
        thinking_chunk = MagicMock()
        thinking_chunk.content = [{"type": "thinking", "thinking": "Let me think..."}]
        text_chunk = MagicMock()
        text_chunk.content = [{"type": "text", "text": "Here's the answer."}]

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(
            return_value=MockAsyncIterator([thinking_chunk, text_chunk])
        )

        created_msgs: list[AsyncMock] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            created_msgs.append(m)
            return m

        mock_step = AsyncMock()

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("chainlit.Step", return_value=mock_step), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            session_store: dict = {"chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("Explain this")

            # Step should have thinking streamed, response msg should have text
            mock_step.stream_token.assert_called()
            # Second message (response) gets text tokens
            response_msg = created_msgs[1]
            response_msg.stream_token.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Errors during streaming produce an error message."""
        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(side_effect=RuntimeError("Connection failed"))

        created_msgs: list[AsyncMock] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            created_msgs.append(m)
            return m

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            session_store: dict = {"chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("test")

            # Last message should contain the error
            error_msg = created_msgs[-1]
            assert "error" in error_msg.content.lower()

    @pytest.mark.asyncio
    async def test_chat_history_updated(self):
        """Chat history includes both user and assistant messages after streaming."""
        chunk = MagicMock()
        chunk.content = "Response"

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=MockAsyncIterator([chunk]))

        created_msgs: list[AsyncMock] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            created_msgs.append(m)
            return m

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("chainlit.Step", return_value=AsyncMock()), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            session_store: dict = {"chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("My question")

            history = session_store["chat_history"]
            assert history[0] == {"role": "human", "content": "My question"}
            assert history[1] == {"role": "assistant", "content": "Response"}

    @pytest.mark.asyncio
    async def test_no_text_sends_fallback(self):
        """When no text is streamed, the status message shows fallback."""
        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=MockAsyncIterator([]))

        created_msgs: list[AsyncMock] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            created_msgs.append(m)
            return m

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("chainlit.Step", return_value=AsyncMock()), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            session_store: dict = {"chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("test")

            # Status message should be updated with fallback text
            status_msg = created_msgs[0]
            status_msg.send.assert_called()
            status_msg.update.assert_called()
            assert status_msg.content == "(No response text)"

    @pytest.mark.asyncio
    async def test_status_message_shows_provider_name(self):
        """Status message displays the correct provider name."""
        chunk = MagicMock()
        chunk.content = "Hi"

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=MockAsyncIterator([chunk]))

        initial_contents: list[str] = []

        def make_msg(**kwargs: Any) -> AsyncMock:
            m = AsyncMock()
            m.content = kwargs.get("content", "")
            initial_contents.append(m.content)
            return m

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", side_effect=make_msg), \
             patch("chainlit.Step", return_value=AsyncMock()), \
             patch("src.ui.chat_handler._get_chat_llm", return_value=mock_llm):
            # Test with Anthropic provider
            session_store: dict = {"chat_provider": "anthropic", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await _handle_chat_message("test")

            # First message created should be the status with "Claude" in it
            assert "Claude" in initial_contents[0]


# ---------------------------------------------------------------------------
# on_message file attachment tests
# ---------------------------------------------------------------------------


class TestOnMessageFileAttachments:
    """Tests for file attachment processing in on_message chat mode."""

    @pytest.mark.asyncio
    async def test_chat_mode_processes_text_file(self):
        """Text file content is prepended to user input in chat mode."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("print('hello')")
            f.flush()
            tmp_path = f.name

        elem = MagicMock()
        elem.name = "script.py"
        elem.path = tmp_path

        message = MagicMock()
        message.content = "Explain this code"
        message.elements = [elem]

        mock_msg = AsyncMock()

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg), \
             patch("chainlit.Step", return_value=AsyncMock()), \
             patch("src.app._handle_chat_message", new_callable=AsyncMock) as mock_handler:
            session_store: dict = {"profile_mode": "chat", "chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await on_message(message)

            mock_handler.assert_called_once()
            call_args = mock_handler.call_args
            augmented_input = call_args[0][0] if call_args[0] else call_args[1].get("user_input", "")
            assert "print('hello')" in augmented_input
            assert "Explain this code" in augmented_input

    @pytest.mark.asyncio
    async def test_chat_mode_passes_image_blocks(self):
        """Image attachments are passed as image_blocks to the handler."""
        # Create a minimal image file
        with tempfile.NamedTemporaryFile(suffix=".png", mode="wb", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
            f.flush()
            tmp_path = f.name

        elem = MagicMock()
        elem.name = "photo.png"
        elem.path = tmp_path

        message = MagicMock()
        message.content = "What is in this image?"
        message.elements = [elem]

        with patch("chainlit.user_session") as mock_session, \
             patch("src.app._handle_chat_message", new_callable=AsyncMock) as mock_handler:
            session_store: dict = {"profile_mode": "chat", "chat_provider": "google", "chat_history": []}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await on_message(message)

            mock_handler.assert_called_once()
            call_kwargs = mock_handler.call_args[1]
            assert call_kwargs.get("image_blocks") is not None
            assert len(call_kwargs["image_blocks"]) == 1

    @pytest.mark.asyncio
    async def test_evaluator_mode_ignores_attachments(self):
        """In evaluator mode, file attachments are not processed."""
        message = MagicMock()
        message.content = "system prompt mode"
        message.elements = [MagicMock(name="file.py", path="/tmp/file.py")]

        mock_msg = AsyncMock()

        with patch("chainlit.user_session") as mock_session, \
             patch("chainlit.Message", return_value=mock_msg), \
             patch("src.app._handle_chat_message", new_callable=AsyncMock) as mock_handler:
            session_store: dict = {"profile_mode": "evaluator", "mode": MagicMock(value="prompt")}
            mock_session.get = MagicMock(side_effect=lambda k, d=None: session_store.get(k, d))
            mock_session.set = MagicMock(side_effect=lambda k, v: session_store.__setitem__(k, v))

            await on_message(message)

            # Chat handler should NOT be called in evaluator mode
            mock_handler.assert_not_called()

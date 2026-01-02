"""
LLM-based Focus Score Evaluator

Provides intelligent focus score evaluation using LLM instead of hardcoded rules.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .manager import get_llm_manager
from .prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class FocusEvaluator:
    """LLM-based focus score evaluator"""

    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.prompt_manager = get_prompt_manager()

    def _format_activities_detail(self, activities: List[Dict[str, Any]]) -> str:
        """
        Format activities into human-readable detail text

        Args:
            activities: List of activity dictionaries

        Returns:
            Formatted activities detail string
        """
        if not activities:
            return "No activities recorded"

        lines = []
        for i, activity in enumerate(activities, 1):
            title = activity.get("title", "Untitled Activity")
            description = activity.get("description", "")
            duration = activity.get("session_duration_minutes", 0)
            start_time = activity.get("start_time", "")
            end_time = activity.get("end_time", "")
            topics = activity.get("topic_tags", [])
            action_count = len(activity.get("source_action_ids", []))

            lines.append(f"\n### Activity {i}")
            lines.append(f"**Title**: {title}")
            if description:
                lines.append(f"**Description**: {description}")
            lines.append(f"**Time**: {start_time} - {end_time}")
            lines.append(f"**Duration**: {duration:.1f} minutes")
            lines.append(f"**Action Count**: {action_count}")
            if topics:
                lines.append(f"**Topics**: {', '.join(topics)}")

        return "\n".join(lines)

    def _collect_all_topics(self, activities: List[Dict[str, Any]]) -> List[str]:
        """
        Collect all unique topic tags from activities

        Args:
            activities: List of activity dictionaries

        Returns:
            List of unique topic tags
        """
        all_topics = set()
        for activity in activities:
            topics = activity.get("topic_tags", [])
            all_topics.update(topics)
        return sorted(list(all_topics))

    async def evaluate_focus(
        self,
        activities: List[Dict[str, Any]],
        session_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate focus score using LLM

        Args:
            activities: List of activity dictionaries from a work session
            session_info: Optional session metadata (start_time, end_time, etc.)

        Returns:
            Dictionary containing:
                - focus_score: 0-100 integer score
                - focus_level: "excellent" | "good" | "moderate" | "low"
                - dimension_scores: Dict of 5 dimension scores
                - analysis: Dict with strengths, weaknesses, suggestions
                - work_type: Type of work
                - is_focused_work: Boolean
                - distraction_percentage: 0-100
                - deep_work_minutes: Float
                - context_summary: String summary
        """
        if not activities:
            logger.warning("No activities provided for focus evaluation")
            return self._get_default_evaluation()

        # Calculate session metadata
        total_duration = sum(
            activity.get("session_duration_minutes", 0) for activity in activities
        )
        activity_count = len(activities)
        all_topics = self._collect_all_topics(activities)

        # Determine session time range
        if session_info:
            start_time = session_info.get("start_time", "")
            end_time = session_info.get("end_time", "")
        else:
            # Extract from activities
            start_times = [a.get("start_time") for a in activities if a.get("start_time")]
            end_times = [a.get("end_time") for a in activities if a.get("end_time")]
            start_time = min(start_times) if start_times else ""
            end_time = max(end_times) if end_times else ""

        # Format activities detail
        activities_detail = self._format_activities_detail(activities)

        # Get prompt template
        try:
            user_prompt_template = self.prompt_manager.get_prompt(
                "focus_score_evaluation", "user_prompt_template"
            )
            system_prompt = self.prompt_manager.get_prompt(
                "focus_score_evaluation", "system_prompt"
            )
        except Exception as e:
            logger.error(f"Failed to load focus evaluation prompts: {e}")
            return self._get_default_evaluation()

        # Fill in prompt template
        user_prompt = user_prompt_template.format(
            start_time=start_time,
            end_time=end_time,
            total_duration=f"{total_duration:.1f}",
            activity_count=activity_count,
            topic_tags=", ".join(all_topics) if all_topics else "None",
            activities_detail=activities_detail,
        )

        # Call LLM
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.llm_manager.chat_completion(
                messages,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                request_type="focus_evaluation",
            )

            content = response.get("content", "")

            # Parse JSON response
            evaluation = self._parse_llm_response(content)

            # Validate and normalize the evaluation
            evaluation = self._validate_evaluation(evaluation)

            logger.info(
                f"LLM focus evaluation completed: score={evaluation.get('focus_score')}, "
                f"level={evaluation.get('focus_level')}"
            )

            return evaluation

        except Exception as e:
            logger.error(f"LLM focus evaluation failed: {e}", exc_info=True)
            return self._get_default_evaluation()

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response

        Args:
            content: LLM response content

        Returns:
            Parsed evaluation dict
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content.strip()

        # Parse JSON
        try:
            evaluation = json.loads(json_str)
            return evaluation
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nContent: {content}")
            raise

    def _validate_evaluation(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize evaluation result

        Args:
            evaluation: Raw evaluation dict from LLM

        Returns:
            Validated and normalized evaluation dict
        """
        # Ensure focus_score is 0-100 integer
        focus_score = int(evaluation.get("focus_score", 50))
        focus_score = max(0, min(100, focus_score))
        evaluation["focus_score"] = focus_score

        # Normalize focus_level based on score
        score_to_level = {
            (80, 100): "excellent",
            (60, 79): "good",
            (40, 59): "moderate",
            (0, 39): "low",
        }
        for (min_score, max_score), level in score_to_level.items():
            if min_score <= focus_score <= max_score:
                evaluation["focus_level"] = level
                break

        # Ensure dimension_scores exist and are valid
        if "dimension_scores" not in evaluation:
            evaluation["dimension_scores"] = {}

        for dimension in [
            "topic_consistency",
            "duration_depth",
            "switching_rhythm",
            "work_quality",
            "goal_orientation",
        ]:
            if dimension not in evaluation["dimension_scores"]:
                evaluation["dimension_scores"][dimension] = focus_score
            else:
                score = int(evaluation["dimension_scores"][dimension])
                evaluation["dimension_scores"][dimension] = max(0, min(100, score))

        # Ensure analysis structure exists
        if "analysis" not in evaluation:
            evaluation["analysis"] = {}

        for key in ["strengths", "weaknesses", "suggestions"]:
            if key not in evaluation["analysis"]:
                evaluation["analysis"][key] = []

        # Ensure other fields have defaults
        evaluation.setdefault("work_type", "unclear")
        evaluation.setdefault("is_focused_work", focus_score >= 60)
        evaluation.setdefault("distraction_percentage", max(0, 100 - focus_score))
        evaluation.setdefault("deep_work_minutes", 0)
        evaluation.setdefault("context_summary", "")

        return evaluation

    def _get_default_evaluation(self) -> Dict[str, Any]:
        """
        Get default evaluation result (used when LLM fails)

        Returns:
            Default evaluation dict
        """
        return {
            "focus_score": 50,
            "focus_level": "moderate",
            "dimension_scores": {
                "topic_consistency": 50,
                "duration_depth": 50,
                "switching_rhythm": 50,
                "work_quality": 50,
                "goal_orientation": 50,
            },
            "analysis": {
                "strengths": [],
                "weaknesses": ["Unable to evaluate focus - using default score"],
                "suggestions": ["Please ensure LLM is properly configured"],
            },
            "work_type": "unclear",
            "is_focused_work": False,
            "distraction_percentage": 50,
            "deep_work_minutes": 0,
            "context_summary": "Focus evaluation unavailable",
        }

    async def evaluate_activity_focus(
        self, activity: Dict[str, Any], session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate focus score for a single activity using LLM

        Args:
            activity: Single activity dictionary containing title, description, duration, topics, actions
            session_context: Optional session context containing user_intent and related_todos

        Returns:
            Dictionary containing:
                - focus_score: 0-100 integer score
                - reasoning: Brief explanation of the score
                - work_type: Type of work
                - is_productive: Boolean indicating if this is productive work
        """
        if not activity:
            logger.warning("No activity provided for focus evaluation")
            return self._get_default_activity_evaluation()

        # Extract activity information
        title = activity.get("title", "Untitled Activity")
        description = activity.get("description", "")
        duration_minutes = activity.get("session_duration_minutes", 0)
        topics = activity.get("topic_tags", [])
        actions = activity.get("actions", [])
        action_count = len(actions)

        # Format actions summary
        actions_summary = self._format_actions_summary(actions)

        # Extract session context
        user_intent = ""
        related_todos_summary = ""
        if session_context:
            user_intent = session_context.get("user_intent", "") or ""
            related_todos = session_context.get("related_todos", [])
            if related_todos:
                todos_lines = []
                for todo in related_todos:
                    todo_title = todo.get("title", "")
                    todo_desc = todo.get("description", "")
                    if todo_desc:
                        todos_lines.append(f"- {todo_title}: {todo_desc}")
                    else:
                        todos_lines.append(f"- {todo_title}")
                related_todos_summary = "\n".join(todos_lines)

        # Get prompt template
        try:
            user_prompt_template = self.prompt_manager.get_prompt(
                "activity_focus_evaluation", "user_prompt_template"
            )
            system_prompt = self.prompt_manager.get_prompt(
                "activity_focus_evaluation", "system_prompt"
            )
        except Exception as e:
            logger.error(f"Failed to load activity focus evaluation prompts: {e}")
            return self._get_default_activity_evaluation()

        # Fill in prompt template
        user_prompt = user_prompt_template.format(
            title=title,
            description=description or "No description",
            duration_minutes=f"{duration_minutes:.1f}",
            topics=", ".join(topics) if topics else "None",
            action_count=action_count,
            actions_summary=actions_summary,
            user_intent=user_intent or "No work goal specified",
            related_todos=related_todos_summary or "No related todos",
        )

        # Call LLM
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.llm_manager.chat_completion(
                messages,
                max_tokens=500,
                temperature=0.3,  # Lower temperature for consistent evaluation
                request_type="activity_focus_evaluation",
            )

            content = response.get("content", "")

            # Parse JSON response
            evaluation = self._parse_activity_llm_response(content)

            # Validate and normalize the evaluation
            evaluation = self._validate_activity_evaluation(evaluation)

            logger.debug(
                f"Activity focus evaluation completed: score={evaluation.get('focus_score')}, "
                f"activity='{title[:50]}'"
            )

            return evaluation

        except Exception as e:
            logger.error(f"LLM activity focus evaluation failed: {e}", exc_info=True)
            return self._get_default_activity_evaluation()

    def _format_actions_summary(self, actions: List[Dict[str, Any]]) -> str:
        """
        Format actions into a concise summary

        Args:
            actions: List of action dictionaries

        Returns:
            Formatted actions summary string
        """
        if not actions:
            return "No actions recorded"

        lines = []
        for i, action in enumerate(actions[:5], 1):  # Limit to first 5 actions
            title = action.get("title", "Untitled")
            lines.append(f"{i}. {title}")

        if len(actions) > 5:
            lines.append(f"... and {len(actions) - 5} more actions")

        return "\n".join(lines)

    def _parse_activity_llm_response(self, content: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response for activity evaluation

        Args:
            content: LLM response content

        Returns:
            Parsed evaluation dict
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content.strip()

        # Parse JSON
        try:
            evaluation = json.loads(json_str)
            return evaluation
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse activity LLM JSON response: {e}\nContent: {content}"
            )
            raise

    def _validate_activity_evaluation(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize activity evaluation result

        Args:
            evaluation: Raw evaluation dict from LLM

        Returns:
            Validated and normalized evaluation dict
        """
        # Ensure focus_score is 0-100 integer
        focus_score = int(evaluation.get("focus_score", 50))
        focus_score = max(0, min(100, focus_score))
        evaluation["focus_score"] = focus_score

        # Ensure other required fields have defaults
        evaluation.setdefault("reasoning", "")
        evaluation.setdefault("work_type", "unclear")
        evaluation.setdefault("is_productive", focus_score >= 60)

        return evaluation

    def _get_default_activity_evaluation(self) -> Dict[str, Any]:
        """
        Get default activity evaluation result (used when LLM fails)

        Returns:
            Default evaluation dict
        """
        return {
            "focus_score": 50,
            "reasoning": "Unable to evaluate activity focus - using default score",
            "work_type": "unclear",
            "is_productive": False,
        }


# Global instance
_focus_evaluator: Optional[FocusEvaluator] = None


def get_focus_evaluator() -> FocusEvaluator:
    """Get global FocusEvaluator instance"""
    global _focus_evaluator
    if _focus_evaluator is None:
        _focus_evaluator = FocusEvaluator()
    return _focus_evaluator

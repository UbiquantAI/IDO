"""
Behavior Analyzer - Classify user behavior patterns from keyboard/mouse data

This module analyzes keyboard and mouse activity patterns to distinguish between:
- Operation (active work): coding, writing, designing
- Browsing (passive consumption): reading, watching, learning
- Mixed: combination of both

The classification is based on:
- Keyboard activity (60% weight): event frequency, typing intensity, modifier usage
- Mouse activity (40% weight): click/scroll/drag ratios, position variance
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.models import RawRecord, RecordType

logger = get_logger(__name__)


class BehaviorAnalyzer:
    """
    Analyzes keyboard and mouse patterns to classify user behavior

    Behavior Types:
    - operation: Active work (coding, writing, designing)
    - browsing: Passive consumption (reading, watching, browsing)
    - mixed: Combination of both
    """

    def __init__(
        self,
        operation_threshold: float = 0.6,
        browsing_threshold: float = 0.3,
        keyboard_weight: float = 0.6,
        mouse_weight: float = 0.4,
    ):
        """
        Initialize behavior analyzer

        Args:
            operation_threshold: Score threshold for operation classification (default: 0.6)
            browsing_threshold: Score threshold for browsing classification (default: 0.3)
            keyboard_weight: Weight for keyboard metrics 0-1 (default: 0.6)
            mouse_weight: Weight for mouse metrics 0-1 (default: 0.4)
        """
        self.operation_threshold = operation_threshold
        self.browsing_threshold = browsing_threshold
        self.keyboard_weight = keyboard_weight
        self.mouse_weight = mouse_weight

        logger.debug(
            f"BehaviorAnalyzer initialized "
            f"(op_threshold={operation_threshold}, "
            f"browse_threshold={browsing_threshold}, "
            f"kb_weight={keyboard_weight}, "
            f"mouse_weight={mouse_weight})"
        )

    def analyze(
        self,
        keyboard_records: Optional[List[RawRecord]] = None,
        mouse_records: Optional[List[RawRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze behavior from keyboard and mouse records

        Args:
            keyboard_records: Filtered keyboard events
            mouse_records: Filtered mouse events

        Returns:
            Behavior analysis result dictionary with structure:
            {
                "behavior_type": "operation" | "browsing" | "mixed",
                "confidence": 0.0-1.0,
                "metrics": {
                    "keyboard_activity": {...},
                    "mouse_activity": {...},
                    "combined_score": float,
                    "reasoning": str
                }
            }
        """
        # Calculate time window
        time_window = self._calculate_time_window(keyboard_records, mouse_records)

        # Analyze keyboard patterns
        kb_metrics = self._analyze_keyboard_activity(
            keyboard_records or [], time_window
        )

        # Analyze mouse patterns
        mouse_metrics = self._analyze_mouse_activity(mouse_records or [], time_window)

        # Classify behavior
        result = self._classify_behavior(kb_metrics, mouse_metrics)

        logger.debug(
            f"Behavior analysis: {result['behavior_type']} "
            f"(confidence={result['confidence']:.2f}, "
            f"kb_score={kb_metrics['score']:.2f}, "
            f"mouse_score={mouse_metrics['score']:.2f})"
        )

        return result

    def _calculate_time_window(
        self,
        keyboard_records: Optional[List[RawRecord]],
        mouse_records: Optional[List[RawRecord]],
    ) -> float:
        """
        Calculate analysis time window from record timestamps

        Args:
            keyboard_records: Keyboard event records
            mouse_records: Mouse event records

        Returns:
            Time window duration in seconds (minimum 1.0)
        """
        all_records = []
        if keyboard_records:
            all_records.extend(keyboard_records)
        if mouse_records:
            all_records.extend(mouse_records)

        if not all_records:
            return 20.0  # default 20 seconds

        timestamps = [r.timestamp for r in all_records]
        time_span = (max(timestamps) - min(timestamps)).total_seconds()

        return max(time_span, 1.0)  # at least 1 second

    def _analyze_keyboard_activity(
        self, keyboard_records: List[RawRecord], time_window: float
    ) -> Dict[str, Any]:
        """
        Analyze keyboard patterns to determine activity level

        Metrics:
        1. Events per minute (EPM) - raw activity level
        2. Typing intensity - char keys / total keys ratio
        3. Modifier usage - shortcuts (cmd+key, ctrl+key) ratio

        Args:
            keyboard_records: Keyboard event records
            time_window: Analysis window duration in seconds

        Returns:
            Keyboard activity metrics dict
        """
        if not keyboard_records:
            return {
                "events_per_minute": 0,
                "typing_intensity": 0,
                "modifier_usage": 0,
                "score": 0,
            }

        # Calculate events per minute
        epm = len(keyboard_records) / (time_window / 60) if time_window > 0 else 0

        # Classify key types
        char_keys = 0  # a-z, 0-9 (actual typing)
        special_keys = 0  # enter, backspace, arrows (navigation)
        modifier_combos = 0  # cmd+s, ctrl+c (shortcuts)

        for record in keyboard_records:
            key_type = record.data.get("key_type", "")
            modifiers = record.data.get("modifiers", [])

            if key_type == "char":
                char_keys += 1
            elif key_type == "special":
                special_keys += 1

            if modifiers and len(modifiers) > 0:
                modifier_combos += 1

        total_keys = char_keys + special_keys

        # Calculate ratios
        typing_intensity = char_keys / total_keys if total_keys > 0 else 0
        modifier_usage = modifier_combos / total_keys if total_keys > 0 else 0

        # Scoring (0-1 scale)
        # Operation: high EPM (>10), high typing (>0.6), moderate modifiers (>0.1)
        # Browsing: low EPM (<5), low typing (<0.3), few modifiers (<0.05)

        epm_score = min(epm / 20, 1.0)  # normalize to 20 EPM = 1.0
        typing_score = typing_intensity
        modifier_score = min(modifier_usage / 0.2, 1.0)  # 20% modifiers = 1.0

        # Weighted combination
        score = epm_score * 0.4 + typing_score * 0.4 + modifier_score * 0.2

        return {
            "events_per_minute": epm,
            "typing_intensity": typing_intensity,
            "modifier_usage": modifier_usage,
            "score": score,
        }

    def _analyze_mouse_activity(
        self, mouse_records: List[RawRecord], time_window: float
    ) -> Dict[str, Any]:
        """
        Analyze mouse patterns to determine work style

        Patterns:
        - Operation: precise clicks, drags, frequent position changes
        - Browsing: continuous scrolling, few clicks, linear movement

        Args:
            mouse_records: Mouse event records
            time_window: Analysis window duration in seconds

        Returns:
            Mouse activity metrics dict
        """
        if not mouse_records:
            return {
                "click_ratio": 0,
                "scroll_ratio": 0,
                "drag_ratio": 0,
                "precision_score": 0,
                "score": 0,
            }

        # Count event types
        clicks = 0
        scrolls = 0
        drags = 0
        positions = []

        for record in mouse_records:
            action = record.data.get("action", "")

            if action in ["click", "press", "release"]:
                clicks += 1
                position = record.data.get("position")
                if position:
                    positions.append(position)
            elif action == "scroll":
                scrolls += 1
            elif action in ["drag", "drag_end"]:
                drags += 1
                position = record.data.get("position")
                if position:
                    positions.append(position)

        total_events = clicks + scrolls + drags

        # Calculate ratios
        click_ratio = clicks / total_events if total_events > 0 else 0
        scroll_ratio = scrolls / total_events if total_events > 0 else 0
        drag_ratio = drags / total_events if total_events > 0 else 0

        # Calculate precision score (movement variance)
        # High variance = precise targeting (operation)
        # Low variance = linear scrolling (browsing)
        precision_score = self._calculate_position_variance(positions)

        # Scoring
        # Operation: high clicks (>0.4), low scroll (<0.5), high precision (>0.5)
        # Browsing: low clicks (<0.2), high scroll (>0.7), low precision (<0.3)

        click_score = click_ratio
        scroll_score = 1.0 - scroll_ratio  # inverse (low scroll = high score)
        drag_score = drag_ratio * 2.0  # drags strongly indicate operation
        precision_score_normalized = precision_score

        score = (
            click_score * 0.3
            + scroll_score * 0.2
            + min(drag_score, 1.0) * 0.2
            + precision_score_normalized * 0.3
        )

        return {
            "click_ratio": click_ratio,
            "scroll_ratio": scroll_ratio,
            "drag_ratio": drag_ratio,
            "precision_score": precision_score,
            "score": score,
        }

    def _calculate_position_variance(self, positions: List[tuple]) -> float:
        """
        Calculate normalized variance of mouse positions

        Higher variance indicates precise targeting (operation mode)
        Lower variance indicates linear movement (browsing mode)

        Args:
            positions: List of (x, y) position tuples

        Returns:
            Normalized variance score (0-1)
        """
        if len(positions) < 2:
            return 0.5  # neutral score for insufficient data

        # Calculate variance manually (avoiding numpy dependency)
        x_coords = [p[0] for p in positions]
        y_coords = [p[1] for p in positions]

        # Mean
        x_mean = sum(x_coords) / len(x_coords)
        y_mean = sum(y_coords) / len(y_coords)

        # Variance
        x_var = sum((x - x_mean) ** 2 for x in x_coords) / len(x_coords)
        y_var = sum((y - y_mean) ** 2 for y in y_coords) / len(y_coords)

        # Average variance
        avg_variance = (x_var + y_var) / 2

        # Normalize to 0-1 (assuming screen ~1920x1080)
        # High variance (100000+) = 1.0, low variance = 0.0
        normalized = min(avg_variance / 100000, 1.0)

        return normalized

    def _classify_behavior(
        self, kb_metrics: Dict[str, Any], mouse_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine keyboard and mouse metrics to determine behavior type

        Weighting:
        - Keyboard: 60% (stronger signal for operation vs browsing)
        - Mouse: 40% (supporting evidence)

        Args:
            kb_metrics: Keyboard activity metrics
            mouse_metrics: Mouse activity metrics

        Returns:
            Classification result with behavior_type, confidence, and metrics
        """
        kb_score = kb_metrics["score"]
        mouse_score = mouse_metrics["score"]

        # Weighted combination
        combined_score = kb_score * self.keyboard_weight + mouse_score * self.mouse_weight

        # Classification thresholds
        if combined_score >= self.operation_threshold:
            behavior_type = "operation"
            confidence = min(combined_score, 1.0)
        elif combined_score <= self.browsing_threshold:
            behavior_type = "browsing"
            confidence = min(1.0 - combined_score, 1.0)
        else:
            behavior_type = "mixed"
            # Lower confidence in middle range
            confidence = 1.0 - abs(combined_score - 0.5) * 2

        # Generate reasoning
        reasoning = self._generate_reasoning(
            behavior_type, kb_metrics, mouse_metrics, combined_score
        )

        return {
            "behavior_type": behavior_type,
            "confidence": confidence,
            "metrics": {
                "keyboard_activity": kb_metrics,
                "mouse_activity": mouse_metrics,
                "combined_score": combined_score,
                "reasoning": reasoning,
            },
        }

    def _generate_reasoning(
        self,
        behavior_type: str,
        kb_metrics: Dict[str, Any],
        mouse_metrics: Dict[str, Any],
        combined_score: float,
    ) -> str:
        """
        Generate human-readable explanation for classification

        Args:
            behavior_type: Classified behavior type
            kb_metrics: Keyboard activity metrics
            mouse_metrics: Mouse activity metrics
            combined_score: Combined classification score

        Returns:
            Reasoning string explaining the classification
        """
        kb_epm = kb_metrics["events_per_minute"]
        typing = kb_metrics["typing_intensity"]
        scroll_ratio = mouse_metrics["scroll_ratio"]
        click_ratio = mouse_metrics["click_ratio"]

        if behavior_type == "operation":
            return (
                f"High keyboard activity ({kb_epm:.1f} EPM) with "
                f"{typing*100:.0f}% typing and {click_ratio*100:.0f}% mouse clicks "
                f"indicates active work (coding, writing, or design)"
            )
        elif behavior_type == "browsing":
            return (
                f"Low keyboard activity ({kb_epm:.1f} EPM) with "
                f"{scroll_ratio*100:.0f}% scrolling indicates passive consumption "
                f"(reading, watching, or browsing)"
            )
        else:
            return (
                f"Mixed activity pattern (score: {combined_score:.2f}) suggests "
                f"combination of active work and information gathering"
            )

    def format_behavior_context(
        self, analysis_result: Dict[str, Any], language: str = "en"
    ) -> str:
        """
        Format behavior analysis for prompt inclusion

        Args:
            analysis_result: Result from analyze() method
            language: Language code ("en" or "zh")

        Returns:
            Formatted context string for LLM prompt
        """
        behavior_type = analysis_result["behavior_type"]
        confidence = analysis_result["confidence"]
        reasoning = analysis_result["metrics"]["reasoning"]

        kb_epm = analysis_result["metrics"]["keyboard_activity"]["events_per_minute"]
        kb_typing = analysis_result["metrics"]["keyboard_activity"]["typing_intensity"]
        mouse_clicks = analysis_result["metrics"]["mouse_activity"]["click_ratio"]
        mouse_scrolls = analysis_result["metrics"]["mouse_activity"]["scroll_ratio"]

        if language == "zh":
            # Chinese format
            context = f"""行为类型：{behavior_type.upper()} (置信度: {confidence:.0%})
- 键盘：{kb_epm:.1f} 次/分钟 ({kb_typing:.0%} 打字)
- 鼠标：{mouse_clicks:.0%} 点击, {mouse_scrolls:.0%} 滚动
- 分析：{reasoning}"""
        else:
            # English format
            context = f"""Behavior Type: {behavior_type.upper()} (Confidence: {confidence:.0%})
- Keyboard: {kb_epm:.1f} events/min ({kb_typing:.0%} typing)
- Mouse: {mouse_clicks:.0%} clicks, {mouse_scrolls:.0%} scrolling
- Analysis: {reasoning}"""

        return context.strip()

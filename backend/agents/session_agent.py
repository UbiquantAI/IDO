"""
SessionAgent - Intelligent long-running agent for session aggregation
Aggregates Events (medium-grained work segments) into Activities (coarse-grained work sessions)
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from core.db import get_db
from core.json_parser import parse_json_from_response
from core.logger import get_logger
from core.settings import get_settings
from llm.focus_evaluator import get_focus_evaluator
from llm.manager import get_llm_manager
from llm.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


class SessionAgent:
    """
    Intelligent session aggregation agent

    Aggregates Events into Activities based on:
    - Thematic relevance (core): Same work topic/project/problem domain
    - Time continuity (strong signal): Events within 30min tend to merge
    - Goal association (strong signal): Different objects serving same high-level goal
    - Project consistency (auxiliary): Same project/repo/branch
    - Workflow continuity (auxiliary): Events forming a workflow
    """

    def __init__(
        self,
        aggregation_interval: int = 1800,  # 30 minutes
        time_window_min: int = 30,  # minutes
        time_window_max: int = 120,  # minutes
        min_event_duration_seconds: int = 120,  # 2 minutes
        min_event_actions: int = 2,  # Minimum 2 actions per event
        merge_time_gap_tolerance: int = 300,  # 5 minutes tolerance for adjacent activities
        merge_similarity_threshold: float = 0.6,  # Minimum similarity score for merging
    ):
        """
        Initialize SessionAgent

        Args:
            aggregation_interval: How often to run aggregation (seconds, default 30min)
            time_window_min: Minimum time window for session (minutes, default 30min)
            time_window_max: Maximum time window for session (minutes, default 120min)
            min_event_duration_seconds: Minimum event duration for quality filtering (default 120s)
            min_event_actions: Minimum number of actions per event (default 2)
            merge_time_gap_tolerance: Max time gap (seconds) to consider for merging adjacent activities (default 300s/5min)
            merge_similarity_threshold: Minimum semantic similarity score (0-1) required for merging (default 0.6)
        """
        self.aggregation_interval = aggregation_interval
        self.time_window_min = time_window_min
        self.time_window_max = time_window_max
        self.min_event_duration_seconds = min_event_duration_seconds
        self.min_event_actions = min_event_actions
        self.merge_time_gap_tolerance = merge_time_gap_tolerance
        self.merge_similarity_threshold = merge_similarity_threshold

        # Initialize components
        self.db = get_db()
        self.llm_manager = get_llm_manager()
        self.settings = get_settings()

        # Running state
        self.is_running = False
        self.is_paused = False
        self.aggregation_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats: Dict[str, Any] = {
            "activities_created": 0,
            "events_aggregated": 0,
            "events_filtered_quality": 0,  # Events filtered due to quality criteria
            "last_aggregation_time": None,
        }

        logger.debug(
            f"SessionAgent initialized (interval: {aggregation_interval}s, "
            f"time_window: {time_window_min}-{time_window_max}min, "
            f"quality_filter: min_duration={min_event_duration_seconds}s, min_actions={min_event_actions}, "
            f"merge_config: gap_tolerance={merge_time_gap_tolerance}s, similarity_threshold={merge_similarity_threshold})"
        )

    def _get_language(self) -> str:
        """Get current language setting from config with caching"""
        return self.settings.get_language()

    async def start(self):
        """Start the session agent"""
        if self.is_running:
            logger.warning("SessionAgent is already running")
            return

        self.is_running = True

        # Start aggregation task
        self.aggregation_task = asyncio.create_task(
            self._periodic_session_aggregation()
        )

        logger.info(
            f"SessionAgent started (aggregation interval: {self.aggregation_interval}s)"
        )

    async def stop(self):
        """Stop the session agent"""
        if not self.is_running:
            return

        self.is_running = False
        self.is_paused = False

        # Cancel aggregation task
        if self.aggregation_task:
            self.aggregation_task.cancel()
            try:
                await self.aggregation_task
            except asyncio.CancelledError:
                pass

        logger.info("SessionAgent stopped")

    def pause(self):
        """Pause the session agent (system sleep)"""
        if not self.is_running:
            return

        self.is_paused = True
        logger.debug("SessionAgent paused")

    def resume(self):
        """Resume the session agent (system wake)"""
        if not self.is_running:
            return

        self.is_paused = False
        logger.debug("SessionAgent resumed")

    async def _periodic_session_aggregation(self):
        """Scheduled task: aggregate sessions every N minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.aggregation_interval)

                # Skip processing if paused (system sleep)
                if self.is_paused:
                    logger.debug("SessionAgent paused, skipping aggregation")
                    continue

                await self._aggregate_sessions()
            except asyncio.CancelledError:
                logger.debug("Session aggregation task cancelled")
                break
            except Exception as e:
                logger.error(f"Session aggregation task exception: {e}", exc_info=True)

    async def _aggregate_sessions(self):
        """
        Main aggregation logic:
        1. Get unaggregated Events
        2. Call LLM to cluster into sessions
        3. Apply learned merge patterns
        4. Check split candidates
        5. Merge with existing activities if applicable
        6. Create Activity records
        """
        try:
            # Get unaggregated events
            unaggregated_events = await self._get_unaggregated_events()

            if not unaggregated_events or len(unaggregated_events) == 0:
                logger.debug("No events to aggregate into sessions")
                return

            logger.debug(
                f"Starting to aggregate {len(unaggregated_events)} events into activities (sessions)"
            )

            # Call LLM to cluster events into sessions
            activities = await self._cluster_events_to_sessions(unaggregated_events)

            if not activities:
                logger.debug("No activities generated from event clustering")
                return

            # Merge with existing activities before saving
            activities_to_save, activities_to_update = await self._merge_with_existing_activities(activities)

            # Update existing activities
            for update_data in activities_to_update:
                await self.db.activities.save(
                    activity_id=update_data["id"],
                    title=update_data["title"],
                    description=update_data["description"],
                    start_time=update_data["start_time"].isoformat() if isinstance(update_data["start_time"], datetime) else update_data["start_time"],
                    end_time=update_data["end_time"].isoformat() if isinstance(update_data["end_time"], datetime) else update_data["end_time"],
                    source_event_ids=update_data["source_event_ids"],
                    session_duration_minutes=update_data.get("session_duration_minutes"),
                    topic_tags=update_data.get("topic_tags", []),
                )

                # Mark new events as aggregated to this existing activity
                new_event_ids = update_data.get("_new_event_ids", [])
                if new_event_ids:
                    await self.db.events.mark_as_aggregated(
                        event_ids=new_event_ids,
                        activity_id=update_data["id"],
                    )
                    self.stats["events_aggregated"] += len(new_event_ids)

                logger.debug(
                    f"Updated existing activity {update_data['id']} with {len(new_event_ids)} new events "
                    f"(merge reason: {update_data.get('_merge_reason', 'unknown')})"
                )

            # Save new activities
            for activity_data in activities_to_save:
                activity_id = activity_data["id"]
                source_event_ids = activity_data.get("source_event_ids", [])

                if not source_event_ids:
                    logger.warning(f"Activity {activity_id} has no source events, skipping")
                    continue

                # Calculate session duration
                start_time = activity_data.get("start_time")
                end_time = activity_data.get("end_time")
                session_duration_minutes = None

                if start_time and end_time:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time)

                    duration = end_time - start_time
                    session_duration_minutes = int(duration.total_seconds() / 60)

                # Save activity
                await self.db.activities.save(
                    activity_id=activity_id,
                    title=activity_data.get("title", ""),
                    description=activity_data.get("description", ""),
                    start_time=activity_data["start_time"].isoformat() if isinstance(activity_data["start_time"], datetime) else activity_data["start_time"],
                    end_time=activity_data["end_time"].isoformat() if isinstance(activity_data["end_time"], datetime) else activity_data["end_time"],
                    source_event_ids=source_event_ids,
                    session_duration_minutes=session_duration_minutes,
                    topic_tags=activity_data.get("topic_tags", []),
                )

                # Mark events as aggregated
                await self.db.events.mark_as_aggregated(
                    event_ids=source_event_ids,
                    activity_id=activity_id,
                )

                self.stats["activities_created"] += 1
                self.stats["events_aggregated"] += len(source_event_ids)

            self.stats["last_aggregation_time"] = datetime.now()

            logger.debug(
                f"Session aggregation completed: created {len(activities_to_save)} new activities, "
                f"updated {len(activities_to_update)} existing activities, "
                f"from {self.stats['events_aggregated']} events"
            )

        except Exception as e:
            logger.error(f"Failed to aggregate sessions: {e}", exc_info=True)

    async def _get_unaggregated_events(
        self, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch events not yet aggregated into activities

        Args:
            since: Starting time to fetch events from

        Returns:
            List of event dictionaries
        """
        try:
            # Default: fetch events from last 2 hours
            start_time = since or datetime.now() - timedelta(hours=2)
            end_time = datetime.now()

            # Get events in timeframe
            events = await self.db.events.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            # Filter out already aggregated events and apply quality filters
            result: List[Dict[str, Any]] = []
            filtered_count = 0
            quality_filtered_count = 0

            for event in events:
                # Skip already aggregated events (using aggregated_into_activity_id field)
                if event.get("aggregated_into_activity_id"):
                    filtered_count += 1
                    continue

                # Skip Pomodoro events (handled by work phase aggregation)
                # These events are processed when each Pomodoro work phase ends
                if event.get("pomodoro_session_id"):
                    filtered_count += 1
                    logger.debug(
                        f"Skipping Pomodoro event {event.get('id')} "
                        f"(session: {event.get('pomodoro_session_id')}) - "
                        f"handled by work phase aggregation"
                    )
                    continue

                # Quality filter 1: Check minimum number of actions
                source_action_ids = event.get("source_action_ids", [])
                if len(source_action_ids) < self.min_event_actions:
                    quality_filtered_count += 1
                    logger.debug(
                        f"Filtering out event {event.get('id')} - insufficient actions "
                        f"({len(source_action_ids)} < {self.min_event_actions})"
                    )
                    continue

                # Quality filter 2: Check minimum duration
                start_time_str = event.get("start_time")
                end_time_str = event.get("end_time")

                if start_time_str and end_time_str:
                    try:
                        event_start = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                        event_end = datetime.fromisoformat(end_time_str) if isinstance(end_time_str, str) else end_time_str
                        duration_seconds = (event_end - event_start).total_seconds()

                        if duration_seconds < self.min_event_duration_seconds:
                            quality_filtered_count += 1
                            logger.debug(
                                f"Filtering out event {event.get('id')} - too short "
                                f"({duration_seconds:.1f}s < {self.min_event_duration_seconds}s)"
                            )
                            continue
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse event timestamps: {parse_error}")
                        # If we can't parse timestamps, allow the event through
                        pass

                result.append(event)

            # Update statistics
            self.stats["events_filtered_quality"] += quality_filtered_count

            logger.debug(
                f"Event filtering: {len(events)} total, {filtered_count} already aggregated, "
                f"{quality_filtered_count} quality-filtered, {len(result)} remaining"
            )

            return result

        except Exception as exc:
            logger.error("Failed to get unaggregated events: %s", exc, exc_info=True)
            return []

    async def _cluster_events_to_sessions(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to cluster events into session-level activities

        Args:
            events: List of event dictionaries

        Returns:
            List of activity dictionaries
        """
        if not events:
            return []

        try:
            logger.debug(f"Clustering {len(events)} events into sessions")

            # Build events JSON with index
            events_with_index = [
                {
                    "index": i + 1,
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "start_time": event.get("start_time", ""),
                    "end_time": event.get("end_time", ""),
                }
                for i, event in enumerate(events)
            ]
            events_json = json.dumps(events_with_index, ensure_ascii=False, indent=2)

            # Get current language and prompt manager
            language = self._get_language()
            prompt_manager = get_prompt_manager(language)

            # Build messages
            messages = prompt_manager.build_messages(
                "session_aggregation", "user_prompt_template", events_json=events_json
            )

            # Get configuration parameters
            config_params = prompt_manager.get_config_params("session_aggregation")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(f"Session clustering result format error: {content[:200]}")
                return []

            activities_data = result.get("activities", [])

            # Convert to complete activity objects
            activities = []
            for activity_data in activities_data:
                # Normalize source indexes
                normalized_indexes = self._normalize_source_indexes(
                    activity_data.get("source"), len(events)
                )

                if not normalized_indexes:
                    continue

                source_event_ids: List[str] = []
                source_events: List[Dict[str, Any]] = []
                for idx in normalized_indexes:
                    event = events[idx - 1]
                    event_id = event.get("id")
                    if event_id:
                        source_event_ids.append(event_id)
                    source_events.append(event)

                if not source_events:
                    continue

                # Get timestamps
                start_time = None
                end_time = None
                for e in source_events:
                    st = e.get("start_time")
                    et = e.get("end_time")

                    if st:
                        if isinstance(st, str):
                            st = datetime.fromisoformat(st)
                        if start_time is None or st < start_time:
                            start_time = st

                    if et:
                        if isinstance(et, str):
                            et = datetime.fromisoformat(et)
                        if end_time is None or et > end_time:
                            end_time = et

                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time

                # Extract topic tags from LLM response if provided
                topic_tags = activity_data.get("topic_tags", [])
                if not topic_tags:
                    # Fallback: extract from title
                    topic_tags = []

                activity = {
                    "id": str(uuid.uuid4()),
                    "title": activity_data.get("title", "Unnamed session"),
                    "description": activity_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_event_ids": source_event_ids,
                    "topic_tags": topic_tags,
                    "created_at": datetime.now(),
                }

                activities.append(activity)

            logger.debug(
                f"Clustering completed: generated {len(activities)} activities (before overlap detection)"
            )

            # Post-process: detect and merge overlapping activities
            activities = self._merge_overlapping_activities(activities)

            logger.debug(
                f"After overlap merging: {len(activities)} activities"
            )

            # Validate with supervisor, passing original events for semantic validation
            activities = await self._validate_activities_with_supervisor(
                activities, events
            )

            return activities

        except Exception as e:
            logger.error(f"Failed to cluster events to sessions: {e}", exc_info=True)
            return []

    async def _validate_activities_with_supervisor(
        self,
        activities: List[Dict[str, Any]],
        source_events: Optional[List[Dict[str, Any]]] = None,
        source_actions: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Validate activities with ActivitySupervisor using multi-round revision

        Args:
            activities: List of activities to validate
            source_events: Optional list of all source events for semantic validation (deprecated)
            source_actions: Optional list of all source actions for semantic and temporal validation (preferred)
            max_iterations: Maximum number of validation iterations (default: 3)

        Returns:
            Validated (and possibly revised) list of activities
        """
        if not activities:
            return activities

        try:
            from agents.supervisor import ActivitySupervisor

            language = self._get_language()
            supervisor = ActivitySupervisor(language=language)

            current_activities = activities
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"ActivitySupervisor validation iteration {iteration}/{max_iterations}")

                # Prepare activities for validation (only title and description)
                activities_for_validation = [
                    {
                        "title": activity.get("title", ""),
                        "description": activity.get("description", ""),
                    }
                    for activity in current_activities
                ]

                # Build action/event mapping for semantic and temporal validation
                # Prefer actions over events (action-based aggregation)
                actions_for_validation = None
                events_for_validation = None

                if source_actions:
                    # Create a mapping of action IDs to actions for lookup
                    action_map = {action.get("id"): action for action in source_actions if action.get("id")}

                    # For each activity, collect its source actions
                    actions_for_validation = []
                    for activity in current_activities:
                        source_action_ids = activity.get("source_action_ids", [])
                        activity_actions = []
                        for action_id in source_action_ids:
                            if action_id in action_map:
                                activity_actions.append(action_map[action_id])

                        # Add all actions (we'll pass them all and let supervisor map them)
                        actions_for_validation.extend(activity_actions)

                    # Remove duplicates while preserving order
                    seen_ids = set()
                    unique_actions = []
                    for action in actions_for_validation:
                        action_id = action.get("id")
                        if action_id and action_id not in seen_ids:
                            seen_ids.add(action_id)
                            unique_actions.append(action)
                    actions_for_validation = unique_actions

                elif source_events:
                    # Fallback to events for backward compatibility
                    # Create a mapping of event IDs to events for lookup
                    event_map = {event.get("id"): event for event in source_events if event.get("id")}

                    # For each activity, collect its source events
                    events_for_validation = []
                    for activity in current_activities:
                        source_event_ids = activity.get("source_event_ids", [])
                        activity_events = []
                        for event_id in source_event_ids:
                            if event_id in event_map:
                                activity_events.append(event_map[event_id])

                        # Add all events (we'll pass them all and let supervisor map them)
                        events_for_validation.extend(activity_events)

                    # Remove duplicates while preserving order
                    seen_ids = set()
                    unique_events = []
                    for event in events_for_validation:
                        event_id = event.get("id")
                        if event_id and event_id not in seen_ids:
                            seen_ids.add(event_id)
                            unique_events.append(event)
                    events_for_validation = unique_events

                # Validate with source actions (preferred) or events (fallback)
                result = await supervisor.validate(
                    activities_for_validation,
                    source_events=events_for_validation,
                    source_actions=actions_for_validation
                )

                # Check if we have revised content
                if not result.revised_content or len(result.revised_content) == 0:
                    # No revisions provided, accept current activities
                    if result.issues or result.suggestions:
                        logger.info(
                            f"ActivitySupervisor iteration {iteration} - No revisions provided. "
                            f"Issues: {result.issues}, Suggestions: {result.suggestions}"
                        )
                    else:
                        logger.info(f"ActivitySupervisor iteration {iteration} - All activities validated successfully")
                    break

                # We have revisions - check if count matches
                revised_activities = result.revised_content
                assert revised_activities is not None  # Type assertion for type checker

                if len(revised_activities) != len(current_activities):
                    # Activity count changed (split/merge)
                    logger.warning(
                        f"ActivitySupervisor iteration {iteration} changed activity count from "
                        f"{len(current_activities)} to {len(revised_activities)}. "
                        f"Keeping original activities (split/merge not yet implemented)."
                    )
                    break

                # Apply revisions - update title and description
                changes_made = False
                for i, activity in enumerate(current_activities):
                    if i < len(revised_activities):
                        old_title = activity["title"]
                        old_desc = activity["description"]
                        new_title = revised_activities[i].get("title", old_title)
                        new_desc = revised_activities[i].get("description", old_desc)

                        if old_title != new_title or old_desc != new_desc:
                            activity["title"] = new_title
                            activity["description"] = new_desc
                            changes_made = True
                            logger.debug(
                                f"ActivitySupervisor iteration {iteration} - Activity {i} revised: "
                                f"title: '{old_title}' → '{new_title}'"
                            )

                if not changes_made:
                    # No actual changes made, stop iterations
                    logger.info(
                        f"ActivitySupervisor iteration {iteration} - No changes made, stopping iterations"
                    )
                    break

                logger.info(
                    f"ActivitySupervisor iteration {iteration} - Applied revisions. "
                    f"Issues: {result.issues}, Suggestions: {result.suggestions}"
                )

                # If supervisor says it's valid now, we can stop
                if result.is_valid:
                    logger.info(
                        f"ActivitySupervisor iteration {iteration} - Activities now valid, stopping iterations"
                    )
                    break

            if iteration >= max_iterations:
                logger.warning(
                    f"ActivitySupervisor reached max iterations ({max_iterations}), using current state"
                )

            return current_activities

        except Exception as e:
            logger.error(f"ActivitySupervisor validation failed: {e}", exc_info=True)
            # Return original activities if validation fails
            return activities

    def _calculate_activity_similarity(
        self, activity1: Dict[str, Any], activity2: Dict[str, Any]
    ) -> float:
        """
        Calculate semantic similarity between two activities

        Uses multiple signals:
        - Title similarity (Jaccard similarity on words)
        - Topic tag overlap (Jaccard similarity on tags)

        Args:
            activity1: First activity dictionary
            activity2: Second activity dictionary

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Extract titles
        title1 = (activity1.get("title") or "").lower().strip()
        title2 = (activity2.get("title") or "").lower().strip()

        # If either title is empty, low similarity
        if not title1 or not title2:
            return 0.0

        # Exact match on title = very high similarity
        if title1 == title2:
            return 1.0

        # Calculate word-level Jaccard similarity for titles
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            title_similarity = 0.0
        else:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            title_similarity = intersection / union if union > 0 else 0.0

        # Calculate topic tag Jaccard similarity
        tags1 = set(activity1.get("topic_tags", []))
        tags2 = set(activity2.get("topic_tags", []))

        if not tags1 or not tags2:
            tag_similarity = 0.0
        else:
            intersection = len(tags1 & tags2)
            union = len(tags1 | tags2)
            tag_similarity = intersection / union if union > 0 else 0.0

        # Weighted combination: title is more important than tags
        # Title weight: 0.7, Tag weight: 0.3
        combined_similarity = (title_similarity * 0.7) + (tag_similarity * 0.3)

        return combined_similarity

    def _merge_overlapping_activities(
        self, activities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect and merge overlapping activities to prevent duplicate time consumption

        Args:
            activities: List of activity dictionaries

        Returns:
            List of activities with overlaps merged
        """
        if len(activities) <= 1:
            return activities

        # Sort by start_time
        sorted_activities = sorted(
            activities,
            key=lambda a: a.get("start_time") or datetime.min
        )

        merged: List[Dict[str, Any]] = []
        current = sorted_activities[0].copy()

        for i in range(1, len(sorted_activities)):
            next_activity = sorted_activities[i]

            # Check for time overlap or proximity
            current_end = current.get("end_time")
            next_start = next_activity.get("start_time")

            should_merge = False
            merge_reason = ""

            if current_end and next_start:
                # Convert to datetime if needed
                if isinstance(current_end, str):
                    current_end = datetime.fromisoformat(current_end)
                if isinstance(next_start, str):
                    next_start = datetime.fromisoformat(next_start)

                # Calculate time gap between activities
                time_gap = (next_start - current_end).total_seconds()

                # Case 1: Direct time overlap (original logic)
                if next_start < current_end:
                    should_merge = True
                    merge_reason = "time_overlap"

                # Case 2: Adjacent or small gap with semantic similarity
                elif 0 <= time_gap <= self.merge_time_gap_tolerance:
                    # Calculate semantic similarity
                    similarity = self._calculate_activity_similarity(current, next_activity)

                    if similarity >= self.merge_similarity_threshold:
                        should_merge = True
                        merge_reason = f"proximity_similarity (gap: {time_gap:.0f}s, similarity: {similarity:.2f})"

                # Perform merge if criteria met
                if should_merge:
                    logger.debug(
                        f"Merging activities (reason: {merge_reason}): '{current.get('title')}' and '{next_activity.get('title')}'"
                    )

                    # Merge source_event_ids (remove duplicates)
                    current_events = set(current.get("source_event_ids", []))
                    next_events = set(next_activity.get("source_event_ids", []))
                    merged_events = list(current_events | next_events)

                    # Update end_time to the latest
                    next_end = next_activity.get("end_time")
                    if isinstance(next_end, str):
                        next_end = datetime.fromisoformat(next_end)
                    if next_end and next_end > current_end:
                        current["end_time"] = next_end

                    # Merge topic_tags
                    current_tags = set(current.get("topic_tags", []))
                    next_tags = set(next_activity.get("topic_tags", []))
                    merged_tags = list(current_tags | next_tags)

                    # Update current with merged data
                    current["source_event_ids"] = merged_events
                    current["topic_tags"] = merged_tags

                    # Merge titles and descriptions based on duration
                    # Calculate durations to determine primary activity
                    current_start = current.get("start_time")
                    if isinstance(current_start, str):
                        current_start = datetime.fromisoformat(current_start)
                    next_start_dt = next_activity.get("start_time")
                    if isinstance(next_start_dt, str):
                        next_start_dt = datetime.fromisoformat(next_start_dt)

                    current_duration = (current_end - current_start).total_seconds() if current_start and current_end else 0
                    next_duration = (next_end - next_start_dt).total_seconds() if next_start_dt and next_end else 0

                    current_title = current.get("title", "")
                    next_title = next_activity.get("title", "")
                    current_desc = current.get("description", "")
                    next_desc = next_activity.get("description", "")

                    # Select title from the longer-duration activity (primary activity)
                    if next_title and next_title != current_title:
                        if next_duration > current_duration:
                            # Next activity is primary, use its title
                            logger.debug(
                                f"Selected '{next_title}' as primary (duration: {next_duration:.0f}s > {current_duration:.0f}s)"
                            )
                            current["title"] = next_title
                            # Add current as secondary context in description if needed
                            if current_desc and current_title:
                                current["description"] = f"{next_desc}\n\n[Related: {current_title}]\n{current_desc}" if next_desc else current_desc
                            elif next_desc:
                                current["description"] = next_desc
                        else:
                            # Current activity is primary, keep its title
                            logger.debug(
                                f"Kept '{current_title}' as primary (duration: {current_duration:.0f}s >= {next_duration:.0f}s)"
                            )
                            # Keep current title, add next as secondary context
                            if next_desc and next_title:
                                if current_desc:
                                    current["description"] = f"{current_desc}\n\n[Related: {next_title}]\n{next_desc}"
                                else:
                                    current["description"] = next_desc
                            # If only next has description, use it
                            elif next_desc and not current_desc:
                                current["description"] = next_desc
                    else:
                        # Same title or one is empty, just merge descriptions
                        if next_desc and next_desc != current_desc:
                            if current_desc:
                                current["description"] = f"{current_desc}\n\n{next_desc}"
                            else:
                                current["description"] = next_desc

                    logger.debug(
                        f"Merged into: '{current.get('title')}' with {len(merged_events)} events"
                    )
                    continue

            # No overlap, save current and move to next
            merged.append(current)
            current = next_activity.copy()

        # Don't forget the last activity
        merged.append(current)

        return merged

    async def _get_recent_activities_for_merge(
        self, lookback_hours: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities from database for merge checking

        Args:
            lookback_hours: How many hours to look back (default: 2 hours)

        Returns:
            List of recent activity dictionaries
        """
        try:
            # Query activities from the last N hours
            start_time = datetime.now() - timedelta(hours=lookback_hours)
            end_time = datetime.now()

            activities = await self.db.activities.get_by_date(
                start_time.strftime("%Y-%m-%d"),
                end_time.strftime("%Y-%m-%d"),
            )

            # Filter to only include activities within the time window
            # (get_by_date uses date, we need more precise filtering)
            filtered_activities = []
            for activity in activities:
                activity_start = activity.get("start_time")
                if isinstance(activity_start, str):
                    activity_start = datetime.fromisoformat(activity_start)

                if activity_start and activity_start >= start_time:
                    filtered_activities.append(activity)

            logger.debug(
                f"Found {len(filtered_activities)} recent activities in the last {lookback_hours} hours"
            )

            return filtered_activities

        except Exception as e:
            logger.error(f"Failed to get recent activities for merge: {e}", exc_info=True)
            return []

    async def _merge_with_existing_activities(
        self, new_activities: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Check if new activities should be merged with existing activities

        Args:
            new_activities: List of newly created activity dictionaries

        Returns:
            Tuple of (activities_to_save, activities_to_update)
            - activities_to_save: New activities that don't merge with existing ones
            - activities_to_update: Existing activities that should be updated with new events
        """
        if not new_activities:
            return [], []

        try:
            # Get recent activities from database
            existing_activities = await self._get_recent_activities_for_merge(lookback_hours=2)

            if not existing_activities:
                # No existing activities to merge with
                return new_activities, []

            # Sort existing activities by end_time for efficient checking
            def get_sort_key(activity: Dict[str, Any]) -> datetime:
                end_time = activity.get("end_time")
                if isinstance(end_time, str):
                    try:
                        return datetime.fromisoformat(end_time)
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(end_time, datetime):
                    return end_time
                return datetime.min

            existing_activities_sorted = sorted(existing_activities, key=get_sort_key)

            activities_to_save = []
            activities_to_update = []
            merged_new_activity_ids = set()

            # For each new activity, check if it should merge with any existing activity
            for new_activity in new_activities:
                merged = False

                new_start = new_activity.get("start_time")
                if isinstance(new_start, str):
                    new_start = datetime.fromisoformat(new_start)

                # Check against each existing activity
                for existing_activity in existing_activities_sorted:
                    existing_end = existing_activity.get("end_time")
                    if isinstance(existing_end, str):
                        existing_end = datetime.fromisoformat(existing_end)

                    existing_start = existing_activity.get("start_time")
                    if isinstance(existing_start, str):
                        existing_start = datetime.fromisoformat(existing_start)

                    if not existing_end or not new_start or not existing_start:
                        continue

                    # Calculate time gap
                    time_gap = (new_start - existing_end).total_seconds()

                    # Check merge conditions
                    should_merge = False
                    merge_reason = ""

                    # Case 1: Time overlap
                    new_end = new_activity.get("end_time")
                    if isinstance(new_end, str):
                        new_end = datetime.fromisoformat(new_end)

                    if new_end and new_start < existing_end:
                        should_merge = True
                        merge_reason = "time_overlap"

                    # Case 2: Adjacent or small gap with semantic similarity
                    elif 0 <= time_gap <= self.merge_time_gap_tolerance:
                        similarity = self._calculate_activity_similarity(
                            existing_activity, new_activity
                        )

                        if similarity >= self.merge_similarity_threshold:
                            should_merge = True
                            merge_reason = f"proximity_similarity (gap: {time_gap:.0f}s, similarity: {similarity:.2f})"

                    if should_merge:
                        # Merge new activity into existing activity
                        logger.debug(
                            f"Merging new activity '{new_activity.get('title')}' into existing "
                            f"activity '{existing_activity.get('title')}' (reason: {merge_reason})"
                        )

                        # Merge source_event_ids
                        existing_events = set(existing_activity.get("source_event_ids", []))
                        new_events = set(new_activity.get("source_event_ids", []))
                        all_events = list(existing_events | new_events)
                        new_event_ids_only = list(new_events - existing_events)

                        # Update time range
                        merged_start = min(existing_start, new_start)
                        merged_end = max(existing_end, new_end) if new_end else existing_end

                        # Calculate new duration
                        duration_minutes = int((merged_end - merged_start).total_seconds() / 60)

                        # Merge topic tags
                        existing_tags = set(existing_activity.get("topic_tags", []))
                        new_tags = set(new_activity.get("topic_tags", []))
                        merged_tags = list(existing_tags | new_tags)

                        # Determine primary title/description based on duration
                        existing_duration = (existing_end - existing_start).total_seconds()
                        new_duration = (new_end - new_start).total_seconds() if new_end else 0

                        if new_duration > existing_duration:
                            # New activity is primary
                            title = new_activity.get("title", existing_activity.get("title", ""))
                            description = new_activity.get("description", "")
                            if description and existing_activity.get("description"):
                                description = f"{description}\n\n[Related: {existing_activity.get('title')}]\n{existing_activity.get('description')}"
                            elif existing_activity.get("description"):
                                description = existing_activity.get("description")
                        else:
                            # Existing activity is primary
                            title = existing_activity.get("title", "")
                            description = existing_activity.get("description", "")
                            if new_activity.get("description") and new_activity.get("title"):
                                if description:
                                    description = f"{description}\n\n[Related: {new_activity.get('title')}]\n{new_activity.get('description')}"
                                else:
                                    description = new_activity.get("description", "")

                        # Create update record
                        update_record = {
                            "id": existing_activity["id"],
                            "title": title,
                            "description": description,
                            "start_time": merged_start,
                            "end_time": merged_end,
                            "source_event_ids": all_events,
                            "session_duration_minutes": duration_minutes,
                            "topic_tags": merged_tags,
                            "_new_event_ids": new_event_ids_only,
                            "_merge_reason": merge_reason,
                        }

                        # Check if this existing activity was already updated in this batch
                        existing_update = None
                        for idx, update in enumerate(activities_to_update):
                            if update["id"] == existing_activity["id"]:
                                existing_update = idx
                                break

                        if existing_update is not None:
                            # Merge with previous update
                            prev_update = activities_to_update[existing_update]
                            prev_events = set(prev_update["source_event_ids"])
                            combined_events = list(prev_events | set(all_events))
                            prev_new_events = set(prev_update.get("_new_event_ids", []))
                            combined_new_events = list(prev_new_events | set(new_event_ids_only))

                            prev_update["source_event_ids"] = combined_events
                            prev_update["_new_event_ids"] = combined_new_events
                            prev_update["end_time"] = max(prev_update["end_time"], merged_end)
                            prev_update["session_duration_minutes"] = int(
                                (prev_update["end_time"] - prev_update["start_time"]).total_seconds() / 60
                            )
                        else:
                            activities_to_update.append(update_record)

                        merged_new_activity_ids.add(new_activity["id"])
                        merged = True
                        break

                if not merged:
                    # No merge happened, this is a new activity to save
                    activities_to_save.append(new_activity)

            logger.debug(
                f"Merge check completed: {len(activities_to_save)} new activities to save, "
                f"{len(activities_to_update)} existing activities to update, "
                f"{len(merged_new_activity_ids)} new activities merged"
            )

            return activities_to_save, activities_to_update

        except Exception as e:
            logger.error(f"Failed to merge with existing activities: {e}", exc_info=True)
            # On error, return all as new activities
            return new_activities, []

    def _normalize_source_indexes(
        self, raw_indexes: Any, total_events: int
    ) -> List[int]:
        """Normalize LLM provided indexes to a unique, ordered int list."""
        if not isinstance(raw_indexes, list) or total_events <= 0:
            return []

        normalized: List[int] = []
        seen: Set[int] = set()

        for idx in raw_indexes:
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue

            if idx_int < 1 or idx_int > total_events:
                continue

            if idx_int in seen:
                continue

            seen.add(idx_int)
            normalized.append(idx_int)

        return normalized

    async def record_user_merge(
        self,
        merged_activity_id: str,
        original_activity_ids: List[str],
        original_activities: List[Dict[str, Any]],
    ) -> None:
        """
        Record user manual merge operation and learn from it

        Args:
            merged_activity_id: ID of the newly created merged activity
            original_activity_ids: IDs of the original activities that were merged
            original_activities: Full data of original activities
        """
        try:
            logger.debug(
                f"Recording user merge: {len(original_activity_ids)} activities -> {merged_activity_id}"
            )

            # Analyze merge pattern using LLM
            pattern = await self._analyze_merge_pattern(
                merged_activity_id, original_activities
            )

            if pattern:
                # Save learned pattern to database
                pattern_id = str(uuid.uuid4())
                await self.db.session_preferences.save_pattern(
                    pattern_id=pattern_id,
                    preference_type="merge_pattern",
                    pattern_description=pattern,
                    confidence_score=0.6,  # Initial confidence
                    times_observed=1,
                    last_observed=datetime.now().isoformat(),
                )

                logger.info(f"Learned new merge pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to record user merge: {e}", exc_info=True)

    async def record_user_split(
        self,
        original_activity_id: str,
        new_activity_ids: List[str],
        original_activity: Dict[str, Any],
        source_events: List[Dict[str, Any]],
    ) -> None:
        """
        Record user manual split operation and learn from it

        Args:
            original_activity_id: ID of the original activity that was split
            new_activity_ids: IDs of the new activities created from split
            original_activity: Full data of original activity
            source_events: Source events of the original activity
        """
        try:
            logger.debug(
                f"Recording user split: {original_activity_id} -> {len(new_activity_ids)} activities"
            )

            # Analyze split pattern using LLM
            pattern = await self._analyze_split_pattern(
                original_activity, new_activity_ids, source_events
            )

            if pattern:
                # Save learned pattern to database
                pattern_id = str(uuid.uuid4())
                await self.db.session_preferences.save_pattern(
                    pattern_id=pattern_id,
                    preference_type="split_pattern",
                    pattern_description=pattern,
                    confidence_score=0.6,  # Initial confidence
                    times_observed=1,
                    last_observed=datetime.now().isoformat(),
                )

                logger.info(f"Learned new split pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to record user split: {e}", exc_info=True)

    async def _analyze_merge_pattern(
        self, merged_activity_id: str, original_activities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Analyze why user merged these activities to extract pattern

        Args:
            merged_activity_id: ID of merged activity
            original_activities: Original activities that were merged

        Returns:
            Pattern description or None
        """
        try:
            # Build analysis prompt
            activities_summary = []
            for activity in original_activities:
                activities_summary.append(
                    {
                        "title": activity.get("title", ""),
                        "description": activity.get("description", ""),
                        "start_time": activity.get("start_time", ""),
                        "end_time": activity.get("end_time", ""),
                    }
                )

            import json

            activities_json = json.dumps(activities_summary, ensure_ascii=False, indent=2)

            # Simple prompt for pattern extraction
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing user behavior patterns. Analyze why the user merged these activities and extract a reusable pattern description (max 100 words).",
                },
                {
                    "role": "user",
                    "content": f"User merged these activities:\n{activities_json}\n\nWhat pattern or rule can we learn from this merge? Describe in one concise sentence.",
                },
            ]

            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages, max_tokens=200, temperature=0.3
            )

            pattern = response.get("content", "").strip()
            return pattern if pattern else None

        except Exception as e:
            logger.error(f"Failed to analyze merge pattern: {e}", exc_info=True)
            return None

    async def _analyze_split_pattern(
        self,
        original_activity: Dict[str, Any],
        new_activity_ids: List[str],
        source_events: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Analyze why user split this activity to extract pattern

        Args:
            original_activity: Original activity that was split
            new_activity_ids: IDs of new activities
            source_events: Source events of the activity

        Returns:
            Pattern description or None
        """
        try:
            # Build analysis prompt
            activity_summary = {
                "title": original_activity.get("title", ""),
                "description": original_activity.get("description", ""),
                "duration_minutes": original_activity.get("session_duration_minutes", 0),
                "num_events": len(source_events),
            }

            import json

            activity_json = json.dumps(activity_summary, ensure_ascii=False, indent=2)

            # Simple prompt for pattern extraction
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing user behavior patterns. Analyze why the user split this activity and extract a reusable pattern description (max 100 words).",
                },
                {
                    "role": "user",
                    "content": f"User split this activity into {len(new_activity_ids)} separate activities:\n{activity_json}\n\nWhat pattern or rule can we learn from this split? Describe in one concise sentence.",
                },
            ]

            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages, max_tokens=200, temperature=0.3
            )

            pattern = response.get("content", "").strip()
            return pattern if pattern else None

        except Exception as e:
            logger.error(f"Failed to analyze split pattern: {e}", exc_info=True)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics information"""
        return {
            "is_running": self.is_running,
            "aggregation_interval": self.aggregation_interval,
            "time_window_min": self.time_window_min,
            "time_window_max": self.time_window_max,
            "language": self._get_language(),
            "stats": self.stats.copy(),
        }

    # ========== Pomodoro Work Phase Aggregation Methods ==========

    async def aggregate_work_phase(
        self,
        session_id: str,
        work_phase: int,
        phase_start_time: datetime,
        phase_end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate actions from a single Pomodoro work phase into activities

        NEW: Direct Actions → Activities aggregation (NO Events layer)

        This method is triggered when a Pomodoro work phase ends (work → break transition).
        It creates activities specifically for that work phase, with intelligent merging
        with activities from previous work phases in the same session.

        Args:
            session_id: Pomodoro session ID
            work_phase: Work phase number (1-based, e.g., 1, 2, 3, 4)
            phase_start_time: When this work phase started
            phase_end_time: When this work phase ended

        Returns:
            List of created/updated activity dictionaries
        """
        try:
            logger.info(
                f"Starting work phase aggregation (ACTION-BASED): session={session_id}, "
                f"phase={work_phase}, duration={(phase_end_time - phase_start_time).total_seconds() / 60:.1f}min"
            )

            # Step 1: Get actions directly for this work phase (NO WAITING for events)
            actions = await self._get_work_phase_actions(
                session_id, phase_start_time, phase_end_time
            )

            if not actions:
                logger.warning(
                    f"No actions found for work phase {work_phase}. "
                    f"User may have been idle during this phase."
                )
                return []

            logger.debug(
                f"Found {len(actions)} actions for work phase {work_phase} "
                f"(session: {session_id})"
            )

            # Step 2: Cluster actions into activities using NEW LLM prompt
            activities = await self._cluster_actions_to_activities(actions)

            if not activities:
                logger.debug(
                    f"No activities generated from action clustering for work phase {work_phase}"
                )
                return []

            # Step 2.3: Filter out short-duration activities (< 2 minutes)
            activities = self._filter_activities_by_duration(activities, min_duration_minutes=2)

            if not activities:
                logger.debug(
                    f"No activities remaining after duration filtering for work phase {work_phase}"
                )
                return []

            # Step 2.5: Validate activities with supervisor (check temporal continuity and semantic accuracy)
            activities = await self._validate_activities_with_supervisor(
                activities, source_actions=actions
            )

            # Step 3: Get existing activities from this session (previous work phases)
            existing_session_activities = await self._get_session_activities(session_id)

            # Step 4: Merge with existing activities from same session (relaxed threshold)
            activities_to_save, activities_to_update = await self._merge_within_session(
                new_activities=activities,
                existing_activities=existing_session_activities,
                session_id=session_id,
            )

            # Step 5: Evaluate focus scores using LLM in parallel, then save activities
            # Get focus evaluator
            focus_evaluator = get_focus_evaluator()

            # Get session context (user intent and related todos) for better evaluation
            session_context = await self._get_session_context(session_id)

            # Batch evaluate all activities in parallel
            logger.info(
                f"Starting parallel LLM focus evaluation for {len(activities_to_save)} activities"
            )
            eval_tasks = [
                focus_evaluator.evaluate_activity_focus(
                    act, session_context=session_context
                )
                for act in activities_to_save
            ]
            eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)

            # Process results with error handling and save activities
            saved_activities = []
            for activity, eval_result in zip(activities_to_save, eval_results):
                # Add pomodoro metadata
                activity["pomodoro_session_id"] = session_id
                activity["pomodoro_work_phase"] = work_phase
                activity["aggregation_mode"] = "action_based"

                # Process LLM evaluation result with fallback
                if isinstance(eval_result, Exception):
                    # Fallback to algorithm on error
                    logger.warning(
                        f"LLM evaluation failed for activity '{activity.get('title', 'Untitled')}': {eval_result}. "
                        "Falling back to algorithm-based scoring."
                    )
                    activity["focus_score"] = self._calculate_focus_score_from_actions(
                        activity
                    )
                else:
                    # Use LLM evaluation score (0-100 scale)
                    activity["focus_score"] = eval_result.get("focus_score", 50)
                    logger.debug(
                        f"LLM focus score for '{activity.get('title', 'Untitled')[:50]}': "
                        f"{activity['focus_score']} (reasoning: {eval_result.get('reasoning', '')[:100]})"
                    )

                # Save to database with ACTION sources
                await self.db.activities.save(
                    activity_id=activity["id"],
                    title=activity["title"],
                    description=activity["description"],
                    start_time=(
                        activity["start_time"].isoformat()
                        if isinstance(activity["start_time"], datetime)
                        else activity["start_time"]
                    ),
                    end_time=(
                        activity["end_time"].isoformat()
                        if isinstance(activity["end_time"], datetime)
                        else activity["end_time"]
                    ),
                    source_event_ids=None,  # NOT USED in action-based mode
                    source_action_ids=activity["source_action_ids"],  # NEW: action IDs
                    aggregation_mode="action_based",  # NEW FLAG
                    session_duration_minutes=activity.get("session_duration_minutes"),
                    topic_tags=activity.get("topic_tags", []),
                    pomodoro_session_id=activity.get("pomodoro_session_id"),
                    pomodoro_work_phase=activity.get("pomodoro_work_phase"),
                    focus_score=activity.get("focus_score"),
                )

                # NO NEED to mark events as aggregated (we're bypassing events)

                saved_activities.append(activity)
                logger.debug(
                    f"Created activity '{activity['title']}' for work phase {work_phase} "
                    f"(focus_score: {activity['focus_score']:.2f}, actions: {len(activity['source_action_ids'])})"
                )

            # Step 6: Update existing activities
            for update_data in activities_to_update:
                await self.db.activities.save(
                    activity_id=update_data["id"],
                    title=update_data["title"],
                    description=update_data["description"],
                    start_time=(
                        update_data["start_time"].isoformat()
                        if isinstance(update_data["start_time"], datetime)
                        else update_data["start_time"]
                    ),
                    end_time=(
                        update_data["end_time"].isoformat()
                        if isinstance(update_data["end_time"], datetime)
                        else update_data["end_time"]
                    ),
                    source_event_ids=None,
                    source_action_ids=update_data["source_action_ids"],
                    aggregation_mode="action_based",
                    session_duration_minutes=update_data.get("session_duration_minutes"),
                    topic_tags=update_data.get("topic_tags", []),
                    pomodoro_session_id=update_data.get("pomodoro_session_id"),
                    pomodoro_work_phase=update_data.get("pomodoro_work_phase"),
                    focus_score=update_data.get("focus_score"),
                )

                # NO NEED to mark events as aggregated (action-based mode)

                saved_activities.append(update_data)
                logger.debug(
                    f"Updated existing activity '{update_data['title']}' with new actions "
                    f"(merge reason: {update_data.get('_merge_reason', 'unknown')})"
                )

            logger.info(
                f"Work phase {work_phase} aggregation completed (ACTION-BASED): "
                f"{len(activities_to_save)} new activities, {len(activities_to_update)} updated"
            )

            return saved_activities

        except Exception as e:
            logger.error(
                f"Failed to aggregate work phase {work_phase} for session {session_id}: {e}",
                exc_info=True,
            )
            return []

    async def _get_work_phase_events(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get events within a specific work phase time window

        Includes retry mechanism to handle Action → Event aggregation delays.

        Args:
            session_id: Pomodoro session ID
            start_time: Work phase start time
            end_time: Work phase end time
            max_retries: Maximum number of retries (default: 3)

        Returns:
            List of event dictionaries
        """
        for attempt in range(max_retries):
            try:
                # Get all events in this time window
                all_events = await self.db.events.get_in_timeframe(
                    start_time.isoformat(), end_time.isoformat()
                )

                # Filter for this specific pomodoro session (if events are tagged)
                # Note: Events may not have pomodoro_session_id if they were created
                # before the session was tagged, so we'll filter primarily by time
                events = [
                    event
                    for event in all_events
                    if event.get("aggregated_into_activity_id") is None
                ]

                if events:
                    logger.debug(
                        f"Found {len(events)} unaggregated events for work phase "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    return events

                # No events found, wait and retry
                if attempt < max_retries - 1:
                    logger.debug(
                        f"No events found for work phase yet, retrying in 5s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(
                    f"Error fetching work phase events (attempt {attempt + 1}): {e}",
                    exc_info=True,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)

        # All retries exhausted
        logger.warning(
            f"No events found for work phase after {max_retries} attempts. "
            f"Time window: {start_time.isoformat()} to {end_time.isoformat()}"
        )
        return []

    async def _get_session_activities(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all activities associated with a Pomodoro session

        Args:
            session_id: Pomodoro session ID

        Returns:
            List of activity dictionaries
        """
        try:
            # Query activities by pomodoro_session_id
            # This will be implemented in activities repository
            activities = await self.db.activities.get_by_pomodoro_session(session_id)
            logger.debug(
                f"Found {len(activities)} existing activities for session {session_id}"
            )
            return activities
        except Exception as e:
            logger.error(
                f"Error fetching session activities for {session_id}: {e}",
                exc_info=True,
            )
            return []

    async def _get_session_context(
        self, session_id: str
    ) -> Dict[str, Any]:
        """
        Get session context including user intent and related todos

        Args:
            session_id: Pomodoro session ID

        Returns:
            Dictionary containing:
                - user_intent: User's description of work goal (str)
                - related_todos: List of related todo items (List[Dict])
        """
        try:
            # Get session information
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return {"user_intent": None, "related_todos": []}

            user_intent = session.get("user_intent", "")
            associated_todo_id = session.get("associated_todo_id")

            # Get related todos
            related_todos = []
            if associated_todo_id:
                # Fetch the specific associated todo
                todo = await self.db.todos.get_by_id(associated_todo_id)
                if todo and not todo.get("deleted", False):
                    related_todos.append(todo)

            logger.debug(
                f"Session context for {session_id}: intent='{user_intent[:50] if user_intent else 'None'}', "
                f"related_todos={len(related_todos)}"
            )

            return {
                "user_intent": user_intent,
                "related_todos": related_todos,
            }

        except Exception as e:
            logger.error(
                f"Error fetching session context for {session_id}: {e}",
                exc_info=True,
            )
            return {"user_intent": None, "related_todos": []}

    def _merge_activities(
        self,
        existing_activity: Dict[str, Any],
        new_activity: Dict[str, Any],
        merge_reason: str,
    ) -> Dict[str, Any]:
        """
        Merge two activities into one

        Args:
            existing_activity: The existing activity to merge into
            new_activity: The new activity to merge
            merge_reason: Reason for the merge

        Returns:
            Merged activity dictionary
        """
        # Parse timestamps
        existing_start = (
            existing_activity["start_time"]
            if isinstance(existing_activity["start_time"], datetime)
            else datetime.fromisoformat(existing_activity["start_time"])
        )
        existing_end = (
            existing_activity["end_time"]
            if isinstance(existing_activity["end_time"], datetime)
            else datetime.fromisoformat(existing_activity["end_time"])
        )
        new_start = (
            new_activity["start_time"]
            if isinstance(new_activity["start_time"], datetime)
            else datetime.fromisoformat(new_activity["start_time"])
        )
        new_end = (
            new_activity["end_time"]
            if isinstance(new_activity["end_time"], datetime)
            else datetime.fromisoformat(new_activity["end_time"])
        )

        # Merge source_event_ids
        existing_events = set(existing_activity.get("source_event_ids", []))
        new_events = set(new_activity.get("source_event_ids", []))
        all_events = list(existing_events | new_events)

        # Update time range
        merged_start = min(existing_start, new_start)
        merged_end = max(existing_end, new_end) if new_end else existing_end

        # Calculate new duration
        duration_minutes = int((merged_end - merged_start).total_seconds() / 60)

        # Merge topic tags
        existing_tags = set(existing_activity.get("topic_tags", []))
        new_tags = set(new_activity.get("topic_tags", []))
        merged_tags = list(existing_tags | new_tags)

        # Determine primary title/description based on duration
        existing_duration = (existing_end - existing_start).total_seconds()
        new_duration = (new_end - new_start).total_seconds() if new_end else 0

        if new_duration > existing_duration:
            # New activity is primary
            title = new_activity.get("title", existing_activity.get("title", ""))
            description = new_activity.get("description", "")
            if description and existing_activity.get("description"):
                description = f"{description}\n\n[Related: {existing_activity.get('title')}]\n{existing_activity.get('description')}"
            elif existing_activity.get("description"):
                description = existing_activity.get("description")
        else:
            # Existing activity is primary
            title = existing_activity.get("title", "")
            description = existing_activity.get("description", "")
            if new_activity.get("description") and new_activity.get("title"):
                if description:
                    description = f"{description}\n\n[Related: {new_activity.get('title')}]\n{new_activity.get('description')}"
                else:
                    description = new_activity.get("description", "")

        # Create merged activity
        merged_activity = {
            "id": existing_activity["id"],
            "title": title,
            "description": description,
            "start_time": merged_start,
            "end_time": merged_end,
            "source_event_ids": all_events,
            "session_duration_minutes": duration_minutes,
            "topic_tags": merged_tags,
        }

        return merged_activity

    async def _merge_within_session(
        self,
        new_activities: List[Dict[str, Any]],
        existing_activities: List[Dict[str, Any]],
        session_id: str,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Merge new activities with existing activities from the same Pomodoro session

        Uses relaxed similarity threshold compared to global merging, since activities
        within the same Pomodoro session are more likely to be related (same user intent).

        Merge conditions:
        - Must have same pomodoro_session_id
        - Case 1: Direct time overlap
        - Case 2: Time gap ≤ 5 minutes AND semantic similarity ≥ 0.5 (relaxed from 0.6)

        Args:
            new_activities: Newly generated activities from current work phase
            existing_activities: Activities from previous work phases in same session
            session_id: Pomodoro session ID

        Returns:
            Tuple of (activities_to_save, activities_to_update)
            - activities_to_save: New activities that don't merge with existing ones
            - activities_to_update: Existing activities that absorbed new activities
        """
        if not existing_activities:
            # No existing activities to merge with
            return (new_activities, [])

        # Relaxed similarity threshold for same-session merging
        session_similarity_threshold = 0.5  # Lower than global threshold (0.6)

        activities_to_save = []
        activities_to_update = []

        for new_activity in new_activities:
            merged = False

            # Check for merge with each existing activity
            for existing_activity in existing_activities:
                # Parse timestamps
                new_start = (
                    new_activity["start_time"]
                    if isinstance(new_activity["start_time"], datetime)
                    else datetime.fromisoformat(new_activity["start_time"])
                )
                new_end = (
                    new_activity["end_time"]
                    if isinstance(new_activity["end_time"], datetime)
                    else datetime.fromisoformat(new_activity["end_time"])
                )
                existing_start = (
                    existing_activity["start_time"]
                    if isinstance(existing_activity["start_time"], datetime)
                    else datetime.fromisoformat(existing_activity["start_time"])
                )
                existing_end = (
                    existing_activity["end_time"]
                    if isinstance(existing_activity["end_time"], datetime)
                    else datetime.fromisoformat(existing_activity["end_time"])
                )

                # Check merge conditions
                should_merge = False
                merge_reason = ""

                # Case 1: Time overlap
                if new_start <= existing_end and new_end >= existing_start:
                    should_merge = True
                    merge_reason = "time_overlap"

                # Case 2: Adjacent/close with semantic similarity
                else:
                    # Calculate time gap
                    if new_start > existing_end:
                        time_gap = (new_start - existing_end).total_seconds()
                    else:
                        time_gap = (existing_start - new_end).total_seconds()

                    if 0 <= time_gap <= self.merge_time_gap_tolerance:
                        # Calculate semantic similarity (reuse existing method)
                        similarity = self._calculate_activity_similarity(
                            existing_activity, new_activity
                        )

                        if similarity >= session_similarity_threshold:
                            should_merge = True
                            merge_reason = f"session_proximity_similarity (gap: {time_gap:.0f}s, similarity: {similarity:.2f})"

                if should_merge:
                    # Merge new activity into existing activity
                    merged_activity = self._merge_activities(
                        existing_activity, new_activity, merge_reason
                    )

                    # Track which new events were added
                    merged_activity["_new_event_ids"] = new_activity["source_event_ids"]
                    merged_activity["_merge_reason"] = merge_reason

                    activities_to_update.append(merged_activity)
                    merged = True

                    logger.debug(
                        f"Merging new activity '{new_activity['title']}' into "
                        f"existing '{existing_activity['title']}' (reason: {merge_reason})"
                    )
                    break

            if not merged:
                # No merge found, save as new activity
                activities_to_save.append(new_activity)

        return (activities_to_save, activities_to_update)

    def _calculate_focus_score(self, activity: Dict[str, Any]) -> float:
        """
        Calculate focus score for an activity based on multiple factors

        Focus score ranges from 0.0 (very unfocused) to 1.0 (highly focused).

        Factors:
        1. Event density (30% weight): Events per minute
           - High density (>2 events/min) → frequent task switching → lower score
           - Low density (<0.5 events/min) → sustained work or idle → moderate/high score

        2. Topic consistency (40% weight): Number of unique topics
           - 1 topic → highly focused on single subject → high score
           - 2 topics → related tasks → good score
           - 3+ topics → scattered attention → lower score

        3. Duration (30% weight): Time spent on activity
           - >20 min → deep work session → high score
           - 10-20 min → moderate work session → good score
           - 5-10 min → brief focus → moderate score
           - <5 min → very brief → low score

        Args:
            activity: Activity dictionary with source_event_ids, session_duration_minutes, topic_tags

        Returns:
            Focus score between 0.0 and 1.0
        """
        score = 1.0

        # Factor 1: Event density (30% weight)
        event_count = len(activity.get("source_event_ids", []))
        duration_minutes = activity.get("session_duration_minutes", 1)

        if duration_minutes > 0:
            events_per_minute = event_count / duration_minutes

            if events_per_minute > 2.0:
                # Too many events per minute → frequent switching
                score *= 0.7
            elif events_per_minute < 0.5:
                # Very few events → either deep focus or idle time
                # Slightly penalize to account for possible idle time
                score *= 0.95
            # else: 0.5-2.0 events/min is normal working pace, no adjustment

        # Factor 2: Topic consistency (40% weight)
        topic_count = len(activity.get("topic_tags", []))

        if topic_count == 0:
            # No topics identified → unclear focus
            score *= 0.8
        elif topic_count == 1:
            # Single topic → highly focused
            score *= 1.0
        elif topic_count == 2:
            # Two related topics → good focus
            score *= 0.9
        else:
            # Multiple topics → scattered attention
            score *= 0.7

        # Factor 3: Duration (30% weight)
        if duration_minutes > 20:
            # Deep work session
            score *= 1.0
        elif duration_minutes > 10:
            # Moderate work session
            score *= 0.8
        elif duration_minutes > 5:
            # Brief focus period
            score *= 0.6
        else:
            # Very brief activity
            score *= 0.4

        # Ensure score stays within bounds
        final_score = min(1.0, max(0.0, score))

        return round(final_score, 2)

    async def _get_work_phase_actions(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get actions within a specific work phase time window

        Args:
            session_id: Pomodoro session ID (not used for filtering, as actions don't have session_id)
            start_time: Work phase start time
            end_time: Work phase end time

        Returns:
            List of action dictionaries
        """
        try:
            # Get all actions in this time window
            actions = await self.db.actions.get_in_timeframe(
                start_time.isoformat(), end_time.isoformat()
            )

            logger.debug(
                f"Found {len(actions)} actions for work phase "
                f"({start_time.isoformat()} to {end_time.isoformat()})"
            )

            return actions

        except Exception as e:
            logger.error(
                f"Error fetching work phase actions: {e}",
                exc_info=True,
            )
            return []

    async def _cluster_actions_to_activities(
        self, actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to cluster actions into activity-level work sessions

        Uses the new 'action_aggregation' prompt (not 'session_aggregation')

        Args:
            actions: List of action dictionaries

        Returns:
            List of activity dictionaries with source_action_ids
        """
        if not actions:
            return []

        try:
            logger.debug(f"Clustering {len(actions)} actions into activities (ACTION-BASED)")

            # Build actions JSON with index
            actions_with_index = [
                {
                    "index": i + 1,
                    "title": action.get("title", ""),
                    "description": action.get("description", ""),
                    "timestamp": action.get("timestamp", ""),
                }
                for i, action in enumerate(actions)
            ]
            actions_json = json.dumps(actions_with_index, ensure_ascii=False, indent=2)

            # Get current language and prompt manager
            language = self._get_language()
            from llm.prompt_manager import get_prompt_manager

            prompt_manager = get_prompt_manager(language)

            # Build messages using NEW prompt
            messages = prompt_manager.build_messages(
                "action_aggregation",  # NEW PROMPT CATEGORY
                "user_prompt_template",
                actions_json=actions_json,
            )

            # Get configuration parameters
            config_params = prompt_manager.get_config_params("action_aggregation")

            # Call LLM
            response = await self.llm_manager.chat_completion(messages, **config_params)
            content = response.get("content", "").strip()

            # Parse JSON (already imported at top of file)
            result = parse_json_from_response(content)

            if not isinstance(result, dict):
                logger.warning(
                    f"Action clustering result format error: {content[:200]}"
                )
                return []

            activities_data = result.get("activities", [])

            # Convert to complete activity objects
            activities = []
            for activity_data in activities_data:
                # Normalize source indexes
                normalized_indexes = self._normalize_source_indexes(
                    activity_data.get("source"), len(actions)
                )

                if not normalized_indexes:
                    continue

                source_action_ids: List[str] = []
                source_actions: List[Dict[str, Any]] = []
                for idx in normalized_indexes:
                    action = actions[idx - 1]
                    action_id = action.get("id")
                    if action_id:
                        source_action_ids.append(action_id)
                    source_actions.append(action)

                if not source_actions:
                    continue

                # Get timestamps from ACTIONS (not events)
                start_time = None
                end_time = None
                for a in source_actions:
                    timestamp = a.get("timestamp")
                    if timestamp:
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp)
                        if start_time is None or timestamp < start_time:
                            start_time = timestamp
                        if end_time is None or timestamp > end_time:
                            end_time = timestamp

                if not start_time:
                    start_time = datetime.now()
                if not end_time:
                    end_time = start_time

                # Calculate duration
                duration_minutes = int((end_time - start_time).total_seconds() / 60)

                # Extract topic tags from LLM response
                topic_tags = activity_data.get("topic_tags", [])

                activity = {
                    "id": str(uuid.uuid4()),
                    "title": activity_data.get("title", "Unnamed activity"),
                    "description": activity_data.get("description", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "source_action_ids": source_action_ids,  # NEW: action IDs instead of event IDs
                    "topic_tags": topic_tags,
                    "session_duration_minutes": duration_minutes,
                    "created_at": datetime.now(),
                }

                activities.append(activity)

            logger.debug(
                f"Clustering completed: generated {len(activities)} activities from {len(actions)} actions"
            )

            return activities

        except Exception as e:
            logger.error(
                f"Failed to cluster actions to activities: {e}", exc_info=True
            )
            return []

    def _filter_activities_by_duration(
        self, activities: List[Dict[str, Any]], min_duration_minutes: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Filter out activities with duration less than min_duration_minutes

        Args:
            activities: List of activities to filter
            min_duration_minutes: Minimum duration in minutes (default: 2)

        Returns:
            Filtered list of activities
        """
        if not activities:
            return activities

        filtered_activities = []
        filtered_count = 0

        for activity in activities:
            # Calculate duration
            start_time = activity.get("start_time")
            end_time = activity.get("end_time")

            if not start_time or not end_time:
                # No time info, keep it
                filtered_activities.append(activity)
                continue

            # Convert to datetime if needed
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)

            # Calculate duration in minutes
            duration_minutes = (end_time - start_time).total_seconds() / 60

            if duration_minutes >= min_duration_minutes:
                filtered_activities.append(activity)
            else:
                filtered_count += 1
                logger.debug(
                    f"Filtered out short activity '{activity.get('title', 'Unnamed')}' "
                    f"(duration: {duration_minutes:.1f}min < {min_duration_minutes}min)"
                )

        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} activities with duration < {min_duration_minutes} minutes"
            )

        return filtered_activities

    def _calculate_focus_score_from_actions(self, activity: Dict[str, Any]) -> float:
        """
        Calculate focus score for an ACTION-BASED activity

        Similar to _calculate_focus_score() but uses actions instead of events

        Focus score factors:
        1. Action density (30% weight): Actions per minute
        2. Topic consistency (40% weight): Number of unique topics
        3. Duration (30% weight): Time spent on activity

        Args:
            activity: Activity dictionary with source_action_ids

        Returns:
            Focus score between 0.0 and 1.0
        """
        score = 1.0

        # Factor 1: Action density (30% weight)
        action_count = len(activity.get("source_action_ids", []))
        duration_minutes = activity.get("session_duration_minutes", 1)

        if duration_minutes > 0:
            actions_per_minute = action_count / duration_minutes

            # Actions are finer-grained than events, so adjust thresholds
            # Normal range: 0.5-3 actions/min (vs 0.5-2 events/min)
            if actions_per_minute > 3.0:
                # Too many actions per minute → frequent switching
                score *= 0.7
            elif actions_per_minute < 0.5:
                # Very few actions → either deep focus or idle time
                score *= 0.95
            # else: 0.5-3.0 actions/min is normal working pace, no adjustment

        # Factor 2: Topic consistency (40% weight)
        topic_count = len(activity.get("topic_tags", []))

        if topic_count == 0:
            # No topics identified → unclear focus
            score *= 0.8
        elif topic_count == 1:
            # Single topic → highly focused
            score *= 1.0
        elif topic_count == 2:
            # Two related topics → good focus
            score *= 0.9
        else:
            # Multiple topics → scattered attention
            score *= 0.7

        # Factor 3: Duration (30% weight)
        if duration_minutes > 20:
            # Deep work session
            score *= 1.0
        elif duration_minutes > 10:
            # Moderate work session
            score *= 0.8
        elif duration_minutes > 5:
            # Brief focus period
            score *= 0.6
        else:
            # Very brief activity
            score *= 0.4

        # Ensure score stays within bounds
        final_score = min(1.0, max(0.0, score))

        return round(final_score, 2)

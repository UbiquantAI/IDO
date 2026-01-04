"""
Response models for API handlers
Provides strongly typed response models for better type safety and auto-generation
"""

from typing import Any, Dict, List, Literal, Optional

from models.base import BaseModel, OperationResponse, TimedOperationResponse


# System responses
class SystemStatusData(BaseModel):
    """System status data"""

    is_running: bool
    status: str
    last_error: Optional[str] = None
    active_model: Optional[Dict[str, Any]] = None  # Can be a dict or None


class SystemResponse(BaseModel):
    """Common system operation response"""

    success: bool
    message: str = ""  # Make message optional with default
    data: Optional[Any] = None  # Allow Any for flexible data
    timestamp: str


class DatabasePathData(BaseModel):
    """Database path data"""

    path: str


class DatabasePathResponse(BaseModel):
    """Database path response"""

    success: bool
    data: DatabasePathData
    timestamp: str


class SettingsData(BaseModel):
    """Settings data"""

    llm_enabled: bool
    screenshot_quality: int
    screenshot_interval: float
    perception_enabled: bool
    keyboard_enabled: bool
    mouse_enabled: bool
    processing_interval: int


class SettingsInfoResponse(BaseModel):
    """Settings info response"""

    success: bool
    data: SettingsData
    timestamp: str


class UpdateSettingsResponse(BaseModel):
    """Update settings response"""

    success: bool
    message: str
    timestamp: str


# Activity responses
class ActivityCountData(BaseModel):
    """Activity count data"""

    date_count_map: Dict[str, int]
    total_dates: int
    total_activities: int


class ActivityCountResponse(BaseModel):
    """Activity count by date response"""

    success: bool
    data: ActivityCountData
    error: str = ""


class IncrementalActivitiesData(BaseModel):
    """Incremental activities data"""

    activities: List[Dict[str, Any]]
    count: int
    max_version: int


class IncrementalActivitiesResponse(BaseModel):
    """Incremental activities response"""

    success: bool
    data: IncrementalActivitiesData


# Generic data response (for handlers returning arbitrary data)
class DataResponse(TimedOperationResponse):
    """Generic response with data field and timestamp"""

    pass  # Inherits: success, message, error, data, timestamp


# Three-Layer Architecture Response Models (Activities → Events → Actions)
class EventResponse(BaseModel):
    """Event response data for three-layer architecture"""

    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    source_action_ids: List[str]
    created_at: str


class GetEventsByActivityResponse(OperationResponse):
    """Response containing events for a specific activity"""

    events: List[EventResponse]


class ActionResponse(BaseModel):
    """Action response data for three-layer architecture"""

    id: str
    title: str
    description: str
    keywords: List[str]
    timestamp: str
    screenshots: List[str]
    created_at: str


class GetActionsByEventResponse(OperationResponse):
    """Response containing actions for a specific event"""

    actions: List[ActionResponse]


class MergeActivitiesResponse(OperationResponse):
    """Response after merging multiple activities"""

    merged_activity_id: str = ""


class SplitActivityResponse(OperationResponse):
    """Response after splitting an activity into multiple activities"""

    new_activity_ids: List[str] = []


# Image Management Response Models
class ImageStatsResponse(OperationResponse):
    """Response containing image cache statistics"""

    stats: Optional[Dict[str, Any]] = None


class CachedImagesResponse(OperationResponse):
    """Response containing cached images in base64 format"""

    images: Dict[str, str]
    found_count: int
    requested_count: int


class CleanupImagesResponse(OperationResponse):
    """Response after cleaning up old images"""

    cleaned_count: int = 0


class ClearMemoryCacheResponse(OperationResponse):
    """Response after clearing memory cache"""

    cleared_count: int = 0


class ImageOptimizationConfigResponse(OperationResponse):
    """Response containing image optimization configuration"""

    config: Optional[Dict[str, Any]] = None


class ImageOptimizationStatsResponse(OperationResponse):
    """Response containing image optimization statistics"""

    stats: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class ImagePersistenceHealthData(BaseModel):
    """Data model for image persistence health check"""

    total_actions: int
    actions_with_screenshots: int
    actions_all_images_ok: int
    actions_partial_missing: int
    actions_all_missing: int
    total_image_references: int
    images_found: int
    images_missing: int
    missing_rate_percent: float
    memory_cache_current_size: int
    memory_cache_max_size: int
    memory_ttl_seconds: int
    actions_with_issues: List[Dict[str, Any]]


class ImagePersistenceHealthResponse(OperationResponse):
    """Response containing image persistence health check results"""

    data: Optional[ImagePersistenceHealthData] = None


class CleanupBrokenActionsResponse(OperationResponse):
    """Response after cleaning up broken action images"""

    actions_processed: int = 0
    actions_deleted: int = 0
    references_removed: int = 0
    images_removed: int = 0


class UpdateImageOptimizationConfigResponse(OperationResponse):
    """Response after updating image optimization configuration"""

    config: Optional[Dict[str, Any]] = None


class ReadImageFileResponse(OperationResponse):
    """Response containing image file data as base64"""

    data_url: str = ""


# Insights Module Response Models
class DiaryData(BaseModel):
    """Diary data"""

    id: str
    date: str
    content: str
    source_activity_ids: List[str]
    created_at: str


class GenerateDiaryResponse(OperationResponse):
    """Response after generating a diary"""

    data: Optional[DiaryData] = None
    timestamp: str = ""


class DiaryListData(BaseModel):
    """Diary list data"""

    diaries: List[DiaryData]
    count: int


class GetDiaryListResponse(OperationResponse):
    """Response containing diary list"""

    data: Optional[DiaryListData] = None
    timestamp: str = ""


class DeleteDiaryResponse(OperationResponse):
    """Response after deleting a diary"""

    timestamp: str = ""


# System Settings Response Models
class SettingsInfoData(BaseModel):
    """Settings info data structure"""

    settings: Dict[str, Any]
    database: Dict[str, str]
    screenshot: Dict[str, str]
    language: str
    image: Dict[str, Any]


class GetSettingsInfoResponse(TimedOperationResponse):
    """Response for get_settings_info handler"""

    data: Optional[SettingsInfoData] = None


class ImageOptimizationConfigData(BaseModel):
    """Image optimization configuration data"""

    enabled: bool = True
    strategy: str = "phash"
    phash_threshold: int = 10
    min_interval: float = 0.5
    enable_content_analysis: bool = True
    enable_text_detection: bool = True


class GetImageOptimizationConfigResponse(TimedOperationResponse):
    """Response for get_image_optimization_config handler"""

    data: Optional[ImageOptimizationConfigData] = None


class UpdateImageOptimizationConfigResponseV2(TimedOperationResponse):
    """Response for update_image_optimization_config handler"""

    data: Optional[ImageOptimizationConfigData] = None


class ImageCompressionConfigData(BaseModel):
    """Image compression configuration data"""

    compression_level: int = 85
    enable_region_cropping: bool = False
    crop_threshold: float = 0.8


class GetImageCompressionConfigResponse(TimedOperationResponse):
    """Response for get_image_compression_config handler"""

    data: Optional[ImageCompressionConfigData] = None


class UpdateImageCompressionConfigResponseV2(TimedOperationResponse):
    """Response for update_image_compression_config handler"""

    data: Optional[ImageCompressionConfigData] = None


class ImageCompressionStatsData(BaseModel):
    """Image compression statistics data"""

    total_processed: int = 0
    total_saved_bytes: int = 0
    average_compression_ratio: float = 0.0


class GetImageCompressionStatsResponse(TimedOperationResponse):
    """Response for get_image_compression_stats handler"""

    data: Optional[ImageCompressionStatsData] = None


class InitialSetupData(BaseModel):
    """Initial setup check data"""

    has_models: bool
    has_active_model: bool
    has_completed_setup: bool
    needs_setup: bool
    model_count: int


class CheckInitialSetupResponse(TimedOperationResponse):
    """Response for check_initial_setup handler"""

    data: Optional[InitialSetupData] = None


class CompleteInitialSetupResponse(TimedOperationResponse):
    """Response for complete_initial_setup handler"""

    pass


# Pomodoro Feature Response Models
class PomodoroSessionData(BaseModel):
    """Pomodoro session data with rounds support"""

    session_id: str
    user_intent: str
    start_time: str
    elapsed_minutes: int
    planned_duration_minutes: int
    associated_todo_id: Optional[str] = None
    associated_todo_title: Optional[str] = None
    # Rounds configuration
    work_duration_minutes: int = 25
    break_duration_minutes: int = 5
    total_rounds: int = 4
    current_round: int = 1
    current_phase: Literal["work", "break", "completed"] = "work"
    phase_start_time: Optional[str] = None
    completed_rounds: int = 0
    # Calculated fields for frontend
    remaining_phase_seconds: Optional[int] = None
    pure_work_duration_minutes: int = 0  # completed_rounds × work_duration_minutes (excludes breaks)


class StartPomodoroResponse(TimedOperationResponse):
    """Response after starting a Pomodoro session"""

    data: Optional[PomodoroSessionData] = None


class EndPomodoroData(BaseModel):
    """End Pomodoro session result data"""

    session_id: str
    processing_job_id: Optional[str] = None
    raw_records_count: int = 0
    message: str = ""


class EndPomodoroResponse(TimedOperationResponse):
    """Response after ending a Pomodoro session"""

    data: Optional[EndPomodoroData] = None


class GetPomodoroStatusResponse(TimedOperationResponse):
    """Response for getting current Pomodoro session status"""

    data: Optional[PomodoroSessionData] = None


# Pomodoro Session Detail Models (with activities and focus metrics)


class PomodoroActivityData(BaseModel):
    """Activity data for Pomodoro session detail view"""

    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    session_duration_minutes: int
    work_phase: Optional[int] = None  # Which work round (1-4)
    focus_score: Optional[float] = None  # Focus metric (0.0-1.0)
    topic_tags: List[str] = []
    source_event_ids: List[str] = []  # Deprecated, for backward compatibility
    source_action_ids: List[str] = []  # NEW: Primary source for action-based aggregation
    aggregation_mode: str = "action_based"  # NEW: 'event_based' or 'action_based'


class PhaseTimelineItem(BaseModel):
    """Single phase in timeline (work or break)"""

    phase_type: Literal["work", "break"]
    phase_number: int  # 1-based round number
    start_time: str
    end_time: str
    duration_minutes: int


class FocusMetrics(BaseModel):
    """Focus metrics for a Pomodoro session"""

    overall_focus_score: float  # Weighted average focus score (0.0-1.0)
    activity_count: int  # Number of activities in session
    topic_diversity: int  # Number of unique topics
    average_activity_duration: float  # Average duration per activity (minutes)
    focus_level: str  # Human-readable level: excellent/good/moderate/low


class LLMFocusAnalysis(BaseModel):
    """Detailed focus analysis from LLM evaluation"""

    strengths: List[str]  # Focus strengths (2-4 items)
    weaknesses: List[str]  # Focus weaknesses (1-3 items)
    suggestions: List[str]  # Improvement suggestions (2-4 items)


class LLMFocusDimensionScores(BaseModel):
    """Detailed dimension scores from LLM evaluation"""

    topic_consistency: int  # 0-100 score for topic consistency
    duration_depth: int  # 0-100 score for duration depth
    switching_rhythm: int  # 0-100 score for switching rhythm
    work_quality: int  # 0-100 score for work quality
    goal_orientation: int  # 0-100 score for goal orientation


class LLMFocusEvaluation(BaseModel):
    """Complete LLM-based focus evaluation result"""

    focus_score: int  # 0-100 integer score
    focus_level: Literal["excellent", "good", "moderate", "low"]  # Focus quality level
    dimension_scores: LLMFocusDimensionScores  # Detailed dimension scores
    analysis: LLMFocusAnalysis  # Detailed analysis
    work_type: Literal[
        "development",
        "writing",
        "learning",
        "research",
        "design",
        "communication",
        "entertainment",
        "productivity_analysis",
        "mixed",
        "unclear",
    ]  # Type of work activity
    is_focused_work: bool  # Whether it's high-quality focused work
    distraction_percentage: int  # Distraction time percentage (0-100)
    deep_work_minutes: float  # Deep work duration (minutes)
    context_summary: str  # Overall work summary


class PomodoroSessionDetailData(BaseModel):
    """Detailed Pomodoro session with activities and focus metrics"""

    session: Dict[str, Any]  # Full session data
    activities: List[PomodoroActivityData]
    focus_metrics: FocusMetrics  # Calculated focus metrics
    llm_focus_evaluation: Optional[LLMFocusEvaluation] = None  # LLM-based detailed evaluation
    phase_timeline: List[PhaseTimelineItem] = []  # Work/break phase timeline


class GetPomodoroSessionDetailRequest(BaseModel):
    """Request to get detailed Pomodoro session information"""

    session_id: str


class GetPomodoroSessionDetailResponse(TimedOperationResponse):
    """Response with detailed Pomodoro session data"""

    data: Optional[PomodoroSessionDetailData] = None


class DeletePomodoroSessionRequest(BaseModel):
    """Request to delete a Pomodoro session"""

    session_id: str


class DeletePomodoroSessionData(BaseModel):
    """Data returned after deleting a session"""

    session_id: str
    deleted_activities_count: int


class DeletePomodoroSessionResponse(TimedOperationResponse):
    """Response after deleting a Pomodoro session"""

    data: Optional[DeletePomodoroSessionData] = None


# Knowledge responses
class KnowledgeData(BaseModel):
    """Knowledge item data"""

    id: str
    title: str
    description: str
    keywords: List[str]
    created_at: Optional[str] = None
    source_action_id: Optional[str] = None
    favorite: bool = False
    deleted: bool = False


class ToggleKnowledgeFavoriteResponse(TimedOperationResponse):
    """Response after toggling knowledge favorite status"""

    data: Optional[KnowledgeData] = None


class CreateKnowledgeResponse(TimedOperationResponse):
    """Response after creating knowledge"""

    data: Optional[KnowledgeData] = None


class UpdateKnowledgeResponse(TimedOperationResponse):
    """Response after updating knowledge"""

    data: Optional[KnowledgeData] = None



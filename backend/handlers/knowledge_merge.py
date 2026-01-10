"""
Knowledge merge handlers for analyzing and merging similar knowledge entries.
"""

from datetime import datetime
from typing import cast

from core.db import get_db
from core.logger import get_logger
from core.protocols import KnowledgeRepositoryProtocol
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager
from models.requests import (
    AnalyzeKnowledgeMergeRequest,
    ExecuteKnowledgeMergeRequest,
    MergeGroup,
)
from models.responses import (
    AnalyzeKnowledgeMergeResponse,
    ExecuteKnowledgeMergeResponse,
    MergeSuggestion,
    MergeResult,
)
from services.knowledge_merger import KnowledgeMerger

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


@api_handler(
    body=AnalyzeKnowledgeMergeRequest,
    method="POST",
    path="/knowledge/analyze-merge",
    tags=["knowledge"],
)
async def analyze_knowledge_merge(
    body: AnalyzeKnowledgeMergeRequest,
) -> AnalyzeKnowledgeMergeResponse:
    """
    Analyze knowledge entries for similarity and generate merge suggestions.
    Uses LLM to detect similar content and propose merges.
    """
    try:
        db = get_db()
        knowledge_repo = cast(KnowledgeRepositoryProtocol, db.knowledge)
        llm_manager = get_llm_manager()
        prompt_manager = PromptManager()

        merger = KnowledgeMerger(knowledge_repo, prompt_manager, llm_manager)

        # Analyze similarities
        suggestions_data, total_tokens = await merger.analyze_similarities(
            filter_by_keyword=body.filter_by_keyword,
            include_favorites=body.include_favorites,
            similarity_threshold=body.similarity_threshold,
        )

        # Convert to response models
        suggestions = [
            MergeSuggestion(
                group_id=s.group_id,
                knowledge_ids=s.knowledge_ids,
                merged_title=s.merged_title,
                merged_description=s.merged_description,
                merged_keywords=s.merged_keywords,
                similarity_score=s.similarity_score,
                merge_reason=s.merge_reason,
                estimated_tokens=s.estimated_tokens,
            )
            for s in suggestions_data
        ]

        # Calculate analyzed count
        knowledge_list = await merger._fetch_knowledge(
            body.filter_by_keyword, body.include_favorites
        )

        logger.info(
            f"Analyzed {len(knowledge_list)} knowledge entries, "
            f"found {len(suggestions)} merge suggestions, "
            f"used {total_tokens} tokens"
        )

        return AnalyzeKnowledgeMergeResponse(
            success=True,
            message=f"Found {len(suggestions)} merge suggestions",
            timestamp=datetime.now().isoformat(),
            suggestions=suggestions,
            total_estimated_tokens=total_tokens,
            analyzed_count=len(knowledge_list),
            suggested_merge_count=len(suggestions),
        )

    except Exception as e:
        logger.error(f"Failed to analyze knowledge merge: {e}", exc_info=True)
        return AnalyzeKnowledgeMergeResponse(
            success=False,
            message="Failed to analyze knowledge merge",
            error=str(e),
            timestamp=datetime.now().isoformat(),
            suggestions=[],
            total_estimated_tokens=0,
            analyzed_count=0,
            suggested_merge_count=0,
        )


@api_handler(
    body=ExecuteKnowledgeMergeRequest,
    method="POST",
    path="/knowledge/execute-merge",
    tags=["knowledge"],
)
async def execute_knowledge_merge(
    body: ExecuteKnowledgeMergeRequest,
) -> ExecuteKnowledgeMergeResponse:
    """
    Execute approved knowledge merge operations.
    Creates merged knowledge entries and soft-deletes sources.
    """
    try:
        db = get_db()
        knowledge_repo = cast(KnowledgeRepositoryProtocol, db.knowledge)
        llm_manager = get_llm_manager()
        prompt_manager = PromptManager()

        merger = KnowledgeMerger(knowledge_repo, prompt_manager, llm_manager)

        # Convert request models to service models
        merge_groups = []
        for group in body.merge_groups:
            from services.knowledge_merger import MergeGroup as ServiceMergeGroup

            merge_groups.append(
                ServiceMergeGroup(
                    group_id=group.group_id,
                    knowledge_ids=group.knowledge_ids,
                    merged_title=group.merged_title,
                    merged_description=group.merged_description,
                    merged_keywords=group.merged_keywords,
                    merge_reason=group.merge_reason,
                    keep_favorite=group.keep_favorite,
                )
            )

        # Execute merge
        results_data = await merger.execute_merge(merge_groups)

        # Convert to response models
        results = [
            MergeResult(
                group_id=r.group_id,
                merged_knowledge_id=r.merged_knowledge_id,
                deleted_knowledge_ids=r.deleted_knowledge_ids,
                success=r.success,
                error=r.error,
            )
            for r in results_data
        ]

        total_merged = sum(1 for r in results if r.success)
        total_deleted = sum(len(r.deleted_knowledge_ids) for r in results if r.success)

        logger.info(
            f"Executed merge: {total_merged}/{len(results)} groups successful, "
            f"{total_deleted} knowledge entries deleted"
        )

        return ExecuteKnowledgeMergeResponse(
            success=True,
            message=f"Successfully merged {total_merged} groups",
            timestamp=datetime.now().isoformat(),
            results=results,
            total_merged=total_merged,
            total_deleted=total_deleted,
        )

    except Exception as e:
        logger.error(f"Failed to execute knowledge merge: {e}", exc_info=True)
        return ExecuteKnowledgeMergeResponse(
            success=False,
            message="Failed to execute knowledge merge",
            error=str(e),
            timestamp=datetime.now().isoformat(),
            results=[],
            total_merged=0,
            total_deleted=0,
        )

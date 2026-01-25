from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import json
import uuid

from core.logger import get_logger
from llm.manager import get_llm_manager
from llm.prompt_manager import PromptManager
from core.protocols import KnowledgeRepositoryProtocol

logger = get_logger(__name__)


class MergeSuggestion:
    """Represents a suggested merge of similar knowledge entries"""

    def __init__(
        self,
        group_id: str,
        knowledge_ids: List[str],
        merged_title: str,
        merged_description: str,
        merged_keywords: List[str],
        similarity_score: float,
        merge_reason: str,
        estimated_tokens: int = 0,
    ):
        self.group_id = group_id
        self.knowledge_ids = knowledge_ids
        self.merged_title = merged_title
        self.merged_description = merged_description
        self.merged_keywords = merged_keywords
        self.similarity_score = similarity_score
        self.merge_reason = merge_reason
        self.estimated_tokens = estimated_tokens


class MergeGroup:
    """Represents a user-confirmed merge group"""

    def __init__(
        self,
        group_id: str,
        knowledge_ids: List[str],
        merged_title: str,
        merged_description: str,
        merged_keywords: List[str],
        merge_reason: Optional[str] = None,
        keep_favorite: bool = True,
    ):
        self.group_id = group_id
        self.knowledge_ids = knowledge_ids
        self.merged_title = merged_title
        self.merged_description = merged_description
        self.merged_keywords = merged_keywords
        self.merge_reason = merge_reason
        self.keep_favorite = keep_favorite


class MergeResult:
    """Result of executing a merge operation"""

    def __init__(
        self,
        group_id: str,
        merged_knowledge_id: str,
        deleted_knowledge_ids: List[str],
        success: bool,
        error: Optional[str] = None,
    ):
        self.group_id = group_id
        self.merged_knowledge_id = merged_knowledge_id
        self.deleted_knowledge_ids = deleted_knowledge_ids
        self.success = success
        self.error = error


class KnowledgeMerger:
    """Service for analyzing and merging similar knowledge entries"""

    _instance: Optional["KnowledgeMerger"] = None
    _lock: bool = False  # Global lock for analysis state

    def __init__(
        self,
        knowledge_repo: KnowledgeRepositoryProtocol,
        prompt_manager: PromptManager,
        llm_manager,
    ):
        self.knowledge_repo = knowledge_repo
        self.prompt_manager = prompt_manager
        self.llm_manager = llm_manager

    @classmethod
    def get_instance(
        cls,
        knowledge_repo: Optional[KnowledgeRepositoryProtocol] = None,
        prompt_manager: Optional[PromptManager] = None,
        llm_manager = None,
    ) -> "KnowledgeMerger":
        """Get singleton instance of KnowledgeMerger"""
        if cls._instance is None:
            if knowledge_repo is None or prompt_manager is None or llm_manager is None:
                raise ValueError(
                    "First initialization requires all parameters: knowledge_repo, prompt_manager, llm_manager"
                )
            cls._instance = cls(knowledge_repo, prompt_manager, llm_manager)
        return cls._instance

    @classmethod
    def is_locked(cls) -> bool:
        """Check if analysis is currently in progress"""
        return cls._lock

    @classmethod
    def set_lock(cls, locked: bool) -> None:
        """Set the lock state"""
        cls._lock = locked

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        """
        Check if LLM service is available.

        Returns:
            (is_available, error_message)
        """
        try:
            result = await self.llm_manager.health_check()
            if result.get("available"):
                logger.info(
                    f"LLM health check passed: {result.get('model')} "
                    f"({result.get('provider')}), latency={result.get('latency_ms')}ms"
                )
                return True, None
            else:
                error = result.get("error", "Unknown error")
                logger.warning(f"LLM health check failed: {error}")
                return False, f"LLM service unavailable: {error}"
        except Exception as e:
            logger.error(f"LLM health check error: {e}")
            return False, f"Health check error: {str(e)}"

    async def analyze_similarities(
        self,
        filter_by_keyword: Optional[str],
        include_favorites: bool,
        similarity_threshold: float,
    ) -> Tuple[List[MergeSuggestion], int]:
        """
        Analyze knowledge entries for similarity and generate merge suggestions.

        Args:
            filter_by_keyword: Only analyze knowledge with this keyword (None = all)
            include_favorites: Whether to include favorite knowledge
            similarity_threshold: Similarity threshold (0.0-1.0)

        Returns:
            (suggestions, total_tokens_used)
        """
        # Check if analysis is already in progress
        if self.is_locked():
            raise RuntimeError("Knowledge analysis is already in progress. Please wait for it to complete.")

        # Set lock to prevent concurrent analysis
        self.set_lock(True)
        logger.info("Knowledge analysis started - lock acquired")

        try:
            # 0. Check LLM availability first
            llm_available, llm_error = await self.health_check()
            if not llm_available:
                logger.error(f"LLM service not available: {llm_error}")
                raise RuntimeError(
                    f"Cannot analyze knowledge: LLM service is not available. "
                    f"{llm_error}"
                )
        except Exception as e:
            # Release lock on any error during initialization
            self.set_lock(False)
            logger.info("Knowledge analysis initialization failed - lock released")
            raise

        # 1. Fetch knowledge from database
        knowledge_list = await self._fetch_knowledge(
            filter_by_keyword, include_favorites
        )

        if len(knowledge_list) < 2:
            logger.info("Not enough knowledge entries to analyze")
            self.set_lock(False)
            logger.info("Knowledge analysis - not enough data - lock released")
            return [], 0

        # 2. Group by keywords (tag-based categorization)
        grouped = self._group_by_keywords(knowledge_list)

        # 3. Analyze each group with LLM
        all_suggestions = []
        total_tokens = 0

        try:
            for keyword, group in grouped.items():
                if len(group) < 2:
                    continue  # Skip groups with single item

                logger.info(f"Analyzing group '{keyword}' with {len(group)} entries")
                suggestions, tokens = await self._analyze_group(group, similarity_threshold)
                all_suggestions.extend(suggestions)
                total_tokens += tokens

            logger.info(f"Analysis completed - lock will be released, found {len(all_suggestions)} suggestions")
            return all_suggestions, total_tokens
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise
        finally:
            # Always release lock when done (success or error)
            self.set_lock(False)
            logger.info("Knowledge analysis finished - lock released")

    async def _fetch_knowledge(
        self, filter_by_keyword: Optional[str], include_favorites: bool
    ) -> List[Dict[str, Any]]:
        """Fetch knowledge entries based on filter criteria"""
        all_knowledge = await self.knowledge_repo.get_list(include_deleted=False)

        filtered = all_knowledge

        # Filter by keyword
        if filter_by_keyword:
            filtered = [k for k in filtered if filter_by_keyword in k.get("keywords", [])]

        # Filter favorites
        if not include_favorites:
            filtered = [k for k in filtered if not k.get("favorite", False)]

        return filtered

    def _group_by_keywords(
        self, knowledge_list: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group knowledge by primary keyword (first keyword).
        Knowledge without keywords goes to 'untagged' group.
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for k in knowledge_list:
            keywords = k.get("keywords", [])
            primary_keyword = keywords[0] if keywords else "untagged"
            if primary_keyword not in groups:
                groups[primary_keyword] = []
            groups[primary_keyword].append(k)

        return groups

    async def _analyze_group(
        self, group: List[Dict[str, Any]], threshold: float
    ) -> Tuple[List[MergeSuggestion], int]:
        """
        Use LLM to analyze similarity within a group and generate merge suggestions.

        Strategy:
        1. Send group to LLM with prompt asking for similarity analysis
        2. LLM returns clusters of similar knowledge
        3. For each cluster, LLM generates merged title/description
        """
        # Build prompt with knowledge details
        knowledge_json = json.dumps(
            [
                {
                    "id": k.get("id"),
                    "title": k.get("title"),
                    "description": k.get("description"),
                    "keywords": k.get("keywords", []),
                }
                for k in group
            ],
            ensure_ascii=False,
            indent=2,
        )

        # Build messages with template variables
        messages = self.prompt_manager.build_messages(
            category="knowledge_merge_analysis",
            prompt_type="user_prompt_template",
            knowledge_json=knowledge_json,
            threshold=threshold,
        )

        # Get config params
        config_params = self.prompt_manager.get_config_params("knowledge_merge_analysis")
        max_tokens = config_params.get("max_tokens", 4000)
        temperature = config_params.get("temperature", 0.3)

        try:
            # Call LLM
            response = await self.llm_manager.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.get("content", "")
            usage = response.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            try:
                result = json.loads(content)
                suggestions = self._parse_llm_suggestions(result, group, tokens_used)
                return suggestions, tokens_used
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                logger.error(f"Response content: {content}")
                return [], tokens_used

        except Exception as e:
            logger.error(f"Failed to call LLM for group analysis: {e}", exc_info=True)
            return [], 0

    def _parse_llm_suggestions(
        self, llm_result: Dict, group: List[Dict[str, Any]], tokens_used: int
    ) -> List[MergeSuggestion]:
        """
        Parse LLM response into MergeSuggestion objects.

        Expected LLM response format:
        {
            "merge_clusters": [
                {
                    "knowledge_ids": ["id1", "id2", "id3"],
                    "merged_title": "...",
                    "merged_description": "...",
                    "merged_keywords": ["tag1", "tag2"],
                    "similarity_score": 0.85,
                    "merge_reason": "These entries discuss the same topic..."
                }
            ]
        }
        """
        suggestions = []

        for idx, cluster in enumerate(llm_result.get("merge_clusters", [])):
            # Validate required fields
            if not cluster.get("knowledge_ids"):
                logger.warning(f"Cluster {idx} missing knowledge_ids, skipping")
                continue

            # Collect keywords from all knowledge in cluster
            all_keywords = set()
            for kid in cluster["knowledge_ids"]:
                k = next((k for k in group if k.get("id") == kid), None)
                if k:
                    keywords = k.get("keywords", [])
                    if keywords:
                        all_keywords.update(keywords)

            # Use LLM-provided keywords if available, otherwise use collected keywords
            merged_keywords = cluster.get("merged_keywords", list(all_keywords))

            suggestion = MergeSuggestion(
                group_id=f"merge_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}",
                knowledge_ids=cluster["knowledge_ids"],
                merged_title=cluster.get("merged_title", "Merged Knowledge"),
                merged_description=cluster.get("merged_description", ""),
                merged_keywords=merged_keywords,
                similarity_score=cluster.get("similarity_score", 0.0),
                merge_reason=cluster.get("merge_reason", "Similar content detected"),
                estimated_tokens=tokens_used // len(llm_result.get("merge_clusters", [])),
            )
            suggestions.append(suggestion)

        return suggestions

    async def execute_merge(
        self, merge_groups: List[MergeGroup]
    ) -> List[MergeResult]:
        """
        Execute approved merge operations.

        For each group:
        1. Create new merged knowledge entry
        2. Soft-delete source knowledge entries
        3. Record merge history (optional)
        """
        results = []

        for group in merge_groups:
            try:
                # Create merged knowledge
                merged_id = f"k_{uuid.uuid4().hex}"

                # Fetch source knowledge to check favorites
                all_knowledge = await self.knowledge_repo.get_list(include_deleted=False)
                sources = [k for k in all_knowledge if k.get("id") in group.knowledge_ids]

                # Check if any source is favorite
                is_favorite = any(k.get("favorite", False) for k in sources)

                # Create new knowledge
                await self.knowledge_repo.save(
                    knowledge_id=merged_id,
                    title=group.merged_title,
                    description=group.merged_description,
                    keywords=group.merged_keywords,
                    source_action_id=None,  # No single source
                    favorite=is_favorite and group.keep_favorite,
                )

                logger.info(f"Created merged knowledge: {merged_id}")

                # Hard-delete source knowledge (permanent deletion for merge operation)
                deleted_ids = []
                for kid in group.knowledge_ids:
                    try:
                        await self.knowledge_repo.hard_delete(kid)
                        deleted_ids.append(kid)
                        logger.info(f"Hard deleted source knowledge: {kid}")
                    except Exception as e:
                        logger.error(f"Failed to hard delete knowledge {kid}: {e}")

                # Record history (if implemented)
                # await self._record_merge_history(merged_id, group.knowledge_ids, group.merge_reason)

                results.append(
                    MergeResult(
                        group_id=group.group_id,
                        merged_knowledge_id=merged_id,
                        deleted_knowledge_ids=deleted_ids,
                        success=True,
                    )
                )

            except Exception as e:
                logger.error(f"Failed to merge group {group.group_id}: {e}", exc_info=True)
                results.append(
                    MergeResult(
                        group_id=group.group_id,
                        merged_knowledge_id="",
                        deleted_knowledge_ids=[],
                        success=False,
                        error=str(e),
                    )
                )

        return results

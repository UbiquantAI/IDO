import { useEffect, useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Loader2, Plus, Search, Sparkles } from 'lucide-react'
import { useInsightsStore, type MergeSuggestion } from '@/lib/stores/insights'
import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { KnowledgeCard } from '@/components/insights/KnowledgeCard'
import { CategorySidebar } from '@/components/insights/CategorySidebar'
import { KnowledgeFilterTabs } from '@/components/insights/KnowledgeFilterTabs'
import { NewNoteDialog } from '@/components/insights/NewNoteDialog'
import { KnowledgeDetailDialog } from '@/components/insights/KnowledgeDetailDialog'
import { KnowledgeMergeDialog, type MergeConfig } from '@/components/insights/KnowledgeMergeDialog'
import { MergeSuggestionsDialog } from '@/components/insights/MergeSuggestionsDialog'
import { RetryDialog } from '@/components/ui/retry-dialog'
import { useKnowledgeSync } from '@/hooks/useKnowledgeSync'
import type { InsightKnowledge } from '@/lib/services/insights'

type FilterType = 'all' | 'favorites' | 'recent'

export default function AIKnowledgeView() {
  const { t } = useTranslation()

  // Enable knowledge auto-sync
  useKnowledgeSync()

  const knowledge = useInsightsStore((state) => state.knowledge)
  const loading = useInsightsStore((state) => state.loadingKnowledge)
  const refreshKnowledge = useInsightsStore((state) => state.refreshKnowledge)
  const removeKnowledge = useInsightsStore((state) => state.removeKnowledge)
  const toggleKnowledgeFavorite = useInsightsStore((state) => state.toggleKnowledgeFavorite)
  const createKnowledge = useInsightsStore((state) => state.createKnowledge)
  const updateKnowledge = useInsightsStore((state) => state.updateKnowledge)
  const analyzeMerge = useInsightsStore((state) => state.analyzeMerge)
  const executeMerge = useInsightsStore((state) => state.executeMerge)
  const lastError = useInsightsStore((state) => state.lastError)
  const clearError = useInsightsStore((state) => state.clearError)

  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [newNoteDialogOpen, setNewNoteDialogOpen] = useState(false)
  const [selectedKnowledge, setSelectedKnowledge] = useState<InsightKnowledge | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [showMergeDialog, setShowMergeDialog] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [mergeSuggestions, setMergeSuggestions] = useState<MergeSuggestion[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isMerging, setIsMerging] = useState(false)

  // Retry dialog state for LLM errors
  const [retryDialogOpen, setRetryDialogOpen] = useState(false)
  const [retryError, setRetryError] = useState<string>('')
  const [pendingMergeConfig, setPendingMergeConfig] = useState<MergeConfig | null>(null)

  useEffect(() => {
    void refreshKnowledge()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!lastError) return
    toast.error(lastError)
    clearError()
  }, [lastError, clearError])

  const handleToggleFavorite = async (id: string) => {
    try {
      await toggleKnowledgeFavorite(id)
      const item = knowledge.find((k) => k.id === id)
      toast.success(item?.favorite ? t('insights.unfavorited') : t('insights.favorited'))
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await removeKnowledge(id)
      toast.success(t('insights.deleteSuccess'))
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  const handleCreateNote = async (title: string, description: string, keywords: string[]) => {
    try {
      await createKnowledge(title, description, keywords)
      toast.success(t('insights.knowledgeCreated'))
    } catch (error) {
      toast.error(t('insights.createKnowledgeFailed'))
      throw error
    }
  }

  const handleUpdateKnowledge = async (id: string, title: string, description: string, keywords: string[]) => {
    try {
      await updateKnowledge(id, title, description, keywords)
      toast.success(t('insights.knowledgeUpdated', 'Knowledge updated successfully'))
    } catch (error) {
      toast.error(t('insights.updateKnowledgeFailed', 'Failed to update knowledge'))
      throw error
    }
  }

  const handleViewKnowledge = (knowledge: InsightKnowledge) => {
    setSelectedKnowledge(knowledge)
    setDetailDialogOpen(true)
  }

  const handleStartAnalysis = async (config: MergeConfig) => {
    setShowMergeDialog(false)
    setIsAnalyzing(true)

    try {
      const suggestions = await analyzeMerge({
        filterByKeyword: config.filterByKeyword,
        includeFavorites: config.includeFavorites,
        similarityThreshold: config.similarityThreshold
      })

      if (suggestions.length === 0) {
        toast.info(t('insights.merge.noSuggestions'))
        return
      }

      setMergeSuggestions(suggestions)
      setShowSuggestions(true)
    } catch (error) {
      const errorMessage = (error as Error).message
      // Check if it's an LLM service error that should show retry dialog
      if (errorMessage.includes('LLM service') || errorMessage.includes('LLM service unavailable')) {
        setRetryError(errorMessage)
        setPendingMergeConfig(config)
        setRetryDialogOpen(true)
      } else {
        toast.error(t('insights.merge.error', { error: errorMessage }))
      }
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleRetryAnalysis = async () => {
    if (!pendingMergeConfig) return

    try {
      const suggestions = await analyzeMerge({
        filterByKeyword: pendingMergeConfig.filterByKeyword,
        includeFavorites: pendingMergeConfig.includeFavorites,
        similarityThreshold: pendingMergeConfig.similarityThreshold
      })

      if (suggestions.length === 0) {
        toast.info(t('insights.merge.noSuggestions'))
        return
      }

      setMergeSuggestions(suggestions)
      setShowSuggestions(true)
    } catch (error) {
      const errorMessage = (error as Error).message
      if (errorMessage.includes('LLM service') || errorMessage.includes('LLM service unavailable')) {
        // Keep retry dialog open for another retry attempt
        setRetryError(errorMessage)
      } else {
        setRetryDialogOpen(false)
        toast.error(t('insights.merge.error', { error: errorMessage }))
      }
    }
  }

  const handleExecuteMerge = async (selectedSuggestions: MergeSuggestion[]) => {
    setShowSuggestions(false)
    setIsMerging(true)

    try {
      await executeMerge(selectedSuggestions)
      toast.success(t('insights.merge.success', { count: selectedSuggestions.length }))
    } catch (error) {
      toast.error(t('insights.merge.error', { error: (error as Error).message }))
    } finally {
      setIsMerging(false)
    }
  }

  // Extract all unique keywords
  const availableKeywords = useMemo(() => {
    const keywords = new Set<string>()
    knowledge.forEach((k) => {
      k.keywords.forEach((kw) => keywords.add(kw))
    })
    return Array.from(keywords).sort()
  }, [knowledge])

  // Create knowledge map for suggestions dialog
  const knowledgeMap = useMemo(() => {
    const map = new Map()
    knowledge.forEach((k) => {
      map.set(k.id, { title: k.title, description: k.description })
    })
    return map
  }, [knowledge])

  // Filter knowledge based on active filter, category, and search
  const filteredKnowledge = useMemo(() => {
    let result = [...knowledge]

    // Apply filter (all/favorites/recent)
    if (activeFilter === 'favorites') {
      result = result.filter((item) => item.favorite)
    } else if (activeFilter === 'recent') {
      // Recent: last 7 days
      const sevenDaysAgo = new Date()
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
      result = result.filter((item) => {
        if (!item.createdAt) return false
        return new Date(item.createdAt) >= sevenDaysAgo
      })
    }

    // Apply category filter
    if (selectedCategory) {
      result = result.filter(
        (item) => item.keywords && item.keywords.length > 0 && item.keywords[0] === selectedCategory
      )
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (item) =>
          item.title.toLowerCase().includes(query) ||
          item.description.toLowerCase().includes(query) ||
          (item.keywords && item.keywords.some((k) => k.toLowerCase().includes(query)))
      )
    }

    return result
  }, [knowledge, activeFilter, selectedCategory, searchQuery])

  return (
    <PageLayout stickyHeader maxWidth="4xl">
      <PageHeader
        title={t('insights.knowledgeSummary')}
        description={t('insights.knowledgePageDescription')}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowMergeDialog(true)}
              disabled={knowledge.length < 2 || isAnalyzing || isMerging}>
              <Sparkles className="mr-2 h-4 w-4" />
              {isAnalyzing ? t('insights.merge.analyzing') : t('insights.smartMerge')}
            </Button>
            <Button size="sm" onClick={() => setNewNoteDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              {t('insights.newNote')}
            </Button>
          </div>
        }
      />

      <div className="flex h-full flex-1 gap-6 px-6 pb-6">
        {/* Left Sidebar - Categories */}
        <CategorySidebar
          knowledge={knowledge}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
        />

        {/* Main Content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Fixed Search and Filter Section */}
          <div className="shrink-0 space-y-4 pb-4">
            {/* Search Bar */}
            <div className="relative">
              <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
              <Input
                placeholder={t('insights.searchKnowledge')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Filter Tabs */}
            <KnowledgeFilterTabs activeFilter={activeFilter} onFilterChange={setActiveFilter} />
          </div>

          {/* Scrollable Knowledge Cards Grid */}
          {loading && knowledge.length === 0 ? (
            <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('insights.loading')}
            </div>
          ) : filteredKnowledge.length === 0 ? (
            <div className="flex flex-1 items-center justify-center text-center">
              <div className="space-y-2">
                <h3 className="text-foreground text-lg font-semibold">
                  {activeFilter === 'favorites'
                    ? t('insights.noFavoriteKnowledge')
                    : activeFilter === 'recent'
                      ? t('insights.noRecentKnowledge')
                      : t('insights.noKnowledge')}
                </h3>
                <p className="text-muted-foreground text-sm">
                  {searchQuery.trim() ? 'No results found for your search' : t('activity.noDataDescription')}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 space-y-4 overflow-x-hidden overflow-y-auto pr-2">
              {filteredKnowledge.map((item) => (
                <KnowledgeCard
                  key={item.id}
                  knowledge={item}
                  onToggleFavorite={handleToggleFavorite}
                  onDelete={handleDelete}
                  onView={handleViewKnowledge}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* New Note Dialog */}
      <NewNoteDialog open={newNoteDialogOpen} onOpenChange={setNewNoteDialogOpen} onCreateNote={handleCreateNote} />

      {/* Knowledge Detail Dialog */}
      <KnowledgeDetailDialog
        knowledge={selectedKnowledge}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        onUpdate={handleUpdateKnowledge}
      />

      {/* Knowledge Merge Dialogs */}
      <KnowledgeMergeDialog
        open={showMergeDialog}
        onOpenChange={setShowMergeDialog}
        onConfirm={handleStartAnalysis}
        availableKeywords={availableKeywords}
        knowledgeCount={knowledge.length}
      />

      <MergeSuggestionsDialog
        open={showSuggestions}
        onOpenChange={setShowSuggestions}
        suggestions={mergeSuggestions}
        knowledgeMap={knowledgeMap}
        onConfirm={handleExecuteMerge}
      />

      {/* Retry Dialog for LLM Errors */}
      <RetryDialog
        open={retryDialogOpen}
        onOpenChange={setRetryDialogOpen}
        title={t('knowledge.merge.llmErrorTitle')}
        message={retryError}
        onRetry={handleRetryAnalysis}
        retryLabel={t('knowledge.merge.retryAnalysis')}
        cancelLabel={t('common.cancel')}
      />
    </PageLayout>
  )
}

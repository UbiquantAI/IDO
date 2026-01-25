import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronUp } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

export interface MergeSuggestion {
  groupId: string
  knowledgeIds: string[]
  mergedTitle: string
  mergedDescription: string
  mergedKeywords: string[]
  similarityScore: number
  mergeReason: string
  estimatedTokens: number
}

interface MergeSuggestionsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  suggestions: MergeSuggestion[]
  knowledgeMap: Map<string, { title: string; description: string }>
  onConfirm: (selectedSuggestions: MergeSuggestion[]) => void
}

export function MergeSuggestionsDialog({
  open,
  onOpenChange,
  suggestions,
  knowledgeMap,
  onConfirm
}: MergeSuggestionsDialogProps) {
  const { t } = useTranslation()
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set(suggestions.map((s) => s.groupId)))

  const toggleGroup = (groupId: string) => {
    const newSelection = new Set(selectedGroups)
    if (newSelection.has(groupId)) {
      newSelection.delete(groupId)
    } else {
      newSelection.add(groupId)
    }
    setSelectedGroups(newSelection)
  }

  const selectAll = () => {
    setSelectedGroups(new Set(suggestions.map((s) => s.groupId)))
  }

  const deselectAll = () => {
    setSelectedGroups(new Set())
  }

  const handleConfirm = () => {
    const selected = suggestions.filter((s) => selectedGroups.has(s.groupId))
    onConfirm(selected)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-[800px]">
        <DialogHeader>
          <DialogTitle>{t('knowledge.merge.suggestionsTitle')}</DialogTitle>
          <DialogDescription>
            {t('knowledge.merge.suggestionsDescription', {
              count: suggestions.length
            })}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between py-2">
          <div className="text-muted-foreground text-sm">
            {t('knowledge.merge.selectedCount', {
              selected: selectedGroups.size,
              total: suggestions.length
            })}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={selectAll}>
              {t('common.selectAll')}
            </Button>
            <Button variant="ghost" size="sm" onClick={deselectAll}>
              {t('common.deselectAll')}
            </Button>
          </div>
        </div>

        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-3 pb-4">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.groupId}
                suggestion={suggestion}
                knowledgeMap={knowledgeMap}
                selected={selectedGroups.has(suggestion.groupId)}
                onToggle={() => toggleGroup(suggestion.groupId)}
              />
            ))}
          </div>
        </ScrollArea>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleConfirm} disabled={selectedGroups.size === 0}>
            {t('knowledge.merge.executeMerge', { count: selectedGroups.size })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SuggestionCard({
  suggestion,
  knowledgeMap,
  selected,
  onToggle
}: {
  suggestion: MergeSuggestion
  knowledgeMap: Map<string, { title: string; description: string }>
  selected: boolean
  onToggle: () => void
}) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`rounded-lg border p-4 transition-colors ${
        selected ? 'border-primary bg-primary/5' : 'border-border'
      }`}>
      <div className="flex items-start gap-3">
        <Checkbox checked={selected} onCheckedChange={onToggle} />

        <div className="flex-1 space-y-2">
          {/* Merged Result */}
          <div>
            <div className="font-medium">{suggestion.mergedTitle}</div>
            <div className="text-muted-foreground line-clamp-2 text-sm">{suggestion.mergedDescription}</div>
          </div>

          {/* Keywords */}
          <div className="flex flex-wrap gap-1">
            {suggestion.mergedKeywords.map((keyword) => (
              <Badge key={keyword} variant="secondary" className="text-xs">
                {keyword}
              </Badge>
            ))}
          </div>

          {/* Score & Reason */}
          <div className="text-muted-foreground flex items-center gap-4 text-xs">
            <span>
              {t('knowledge.merge.similarity')}: {(suggestion.similarityScore * 100).toFixed(0)}%
            </span>
            <span className="line-clamp-1">{suggestion.mergeReason}</span>
          </div>

          {/* Source Knowledge Items */}
          <Collapsible open={expanded} onOpenChange={setExpanded}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="h-6 gap-1 px-2">
                {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {t('knowledge.merge.viewSources', {
                  count: suggestion.knowledgeIds.length
                })}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              {suggestion.knowledgeIds.map((id) => {
                const k = knowledgeMap.get(id)
                if (!k) return null
                return (
                  <div key={id} className="rounded border border-dashed p-2 text-sm">
                    <div className="font-medium">{k.title}</div>
                    <div className="text-muted-foreground line-clamp-2">{k.description}</div>
                  </div>
                )
              })}
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>
    </div>
  )
}

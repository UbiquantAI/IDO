import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Tag, Sparkles } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface KnowledgeMergeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (config: MergeConfig) => void
  availableKeywords: string[]
  knowledgeCount: number
}

export interface MergeConfig {
  filterByKeyword: string | null
  includeFavorites: boolean
  similarityThreshold: number
}

export function KnowledgeMergeDialog({
  open,
  onOpenChange,
  onConfirm,
  availableKeywords,
  knowledgeCount
}: KnowledgeMergeDialogProps) {
  const { t } = useTranslation()
  const [config, setConfig] = useState<MergeConfig>({
    filterByKeyword: null,
    includeFavorites: true,
    similarityThreshold: 0.7
  })

  // Rough token estimation: ~100 tokens per knowledge entry analysis
  const estimatedTokens = Math.round(knowledgeCount * 100)
  const estimatedCost = ((estimatedTokens / 1000000) * 15).toFixed(4) // Assume $15/1M tokens

  const handleConfirm = () => {
    onConfirm(config)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="text-primary h-5 w-5" />
            {t('knowledge.merge.title')}
          </DialogTitle>
          <DialogDescription>{t('knowledge.merge.description')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Token Warning */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {t('knowledge.merge.tokenWarning', {
                count: knowledgeCount,
                tokens: estimatedTokens.toLocaleString(),
                cost: estimatedCost
              })}
            </AlertDescription>
          </Alert>

          {/* Filter by Keyword */}
          <div className="space-y-2">
            <Label htmlFor="keyword-filter" className="flex items-center gap-2">
              <Tag className="h-4 w-4" />
              {t('knowledge.merge.filterByTag')}
            </Label>
            <Select
              value={config.filterByKeyword || 'all'}
              onValueChange={(value) =>
                setConfig({
                  ...config,
                  filterByKeyword: value === 'all' ? null : value
                })
              }>
              <SelectTrigger id="keyword-filter">
                <SelectValue placeholder={t('knowledge.merge.allTags')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('knowledge.merge.allTags')}</SelectItem>
                {availableKeywords.map((keyword) => (
                  <SelectItem key={keyword} value={keyword}>
                    {keyword}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-muted-foreground text-sm">{t('knowledge.merge.filterByTagHint')}</p>
          </div>

          {/* Include Favorites */}
          <div className="flex items-center justify-between">
            <Label htmlFor="include-favorites" className="cursor-pointer">
              {t('knowledge.merge.includeFavorites')}
            </Label>
            <Switch
              id="include-favorites"
              checked={config.includeFavorites}
              onCheckedChange={(checked) => setConfig({ ...config, includeFavorites: checked })}
            />
          </div>

          {/* Similarity Threshold */}
          <div className="space-y-2">
            <Label>
              {t('knowledge.merge.similarityThreshold')}: {config.similarityThreshold}
            </Label>
            <Slider
              value={[config.similarityThreshold]}
              onValueChange={([value]) => setConfig({ ...config, similarityThreshold: value })}
              min={0.5}
              max={0.95}
              step={0.05}
              className="w-full"
            />
            <p className="text-muted-foreground text-sm">{t('knowledge.merge.thresholdHint')}</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleConfirm}>{t('knowledge.merge.startAnalysis')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

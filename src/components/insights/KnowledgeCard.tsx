import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Star, Trash2, Eye } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { InsightKnowledge } from '@/lib/services/insights'

interface KnowledgeCardProps {
  knowledge: InsightKnowledge
  onToggleFavorite: (id: string) => void
  onDelete: (id: string) => void
  onView: (knowledge: InsightKnowledge) => void
  isAnalyzing?: boolean
}

export function KnowledgeCard({
  knowledge,
  onToggleFavorite,
  onDelete,
  onView,
  isAnalyzing = false
}: KnowledgeCardProps) {
  const { t } = useTranslation()

  // Get category from first keyword
  const category = knowledge.keywords && knowledge.keywords.length > 0 ? knowledge.keywords[0] : ''

  // Format date
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString()
  }

  return (
    <Card
      className="group card-hover relative cursor-pointer shadow-sm transition-shadow hover:shadow-md"
      onClick={() => onView(knowledge)}
      role="button"
      tabIndex={0}>
      <CardHeader className="pb-3">
        <div className="mb-1 flex items-center gap-2">
          <CardTitle className="warp-break-words text-lg leading-tight">{knowledge.title}</CardTitle>
          {knowledge.favorite && <Star className="icon-bounce h-4 w-4 shrink-0 fill-yellow-400 text-yellow-400" />}
        </div>
        <div className="flex items-center justify-between gap-3">
          <CardDescription className="text-xs">
            {category && <span>{category} · </span>}
            <span>{formatDate(knowledge.createdAt)}</span>
          </CardDescription>

          <div
            className={`flex shrink-0 gap-1 ${isAnalyzing ? 'opacity-50' : 'opacity-0'} transition-opacity group-hover:opacity-100`}>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                onView(knowledge)
              }}
              className="h-8 w-8"
              title={t('insights.view')}
              disabled={isAnalyzing}>
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                onToggleFavorite(knowledge.id)
              }}
              className="h-8 w-8"
              title={knowledge.favorite ? t('insights.unfavorited') : t('insights.favorited')}
              disabled={isAnalyzing}>
              <Star className={`h-4 w-4 ${knowledge.favorite ? 'fill-yellow-400 text-yellow-400' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(knowledge.id)
              }}
              className="h-8 w-8"
              title={t('insights.delete')}
              disabled={isAnalyzing}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <p className="text-muted-foreground line-clamp-3 text-sm leading-6">{knowledge.description}</p>

        {knowledge.keywords && knowledge.keywords.length > 0 && (
          <div className="flex max-h-20 flex-wrap gap-2 overflow-x-hidden overflow-y-auto">
            {knowledge.keywords.map((keyword, index) => (
              <Badge key={`${knowledge.id}-${keyword}-${index}`} variant="secondary" className="text-xs">
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

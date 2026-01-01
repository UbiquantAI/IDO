import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Star, Trash2, FileText } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { InsightKnowledge } from '@/lib/services/insights'

interface KnowledgeCardProps {
  knowledge: InsightKnowledge
  onToggleFavorite: (id: string) => void
  onDelete: (id: string) => void
}

export function KnowledgeCard({ knowledge, onToggleFavorite, onDelete }: KnowledgeCardProps) {
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
    <Card className="group relative shadow-sm transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-center gap-2">
              <CardTitle className="truncate text-lg leading-tight">{knowledge.title}</CardTitle>
              {knowledge.favorite && <Star className="h-4 w-4 shrink-0 fill-yellow-400 text-yellow-400" />}
            </div>
            <CardDescription className="text-xs">
              {category && <span>{category} · </span>}
              <span>{formatDate(knowledge.createdAt)}</span>
            </CardDescription>
          </div>

          <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onToggleFavorite(knowledge.id)}
              className="h-8 w-8"
              title={knowledge.favorite ? t('insights.unfavorited') : t('insights.favorited')}>
              <Star className={`h-4 w-4 ${knowledge.favorite ? 'fill-yellow-400 text-yellow-400' : ''}`} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(knowledge.id)}
              className="h-8 w-8"
              title={t('insights.delete')}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>

          <div className="text-muted-foreground shrink-0">
            <FileText className="h-5 w-5" />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <p className="text-muted-foreground line-clamp-3 text-sm leading-6">{knowledge.description}</p>

        {knowledge.keywords && knowledge.keywords.length > 0 && (
          <div className="flex max-h-20 flex-wrap gap-2 overflow-y-auto">
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

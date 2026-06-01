import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Pencil } from 'lucide-react'
import { InsightKnowledge } from '@/lib/services/insights'

interface KnowledgeDetailDialogProps {
  knowledge: InsightKnowledge | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdate: (id: string, title: string, description: string, keywords: string[]) => Promise<void>
  isAnalyzing?: boolean
}

export function KnowledgeDetailDialog({
  knowledge,
  open,
  onOpenChange,
  onUpdate,
  isAnalyzing = false
}: KnowledgeDetailDialogProps) {
  const { t } = useTranslation()
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [keywordsInput, setKeywordsInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Initialize form when knowledge changes
  useEffect(() => {
    if (knowledge) {
      setTitle(knowledge.title)
      setDescription(knowledge.description)
      setKeywordsInput(knowledge.keywords.join(', '))
    } else {
      setTitle('')
      setDescription('')
      setKeywordsInput('')
    }
    setIsEditing(false)
  }, [knowledge])

  const handleSubmit = async () => {
    if (!knowledge || !title.trim() || !description.trim()) {
      return
    }

    setIsSubmitting(true)
    try {
      const keywords = keywordsInput
        .split(',')
        .map((k) => k.trim())
        .filter((k) => k.length > 0)

      await onUpdate(knowledge.id, title.trim(), description.trim(), keywords)

      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update knowledge:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    if (knowledge) {
      setTitle(knowledge.title)
      setDescription(knowledge.description)
      setKeywordsInput(knowledge.keywords.join(', '))
    }
    setIsEditing(false)
  }

  const handleClose = () => {
    setIsEditing(false)
    onOpenChange(false)
  }

  if (!knowledge) return null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>{isEditing ? t('insights.editKnowledge') : t('insights.knowledgeDetails')}</DialogTitle>
            {!isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(true)}
                className="gap-2"
                disabled={isAnalyzing}>
                <Pencil className="h-4 w-4" />
                {t('insights.edit')}
              </Button>
            )}
          </div>
          <DialogDescription>
            {isEditing
              ? t('insights.editKnowledgeDescription', 'Update the knowledge item details')
              : t('insights.viewKnowledgeDescription', 'View the complete knowledge item')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* View Mode */}
          {!isEditing && (
            <>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs">{t('insights.noteTitle')}</Label>
                <p className="text-base font-medium">{knowledge.title}</p>
              </div>

              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs">{t('insights.noteDescription')}</Label>
                <p className="text-muted-foreground text-sm leading-6 whitespace-pre-wrap">{knowledge.description}</p>
              </div>

              {knowledge.keywords.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs">{t('insights.noteKeywords')}</Label>
                  <div className="flex flex-wrap gap-2">
                    {knowledge.keywords.map((keyword, index) => (
                      <Badge key={index} variant="secondary">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {knowledge.createdAt && (
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs">{t('insights.createdAt')}</Label>
                  <p className="text-muted-foreground text-sm">{new Date(knowledge.createdAt).toLocaleString()}</p>
                </div>
              )}
            </>
          )}

          {/* Edit Mode */}
          {isEditing && (
            <>
              <div className="space-y-2">
                <Label htmlFor="edit-title">{t('insights.noteTitle')}</Label>
                <Input
                  id="edit-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t('insights.enterTitle')}
                  disabled={isAnalyzing}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-description">{t('insights.noteDescription')}</Label>
                <Textarea
                  id="edit-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t('insights.enterDescription')}
                  rows={8}
                  className="resize-none"
                  disabled={isAnalyzing}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-keywords">{t('insights.noteKeywords')}</Label>
                <Input
                  id="edit-keywords"
                  value={keywordsInput}
                  onChange={(e) => setKeywordsInput(e.target.value)}
                  placeholder={t('insights.enterKeywords')}
                  disabled={isAnalyzing}
                />
                <p className="text-muted-foreground text-xs">
                  {t('insights.keywordsHint', 'Separate keywords with commas')}
                </p>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          {isEditing ? (
            <>
              <Button variant="outline" onClick={handleCancel} disabled={isSubmitting || isAnalyzing}>
                {t('insights.cancel')}
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!title.trim() || !description.trim() || isSubmitting || isAnalyzing}>
                {isSubmitting ? t('insights.loading') : t('insights.save')}
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={handleClose} disabled={isAnalyzing}>
              {t('insights.close')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

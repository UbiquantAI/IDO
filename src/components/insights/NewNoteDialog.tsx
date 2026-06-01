import { useState } from 'react'
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

interface NewNoteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateNote: (title: string, description: string, keywords: string[]) => Promise<void>
  isAnalyzing?: boolean
}

export function NewNoteDialog({ open, onOpenChange, onCreateNote, isAnalyzing = false }: NewNoteDialogProps) {
  const { t } = useTranslation()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [keywordsInput, setKeywordsInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      return
    }

    setIsSubmitting(true)
    try {
      const keywords = keywordsInput
        .split(',')
        .map((k) => k.trim())
        .filter((k) => k.length > 0)

      await onCreateNote(title.trim(), description.trim(), keywords)

      // Reset form
      setTitle('')
      setDescription('')
      setKeywordsInput('')
      onOpenChange(false)
    } catch (error) {
      console.error('Failed to create note:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    setTitle('')
    setDescription('')
    setKeywordsInput('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{t('insights.createNote')}</DialogTitle>
          <DialogDescription>
            {t('insights.createNoteDescription', 'Add a new note to your knowledge base')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="title">{t('insights.noteTitle')}</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('insights.enterTitle')}
              autoFocus
              disabled={isAnalyzing}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t('insights.noteDescription')}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('insights.enterDescription')}
              rows={6}
              className="resize-none"
              disabled={isAnalyzing}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="keywords">{t('insights.noteKeywords')}</Label>
            <Input
              id="keywords"
              value={keywordsInput}
              onChange={(e) => setKeywordsInput(e.target.value)}
              placeholder={t('insights.enterKeywords')}
              disabled={isAnalyzing}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isSubmitting || isAnalyzing}>
            {t('insights.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={!title.trim() || !description.trim() || isSubmitting || isAnalyzing}>
            {isSubmitting ? t('insights.loading') : t('insights.createNote')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

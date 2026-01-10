import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { createTodo } from '@/lib/client/apiClient'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'

interface CreateTodoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function CreateTodoDialog({ open, onOpenChange, onSuccess }: CreateTodoDialogProps) {
  const { t } = useTranslation()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [keywords, setKeywords] = useState('')
  const [loading, setLoading] = useState(false)

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setTitle('')
      setDescription('')
      setKeywords('')
    }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim() || !description.trim()) {
      toast.error(t('insights.createTodoError', 'Please fill in all required fields'))
      return
    }

    try {
      setLoading(true)
      const response = await createTodo({
        title: title.trim(),
        description: description.trim(),
        keywords: keywords
          .split(',')
          .map((k) => k.trim())
          .filter(Boolean)
      })

      if (response && typeof response === 'object' && 'success' in response && response.success) {
        toast.success(t('insights.todoCreated', 'Todo created successfully'))
        onOpenChange(false)
        onSuccess?.()
      } else {
        toast.error(t('insights.createTodoError', 'Failed to create todo'))
      }
    } catch (error) {
      console.error('Failed to create todo:', error)
      toast.error(t('insights.createTodoError', 'Failed to create todo'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{t('insights.createTodo', 'Create Todo')}</DialogTitle>
            <DialogDescription>
              {t('insights.createTodoDescription', 'Manually create a new todo item')}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <label htmlFor="title" className="text-sm font-medium">
                {t('insights.createTodoTitle', 'Title')} <span className="text-destructive">*</span>
              </label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('insights.createTodoTitlePlaceholder', 'Enter todo title')}
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="description" className="text-sm font-medium">
                {t('insights.createTodoDesc', 'Description')} <span className="text-destructive">*</span>
              </label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('insights.createTodoDescPlaceholder', 'Enter todo description')}
                required
                disabled={loading}
                rows={4}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="keywords" className="text-sm font-medium">
                {t('insights.createTodoKeywords', 'Keywords')}
              </label>
              <Input
                id="keywords"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder={t('insights.createTodoKeywordsPlaceholder', 'Enter keywords separated by commas')}
                disabled={loading}
              />
              <p className="text-muted-foreground text-xs">
                {t('insights.createTodoKeywordsHelp', 'Separate multiple keywords with commas')}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? t('common.creating', 'Creating...') : t('common.create', 'Create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

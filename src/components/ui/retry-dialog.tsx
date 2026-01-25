import { useTranslation } from 'react-i18next'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface RetryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  message: string
  onRetry: () => void
  retryLabel?: string
  cancelLabel?: string
}

export function RetryDialog({
  open,
  onOpenChange,
  title,
  message,
  onRetry,
  retryLabel,
  cancelLabel
}: RetryDialogProps) {
  const { t } = useTranslation()

  const handleRetry = () => {
    onOpenChange(false)
    onRetry()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription className="text-left">{message}</DialogDescription>
        </DialogHeader>

        <DialogFooter className="flex gap-2 sm:justify-end">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {cancelLabel || t('common.cancel')}
          </Button>
          <Button onClick={handleRetry}>
            <RefreshCw className="mr-2 h-4 w-4" />
            {retryLabel || 'Retry'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

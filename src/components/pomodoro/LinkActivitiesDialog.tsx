import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Link as LinkIcon, Loader2 } from 'lucide-react'
import { findUnlinkedActivities, linkActivitiesToSession } from '@/lib/client/apiClient'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'

interface LinkActivitiesDialogProps {
  sessionId: string
  onLinked?: () => void
}

export function LinkActivitiesDialog({ sessionId, onLinked }: LinkActivitiesDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['unlinked-activities', sessionId],
    queryFn: () => findUnlinkedActivities({ sessionId }),
    enabled: open
  })

  const linkMutation = useMutation({
    mutationFn: () => linkActivitiesToSession({ sessionId, activityIds: selectedIds }),
    onSuccess: (result) => {
      toast.success(t('pomodoro.review.linkActivities.linkSuccess', { count: result.linkedCount }))
      setOpen(false)
      setSelectedIds([])
      onLinked?.()
    },
    onError: () => {
      toast.error(t('pomodoro.review.linkActivities.linkFailed'))
    }
  })

  const activities = data?.activities || []

  const toggleActivity = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const toggleAll = () => {
    setSelectedIds(selectedIds.length === activities.length ? [] : activities.map((a) => a.id))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <LinkIcon className="mr-2 h-4 w-4" />
          {t('pomodoro.review.linkActivities.linkButton')}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('pomodoro.review.linkActivities.title')}</DialogTitle>
          <DialogDescription>{t('pomodoro.review.linkActivities.description')}</DialogDescription>
        </DialogHeader>

        <div className="max-h-96 space-y-2 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : activities.length === 0 ? (
            <div className="text-muted-foreground py-8 text-center">
              {t('pomodoro.review.linkActivities.noActivitiesFound')}
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 border-b pb-2">
                <Checkbox checked={selectedIds.length === activities.length} onCheckedChange={toggleAll} />
                <span className="text-sm font-medium">
                  {t('pomodoro.review.linkActivities.selectAll')} ({activities.length})
                </span>
              </div>

              {activities.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3 rounded-lg border p-3">
                  <Checkbox
                    checked={selectedIds.includes(activity.id)}
                    onCheckedChange={() => toggleActivity(activity.id)}
                  />
                  <div className="flex-1">
                    <div className="font-medium">{activity.title}</div>
                    <div className="text-muted-foreground text-sm">
                      {new Date(activity.startTime).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                      })}{' '}
                      -{' '}
                      {new Date(activity.endTime).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                      })}{' '}
                      ({activity.sessionDurationMinutes} {t('pomodoro.review.linkActivities.minutes')})
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {t('pomodoro.review.linkActivities.cancel')}
          </Button>
          <Button onClick={() => linkMutation.mutate()} disabled={selectedIds.length === 0 || linkMutation.isPending}>
            {linkMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('pomodoro.review.linkActivities.linkSelected', { count: selectedIds.length })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

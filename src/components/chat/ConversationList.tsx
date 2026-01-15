/**
 * Conversation list component
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/lib/types/chat'
import { MessageSquare, Plus, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

interface ConversationListProps {
  conversations: Conversation[]
  currentConversationId: string | null
  onSelect: (conversationId: string) => void
  onNew: () => void
  onDelete: (conversationId: string) => void
}

export function ConversationList({
  conversations,
  currentConversationId,
  onSelect,
  onNew,
  onDelete
}: ConversationListProps) {
  const { t } = useTranslation()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null)

  const handleDeleteClick = (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setConversationToDelete(conversationId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (conversationToDelete) {
      onDelete(conversationToDelete)
      setDeleteDialogOpen(false)
      setConversationToDelete(null)
    }
  }

  const formatDate = (conversation: Conversation) => {
    // Use updatedAt as the display time (last modified)
    const updatedAt = new Date(conversation.updatedAt)
    const now = new Date()

    // Determine if the timestamp is today
    const isSameDay =
      updatedAt.getFullYear() === now.getFullYear() &&
      updatedAt.getMonth() === now.getMonth() &&
      updatedAt.getDate() === now.getDate()

    if (isSameDay) {
      // For today, show only the time (24h)
      return new Intl.DateTimeFormat(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(updatedAt)
    }

    // For other days, show the date
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(updatedAt)
  }

  return (
    <div className="bg-card flex h-full flex-col overflow-hidden rounded-lg border">
      {/* Header */}
      <div className="p-6 pb-3">
        <Button onClick={onNew} className="w-full justify-start gap-2" size="default">
          <Plus className="h-4 w-4" />
          {t('chat.newConversation')}
        </Button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center px-4">
            <MessageSquare className="mb-3 h-12 w-12 opacity-20" />
            <p className="text-center text-sm">{t('chat.noConversations')}</p>
          </div>
        ) : (
          <div className="space-y-1 p-3">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  'group hover:bg-accent relative flex cursor-pointer items-center gap-3 rounded-md p-3 transition-colors',
                  currentConversationId === conversation.id && 'bg-accent'
                )}
                onClick={() => onSelect(conversation.id)}>
                <MessageSquare className="text-muted-foreground h-4 w-4 shrink-0" />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <p className="truncate text-sm leading-none font-medium">{conversation.title}</p>
                  <span className="text-muted-foreground text-xs">{formatDate(conversation)}</span>
                </div>
                {/* Delete button */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={(e) => handleDeleteClick(conversation.id, e)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chat.deleteConversation')}</DialogTitle>
            <DialogDescription>
              {t('chat.confirmDelete')} {t('chat.deleteWarning')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

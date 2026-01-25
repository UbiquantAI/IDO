/**
 * Message item component
 * Rendered with the shadcn/ui AI Response component
 */

import { useDeferredValue, useState } from 'react'
import { cn } from '@/lib/utils'
import type { Message } from '@/lib/types/chat'
import { Bot, User, RotateCw } from 'lucide-react'
import { Response } from '@/components/ui/ai-response'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

interface MessageItemProps {
  message: Message
  isStreaming?: boolean
  isThinking?: boolean
  onRetry?: (conversationId: string, messageId: string) => void
}

export function MessageItem({ message, isStreaming, isThinking, onRetry }: MessageItemProps) {
  const [isRetrying, setIsRetrying] = useState(false)
  const { t } = useTranslation()
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const hasError = !!message.error
  const deferredContent = useDeferredValue(message.content)
  const assistantContent = isStreaming ? deferredContent : message.content

  // Get error type from metadata
  const errorType = message.metadata?.error_type

  // Determine error title based on error type
  const errorTitle =
    errorType === 'network'
      ? t('chat.networkError', 'Network error')
      : errorType === 'llm'
        ? t('chat.llmServiceError', 'LLM service error')
        : t('chat.generationFailed', 'AI Generation Failed')

  if (isSystem) {
    return <div className="text-muted-foreground mx-4 my-2 rounded-lg px-4 py-2 text-sm">{message.content}</div>
  }

  return (
    <div
      className={cn(
        'max-w-full space-y-3 px-4 pb-8',
        isUser ? 'slide-in-right' : 'slide-in-left',
        isStreaming && 'animate-pulse'
      )}>
      {/* Avatar and username (horizontal layout) */}
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-md',
            isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
          )}>
          {isUser ? <User className="h-4.5 w-4.5" /> : <Bot className="h-4.5 w-4.5" />}
        </div>
        <p className="text-sm leading-none font-semibold">
          {isUser ? t('chat.you') : t('chat.aiAssistant')}
          {isThinking && <span className="text-muted-foreground ml-2 text-xs font-normal">{t('chat.thinking')}</span>}
          {isStreaming && !isThinking && (
            <span className="text-muted-foreground ml-2 text-xs font-normal">{t('chat.typing')}</span>
          )}
        </p>
      </div>

      {/* Content area */}
      <div className="space-y-3 overflow-hidden">
        {/* Thinking animation */}
        {isThinking && (
          <div className="flex h-8 items-center gap-1.5 py-2">
            <div className="bg-foreground/30 h-2.5 w-2.5 animate-bounce rounded-full [animation-delay:-0.3s]"></div>
            <div className="bg-foreground/30 h-2.5 w-2.5 animate-bounce rounded-full [animation-delay:-0.15s]"></div>
            <div className="bg-foreground/30 h-2.5 w-2.5 animate-bounce rounded-full"></div>
          </div>
        )}

        {/* Render images if present */}
        {message.images && message.images.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.images.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`Image ${index + 1}`}
                className="max-h-64 max-w-sm rounded-lg border object-contain"
              />
            ))}
          </div>
        )}

        {/* Render text content - hide for error messages (error details shown in error section) */}
        {message.content && !isThinking && !hasError && (
          <div className="text-foreground prose dark:prose-invert max-w-none text-sm select-text [&_.code-block-container]:m-0! [&_p:has(>.code-block-container)]:m-0! [&_p:has(>.code-block-container)]:p-0!">
            {isUser ? (
              // Keep user messages as-is
              <div className="warp-break-words whitespace-pre-wrap select-text">{message.content}</div>
            ) : (
              // Render AI messages via the shadcn Response component
              <>
                <Response className="select-text" parseIncompleteMarkdown={isStreaming}>
                  {assistantContent}
                </Response>
                {isStreaming && <span className="bg-primary ml-1 inline-block h-4 w-2 animate-pulse" />}
              </>
            )}
          </div>
        )}

        {/* Error message + retry button */}
        {hasError && onRetry && (
          <div className="border-destructive/50 bg-destructive/10 mt-3 rounded-lg border p-3">
            <div className="mb-2 flex items-start gap-2">
              <div className="text-destructive mt-0.5">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-destructive text-sm font-medium">{errorTitle}</p>
                <p className="text-muted-foreground mt-1 text-xs whitespace-pre-wrap">{message.error}</p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={async () => {
                setIsRetrying(true)
                try {
                  await onRetry(message.conversationId, message.id)
                } finally {
                  // Delay resetting state to avoid flicker on the retry button
                  setTimeout(() => setIsRetrying(false), 500)
                }
              }}
              disabled={isRetrying}
              className="hover:bg-primary/10 flex items-center gap-1.5">
              <RotateCw className={cn('h-3.5 w-3.5', isRetrying && 'animate-spin')} />
              {isRetrying ? t('chat.retrying') : t('chat.retry')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

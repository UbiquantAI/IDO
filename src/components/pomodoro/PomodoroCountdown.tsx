import { useEffect, useState } from 'react'

import { FlipDigit } from '@/components/pomodoro/FlipDigit'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

export function PomodoroCountdown() {
  const { session } = usePomodoroStore()
  const [colonVisible, setColonVisible] = useState(true)
  const [currentTime, setCurrentTime] = useState(Date.now())

  // Update current time every second for real-time calculation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Blinking colon effect
  useEffect(() => {
    const interval = setInterval(() => {
      setColonVisible((prev) => !prev)
    }, 500)

    return () => clearInterval(interval)
  }, [])

  if (!session) {
    return null
  }

  const formatTime = (totalSeconds: number): { digits: string[]; hasHours: boolean } => {
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.floor((totalSeconds % 3600) / 60)
    const seconds = totalSeconds % 60

    if (hours > 0) {
      return {
        digits: [
          ...hours.toString().padStart(2, '0').split(''),
          ...minutes.toString().padStart(2, '0').split(''),
          ...seconds.toString().padStart(2, '0').split('')
        ],
        hasHours: true
      }
    }
    return {
      digits: [...minutes.toString().padStart(2, '0').split(''), ...seconds.toString().padStart(2, '0').split('')],
      hasHours: false
    }
  }

  const currentPhase = (session.currentPhase || 'work') as 'work' | 'break' | 'completed'
  const isWorkPhase = currentPhase === 'work'
  const isCompleted = currentPhase === 'completed'

  // Calculate remaining seconds based on phase start time (works even when page is in background)
  const phaseDurationSeconds = isWorkPhase
    ? (session.workDurationMinutes || 25) * 60
    : (session.breakDurationMinutes || 5) * 60

  let remainingSeconds = 0
  if (!isCompleted && session) {
    // Use phaseStartTime for reliable calculation
    const phaseStartTime = session.phaseStartTime ? new Date(session.phaseStartTime).getTime() : null

    if (phaseStartTime) {
      // Calculate elapsed time since phase started
      const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)

      // Remaining time = phase duration - elapsed time
      remainingSeconds = Math.max(0, phaseDurationSeconds - elapsedSeconds)
    } else if (session.remainingPhaseSeconds != null) {
      // Fallback: use server's calculated value if phaseStartTime not available
      remainingSeconds = session.remainingPhaseSeconds
    } else {
      // Last resort: show full duration
      remainingSeconds = phaseDurationSeconds
    }
  }

  const timeData = isCompleted ? { digits: ['0', '0', '0', '0'], hasHours: false } : formatTime(remainingSeconds)

  return (
    <div className="flex items-center justify-center">
      {/* Main time display - Flip clock style */}
      <div className="flex items-center justify-center gap-1.5">
        {/* First pair of digits (minutes) */}
        <FlipDigit digit={timeData.digits[0]} phase={currentPhase} />
        <FlipDigit digit={timeData.digits[1]} phase={currentPhase} />

        {/* Colon separator */}
        <div
          className={cn(
            'flex h-28 w-6 flex-col items-center justify-center gap-4 px-1 transition-opacity',
            'text-foreground',
            colonVisible ? 'opacity-100' : 'opacity-30'
          )}>
          <div className="h-2.5 w-2.5 rounded-full bg-current" />
          <div className="h-2.5 w-2.5 rounded-full bg-current" />
        </div>

        {/* Second pair of digits (seconds) */}
        <FlipDigit digit={timeData.digits[2]} phase={currentPhase} />
        <FlipDigit digit={timeData.digits[3]} phase={currentPhase} />
      </div>
    </div>
  )
}

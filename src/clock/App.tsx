/**
 * Clock window app - Desktop countdown timer
 */

import { useEffect, useState } from 'react'
import { listen } from '@tauri-apps/api/event'
import './App.css'

interface ClockState {
  sessionId: string | null
  phase: 'work' | 'break' | 'completed' | null
  remainingSeconds: number
  totalSeconds: number
  currentRound: number
  totalRounds: number
  completedRounds: number
  userIntent: string
  phaseStartTime: string | null
  workDurationMinutes: number
  breakDurationMinutes: number
}

function App() {
  const [state, setState] = useState<ClockState>({
    sessionId: null,
    phase: null,
    remainingSeconds: 0,
    totalSeconds: 0,
    currentRound: 1,
    totalRounds: 4,
    completedRounds: 0,
    userIntent: '',
    phaseStartTime: null,
    workDurationMinutes: 25,
    breakDurationMinutes: 5
  })

  const [displayTime, setDisplayTime] = useState({
    minutes: 0,
    seconds: 0
  })

  const [currentClockTime, setCurrentClockTime] = useState({
    hours: 0,
    minutes: 0
  })

  const [currentTime, setCurrentTime] = useState(Date.now())

  useEffect(() => {
    const unlisten = listen<ClockState>('clock-update', (event) => {
      console.log('[Clock App] State update:', event.payload)
      const newState = event.payload

      // Update state (displayTime will be calculated from phaseStartTime)
      setState(newState)
    })

    return () => {
      unlisten.then((fn) => fn())
    }
  }, [])

  // Show current time when no Pomodoro session is active
  useEffect(() => {
    if (!state.sessionId || !state.phase) {
      const updateClock = () => {
        const now = new Date()
        setCurrentClockTime({
          hours: now.getHours(),
          minutes: now.getMinutes()
        })
      }

      updateClock()
      const interval = setInterval(updateClock, 1000)
      return () => clearInterval(interval)
    }
  }, [state.sessionId, state.phase])

  // Update current time every second for real-time calculation (like main app)
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Calculate display time based on phaseStartTime (same as main app)
  useEffect(() => {
    if (state.phase === 'completed' || !state.phaseStartTime || !state.phase) {
      return
    }

    const phaseStartTime = new Date(state.phaseStartTime).getTime()
    const phaseDuration = state.phase === 'work' ? state.workDurationMinutes * 60 : state.breakDurationMinutes * 60

    const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)
    const remainingSeconds = Math.max(0, phaseDuration - elapsedSeconds)

    setDisplayTime({
      minutes: Math.floor(remainingSeconds / 60),
      seconds: remainingSeconds % 60
    })
  }, [currentTime, state.phaseStartTime, state.phase, state.workDurationMinutes, state.breakDurationMinutes])

  const getPhaseColor = () => {
    switch (state.phase) {
      case 'work':
        return '#ef4444' // red
      case 'break':
        return '#22c55e' // green
      case 'completed':
        return '#3b82f6' // blue
      default:
        return '#6b7280' // gray
    }
  }

  const getPhaseLabel = () => {
    if (!state.phase) {
      return 'CLOCK'
    }
    switch (state.phase) {
      case 'work':
        return 'WORK'
      case 'break':
        return 'BREAK'
      case 'completed':
        return 'DONE'
      default:
        return ''
    }
  }

  // Calculate progress based on phaseStartTime (same as main app)
  const progress = (() => {
    if (!state.phaseStartTime || !state.phase || state.phase === 'completed') {
      return 0
    }

    const phaseStartTime = new Date(state.phaseStartTime).getTime()
    const phaseDuration = state.phase === 'work' ? state.workDurationMinutes * 60 : state.breakDurationMinutes * 60

    const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)
    return Math.min(100, (elapsedSeconds / phaseDuration) * 100)
  })()

  const circumference = 2 * Math.PI * 90
  const strokeDashoffset = circumference - (progress / 100) * circumference

  return (
    <div className="clock-container" data-tauri-drag-region>
      <svg className="progress-ring" width="200" height="200">
        <circle
          className="progress-ring-circle"
          stroke="#1f2937"
          strokeWidth="8"
          fill="transparent"
          r="90"
          cx="100"
          cy="100"
        />
        <circle
          className="progress-ring-progress"
          stroke={getPhaseColor()}
          strokeWidth="8"
          fill="transparent"
          r="90"
          cx="100"
          cy="100"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset,
            transition: 'stroke-dashoffset 0.5s ease-in-out'
          }}
        />
      </svg>

      <div className="clock-content">
        <div className="phase-label" style={{ color: getPhaseColor() }}>
          {getPhaseLabel()}
        </div>

        <div className="time-display">
          {state.phase
            ? `${String(displayTime.minutes).padStart(2, '0')}:${String(displayTime.seconds).padStart(2, '0')}`
            : `${String(currentClockTime.hours).padStart(2, '0')}:${String(currentClockTime.minutes).padStart(2, '0')}`}
        </div>

        {state.phase && (
          <div className="round-info">
            Round {state.currentRound}/{state.totalRounds}
          </div>
        )}

        {state.userIntent && <div className="user-intent">{state.userIntent}</div>}
      </div>
    </div>
  )
}

export default App

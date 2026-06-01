/**
 * Hook for handling notification sound reminders during Pomodoro phase transitions
 */

import { useEffect } from 'react'
import { useSettingsStore } from '@/lib/stores/settings'
import { audioService, type SoundId } from '@/lib/audio'
import { usePomodoroPhaseSwitched } from './usePomodoroEvents'

/**
 * Map Pomodoro phase to sound ID
 */
function getSoundForPhase(newPhase: string): SoundId | null {
  switch (newPhase) {
    case 'break':
      return 'work-complete' // Work phase just completed
    case 'work':
      return 'break-complete' // Break phase just completed
    case 'completed':
      return 'session-complete' // All rounds completed
    default:
      return null
  }
}

/**
 * Hook that automatically plays notification sounds on phase transitions
 */
export function usePomodoroAudio() {
  const { settings } = useSettingsStore()
  const voiceSettings = settings.voice

  useEffect(() => {
    if (!voiceSettings?.enabled) {
      return
    }

    // Preload sounds on mount for instant playback
    audioService.preloadSounds()

    console.log('[usePomodoroAudio] Notification sounds enabled:', {
      enabled: voiceSettings.enabled,
      volume: voiceSettings.volume,
      soundTheme: voiceSettings.soundTheme
    })
  }, [voiceSettings?.enabled, voiceSettings?.soundTheme])

  useEffect(() => {
    if (voiceSettings?.enabled && voiceSettings.volume !== undefined) {
      audioService.setVolume(voiceSettings.volume)
    }
  }, [voiceSettings?.volume, voiceSettings?.enabled])

  usePomodoroPhaseSwitched((payload) => {
    if (!voiceSettings?.enabled) {
      return
    }

    const soundId = getSoundForPhase(payload.new_phase)
    if (!soundId) {
      return
    }

    console.log('[usePomodoroAudio] Playing phase transition sound:', {
      newPhase: payload.new_phase,
      soundId,
      volume: voiceSettings.volume
    })

    audioService.playSound(soundId, voiceSettings.volume).catch((error) => {
      console.error('[usePomodoroAudio] Failed to play sound:', error)
    })
  })
}

export default usePomodoroAudio

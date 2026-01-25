/**
 * Audio Service for playing notification sounds
 * Uses HTML5 Audio API to play sound files for Pomodoro phase transitions
 */

import workCompleteSound from '@/assets/sounds/work-complete.wav'
import breakCompleteSound from '@/assets/sounds/break-complete.wav'
import sessionCompleteSound from '@/assets/sounds/session-complete.wav'

export type SoundId = 'work-complete' | 'break-complete' | 'session-complete'
export type SoundTheme = '8bit' | '16bit' | 'custom'

interface SoundRegistry {
  [key: string]: {
    url: string
    audio: HTMLAudioElement | null
  }
}

/**
 * Singleton service for managing notification sounds
 */
class AudioService {
  private soundRegistry: SoundRegistry = {}
  private currentlyPlaying: HTMLAudioElement | null = null
  private globalVolume = 0.8

  constructor() {
    this.initializeSounds()
  }

  /**
   * Initialize sound registry with default sounds
   */
  private initializeSounds() {
    this.soundRegistry = {
      'work-complete': {
        url: workCompleteSound,
        audio: null
      },
      'break-complete': {
        url: breakCompleteSound,
        audio: null
      },
      'session-complete': {
        url: sessionCompleteSound,
        audio: null
      }
    }
  }

  /**
   * Preload all sound files for instant playback
   */
  preloadSounds() {
    Object.entries(this.soundRegistry).forEach(([id, sound]) => {
      if (!sound.audio) {
        const audio = new Audio(sound.url)
        audio.preload = 'auto'
        audio.volume = this.globalVolume
        this.soundRegistry[id].audio = audio
      }
    })
  }

  /**
   * Play a notification sound
   * @param soundId - The ID of the sound to play
   * @param volume - Optional volume override (0-1), defaults to global volume
   */
  async playSound(soundId: SoundId, volume?: number): Promise<void> {
    const sound = this.soundRegistry[soundId]
    if (!sound) {
      console.warn(`Sound "${soundId}" not found in registry`)
      return
    }

    // Stop currently playing sound
    this.stop()

    // Create new audio instance if not preloaded
    if (!sound.audio) {
      sound.audio = new Audio(sound.url)
    }

    const audio = sound.audio
    audio.volume = volume !== undefined ? volume : this.globalVolume
    audio.currentTime = 0 // Reset to beginning

    this.currentlyPlaying = audio

    try {
      await audio.play()
    } catch (error) {
      console.error(`Failed to play sound "${soundId}":`, error)
    }

    // Clean up reference when playback ends
    audio.onended = () => {
      if (this.currentlyPlaying === audio) {
        this.currentlyPlaying = null
      }
    }
  }

  /**
   * Stop currently playing sound
   */
  stop() {
    if (this.currentlyPlaying) {
      this.currentlyPlaying.pause()
      this.currentlyPlaying.currentTime = 0
      this.currentlyPlaying = null
    }
  }

  /**
   * Set global volume for all sounds
   * @param volume - Volume level (0-1)
   */
  setVolume(volume: number) {
    this.globalVolume = Math.max(0, Math.min(1, volume))

    // Update volume for all preloaded sounds
    Object.values(this.soundRegistry).forEach((sound) => {
      if (sound.audio) {
        sound.audio.volume = this.globalVolume
      }
    })
  }

  /**
   * Get current global volume
   */
  getVolume(): number {
    return this.globalVolume
  }

  /**
   * Check if a sound is currently playing
   */
  isPlaying(): boolean {
    return this.currentlyPlaying !== null && !this.currentlyPlaying.paused
  }

  /**
   * Register a custom sound (for future extensibility)
   * @param soundId - Unique identifier for the sound
   * @param url - URL or path to the sound file
   */
  registerCustomSound(soundId: string, url: string) {
    this.soundRegistry[soundId] = {
      url,
      audio: null
    }
  }

  /**
   * Remove a custom sound from registry
   * @param soundId - ID of the sound to remove
   */
  unregisterCustomSound(soundId: string) {
    if (this.soundRegistry[soundId]?.audio) {
      this.soundRegistry[soundId].audio = null
    }
    delete this.soundRegistry[soundId]
  }
}

// Export singleton instance
export const audioService = new AudioService()
export { AudioService }

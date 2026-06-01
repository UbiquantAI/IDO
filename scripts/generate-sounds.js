#!/usr/bin/env node

/**
 * Generate 8-bit/16-bit style notification sounds for Pomodoro phase transitions
 * Creates simple WAV files with retro chiptune aesthetic
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// WAV file header structure
function createWavHeader(dataLength, sampleRate, numChannels, bitsPerSample) {
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8
  const blockAlign = (numChannels * bitsPerSample) / 8
  const buffer = Buffer.alloc(44)

  // "RIFF" chunk descriptor
  buffer.write('RIFF', 0)
  buffer.writeUInt32LE(36 + dataLength, 4) // File size - 8
  buffer.write('WAVE', 8)

  // "fmt " sub-chunk
  buffer.write('fmt ', 12)
  buffer.writeUInt32LE(16, 16) // Subchunk1Size (16 for PCM)
  buffer.writeUInt16LE(1, 20) // AudioFormat (1 for PCM)
  buffer.writeUInt16LE(numChannels, 22)
  buffer.writeUInt32LE(sampleRate, 24)
  buffer.writeUInt32LE(byteRate, 28)
  buffer.writeUInt16LE(blockAlign, 32)
  buffer.writeUInt16LE(bitsPerSample, 34)

  // "data" sub-chunk
  buffer.write('data', 36)
  buffer.writeUInt32LE(dataLength, 40)

  return buffer
}

// Generate 8-bit square wave (retro game sound)
function generate8BitChime(frequency, duration, sampleRate = 22050) {
  const numSamples = Math.floor(duration * sampleRate)
  const samples = Buffer.alloc(numSamples)

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    // Square wave with envelope
    const envelope = Math.exp(-t * 3) // Fast decay
    const wave = Math.sin(2 * Math.PI * frequency * t) > 0 ? 1 : -1
    const sample = wave * envelope * 127
    samples.writeInt8(Math.floor(sample), i)
  }

  return samples
}

// Generate 16-bit bell-like sound
function generate16BitBell(frequency, duration, sampleRate = 44100) {
  const numSamples = Math.floor(duration * sampleRate)
  const samples = Buffer.alloc(numSamples * 2) // 16-bit = 2 bytes per sample

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    // Harmonic bell sound with overtones
    const envelope = Math.exp(-t * 4)
    const fundamental = Math.sin(2 * Math.PI * frequency * t)
    const harmonic1 = 0.5 * Math.sin(2 * Math.PI * frequency * 2 * t)
    const harmonic2 = 0.25 * Math.sin(2 * Math.PI * frequency * 3 * t)
    const wave = fundamental + harmonic1 + harmonic2
    const sample = wave * envelope * 16384 // 16-bit range
    samples.writeInt16LE(Math.floor(sample), i * 2)
  }

  return samples
}

// Generate ascending 8-bit arpeggio (victory/completion sound)
function generate8BitMelody(sampleRate = 22050) {
  const duration = 1.2
  const numSamples = Math.floor(duration * sampleRate)
  const samples = Buffer.alloc(numSamples)

  // Arpeggio notes: C5, E5, G5, C6 (major chord)
  const notes = [523.25, 659.25, 783.99, 1046.5]
  const noteDuration = duration / notes.length

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    const noteIndex = Math.floor(t / noteDuration)
    const frequency = notes[Math.min(noteIndex, notes.length - 1)]
    const noteTime = t - noteIndex * noteDuration

    // Square wave with note-specific envelope
    const envelope = Math.exp(-noteTime * 5)
    const wave = Math.sin(2 * Math.PI * frequency * noteTime) > 0 ? 1 : -1
    const sample = wave * envelope * 127
    samples.writeInt8(Math.floor(sample), i)
  }

  return samples
}

// Write WAV file
function writeWavFile(filename, samples, sampleRate, bitsPerSample) {
  const header = createWavHeader(samples.length, sampleRate, 1, bitsPerSample)
  const wavData = Buffer.concat([header, samples])
  fs.writeFileSync(filename, wavData)
  console.log(`✓ Generated ${filename} (${Math.round(wavData.length / 1024)}KB)`)
}

// Generate 16-bit bell with two notes (ding-dong pattern)
function generate16BitDingDong(freq1, freq2, sampleRate = 44100) {
  const noteDuration = 0.35 // Each note duration
  const totalDuration = noteDuration * 2 + 0.1 // Two notes with gap
  const numSamples = Math.floor(totalDuration * sampleRate)
  const samples = Buffer.alloc(numSamples * 2) // 16-bit = 2 bytes per sample

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    let wave = 0

    // First note (ding)
    if (t < noteDuration) {
      const envelope = Math.exp(-t * 4.5)
      const fundamental = Math.sin(2 * Math.PI * freq1 * t)
      const harmonic1 = 0.5 * Math.sin(2 * Math.PI * freq1 * 2 * t)
      const harmonic2 = 0.25 * Math.sin(2 * Math.PI * freq1 * 3 * t)
      wave = (fundamental + harmonic1 + harmonic2) * envelope
    }
    // Second note (dong)
    else if (t >= noteDuration + 0.05 && t < totalDuration) {
      const t2 = t - (noteDuration + 0.05)
      const envelope = Math.exp(-t2 * 4)
      const fundamental = Math.sin(2 * Math.PI * freq2 * t2)
      const harmonic1 = 0.5 * Math.sin(2 * Math.PI * freq2 * 2 * t2)
      const harmonic2 = 0.25 * Math.sin(2 * Math.PI * freq2 * 3 * t2)
      wave = (fundamental + harmonic1 + harmonic2) * envelope
    }

    const sample = wave * 16384 // 16-bit range
    samples.writeInt16LE(Math.floor(sample), i * 2)
  }

  return samples
}

// Generate 16-bit bell with ascending arpeggio (C-E-G chord)
function generate16BitArpeggio(sampleRate = 44100) {
  const notes = [523.25, 659.25, 783.99] // C5, E5, G5 (major chord)
  const noteDuration = 0.3
  const totalDuration = noteDuration * notes.length + 0.2
  const numSamples = Math.floor(totalDuration * sampleRate)
  const samples = Buffer.alloc(numSamples * 2) // 16-bit

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    const noteIndex = Math.floor(t / noteDuration)
    const frequency = notes[Math.min(noteIndex, notes.length - 1)]
    const noteTime = t - noteIndex * noteDuration

    // Only play during note duration, not in gaps
    let wave = 0
    if (noteIndex < notes.length && noteTime < noteDuration - 0.05) {
      const envelope = Math.exp(-noteTime * 5)
      const fundamental = Math.sin(2 * Math.PI * frequency * noteTime)
      const harmonic1 = 0.5 * Math.sin(2 * Math.PI * frequency * 2 * noteTime)
      const harmonic2 = 0.25 * Math.sin(2 * Math.PI * frequency * 3 * noteTime)
      wave = (fundamental + harmonic1 + harmonic2) * envelope
    }

    const sample = wave * 16384 // 16-bit range
    samples.writeInt16LE(Math.floor(sample), i * 2)
  }

  return samples
}

// Main execution
const outputDir = path.join(__dirname, '../src/assets/sounds')

console.log('Generating notification sounds based on 16-bit bell tone...\n')

// 1. Work phase complete - 16-bit ding-dong (E5 -> C5, cheerful descending)
const workComplete = generate16BitDingDong(659.25, 523.25, 44100) // E5 -> C5
writeWavFile(path.join(outputDir, 'work-complete.wav'), workComplete, 44100, 16)

// 2. Break phase complete - 16-bit single bell (C5, gentle, calming)
const breakComplete = generate16BitBell(523.25, 0.8, 44100) // C5 note
writeWavFile(path.join(outputDir, 'break-complete.wav'), breakComplete, 44100, 16)

// 3. Session complete - 16-bit ascending arpeggio (C5-E5-G5, celebratory)
const sessionComplete = generate16BitArpeggio(44100)
writeWavFile(path.join(outputDir, 'session-complete.wav'), sessionComplete, 44100, 16)

console.log('\n✅ All notification sounds generated successfully!')
console.log('Sound design:')
console.log('  - Work Complete: E5→C5 ding-dong (descending, satisfying completion)')
console.log('  - Break Complete: C5 single bell (gentle reminder)')
console.log('  - Session Complete: C5-E5-G5 arpeggio (ascending, celebratory)')

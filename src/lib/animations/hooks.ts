/**
 * Animation Hooks
 * Custom React hooks for common animation patterns
 * Pure JS/CSS implementations - no external animation library dependencies
 */

import { useEffect, useRef, useState } from 'react'

// ============================================================================
// REDUCED MOTION
// ============================================================================

/**
 * Check if user prefers reduced motion
 * Returns true if animations should be disabled for accessibility
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)

    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return prefersReducedMotion
}

// ============================================================================
// COUNTER ANIMATION
// ============================================================================

/**
 * Animate a number counter from 0 to target value
 * Uses requestAnimationFrame for smooth 60fps animation
 * @param target - The target number to count to
 * @param duration - Animation duration in milliseconds (default: 1000)
 * @param decimals - Number of decimal places (default: 0)
 * @returns The current animated count value
 */
export function useCounterAnimation(target: number, duration: number = 1000, decimals: number = 0): number {
  const [count, setCount] = useState(0)
  const frameRef = useRef<number | undefined>(undefined)
  const startTimeRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    // Cancel previous animation if exists
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current)
    }

    startTimeRef.current = undefined

    const animate = (currentTime: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = currentTime
      }

      const elapsed = currentTime - startTimeRef.current
      const progress = Math.min(elapsed / duration, 1)

      // Ease out cubic function
      const easeOut = 1 - Math.pow(1 - progress, 3)
      const currentValue = target * easeOut

      setCount(decimals > 0 ? parseFloat(currentValue.toFixed(decimals)) : Math.floor(currentValue))

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate)
      }
    }

    frameRef.current = requestAnimationFrame(animate)

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [target, duration, decimals])

  return count
}

// ============================================================================
// SPRING VALUE
// ============================================================================

/**
 * Animate a value with spring physics
 * Uses requestAnimationFrame for smooth animation with spring-like motion
 * @param target - The target value to animate to
 * @param stiffness - Spring stiffness (default: 300, higher = faster)
 * @param damping - Spring damping (default: 30, higher = less bouncy)
 * @returns The current animated value
 */
export function useSpringValue(target: number, stiffness: number = 300, damping: number = 30): number {
  const [value, setValue] = useState(target)
  const frameRef = useRef<number | undefined>(undefined)
  const velocityRef = useRef(0)

  useEffect(() => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current)
    }

    const animate = () => {
      setValue((currentValue) => {
        const delta = target - currentValue
        const acceleration = delta * (stiffness / 1000)
        const dampingForce = velocityRef.current * (damping / 1000)
        velocityRef.current += acceleration - dampingForce
        const newValue = currentValue + velocityRef.current

        // Stop animation when close enough to target and velocity is low
        if (Math.abs(delta) < 0.01 && Math.abs(velocityRef.current) < 0.01) {
          velocityRef.current = 0
          return target
        }

        frameRef.current = requestAnimationFrame(animate)
        return newValue
      })
    }

    frameRef.current = requestAnimationFrame(animate)

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [target, stiffness, damping])

  return value
}

// ============================================================================
// SCROLL REVEAL
// ============================================================================

/**
 * Reveal element when it enters viewport
 * @param options - Intersection Observer options
 * @returns [ref, isInView] tuple
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>(
  options: IntersectionObserverInit = {}
): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null)
  const [isInView, setIsInView] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsInView(true)
        observer.disconnect() // Only trigger once
      }
    }, options)

    observer.observe(element)

    return () => {
      observer.disconnect()
    }
  }, [options])

  return [ref, isInView]
}

// ============================================================================
// HOVER DETECTION
// ============================================================================

/**
 * Detect hover state for manual animation control
 * @returns [ref, isHovered] tuple
 */
export function useHover<T extends HTMLElement = HTMLDivElement>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null)
  const [isHovered, setIsHovered] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const handleMouseEnter = () => setIsHovered(true)
    const handleMouseLeave = () => setIsHovered(false)

    element.addEventListener('mouseenter', handleMouseEnter)
    element.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter)
      element.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  return [ref, isHovered]
}

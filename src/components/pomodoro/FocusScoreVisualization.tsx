import { CircularProgress } from './CircularProgress'

interface FocusScoreVisualizationProps {
  score: number // 0-100 scale
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function FocusScoreVisualization({ score, size = 'md', showLabel = true }: FocusScoreVisualizationProps) {
  // Normalize score to 0-1 range if needed
  const normalizedScore = score > 1 ? score / 100 : score

  // Map score to color
  const getColor = (score: number): string => {
    if (score >= 0.8) return 'hsl(142, 71%, 45%)' // green-600
    if (score >= 0.6) return 'hsl(221, 83%, 53%)' // blue-600
    if (score >= 0.4) return 'hsl(45, 93%, 47%)' // yellow-500
    return 'hsl(0, 84%, 60%)' // red-500
  }

  // Map score to text color class
  const getTextColorClass = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400'
    if (score >= 0.6) return 'text-blue-600 dark:text-blue-400'
    if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  // Map score to level text
  const getLevelText = (score: number): string => {
    if (score >= 0.8) return 'Excellent'
    if (score >= 0.6) return 'Good'
    if (score >= 0.4) return 'Moderate'
    return 'Low'
  }

  // Map size to dimensions
  const getSizeConfig = (size: 'sm' | 'md' | 'lg'): { circleSize: number; strokeWidth: number; fontSize: string } => {
    switch (size) {
      case 'sm':
        return { circleSize: 80, strokeWidth: 8, fontSize: 'text-lg' }
      case 'md':
        return { circleSize: 120, strokeWidth: 10, fontSize: 'text-2xl' }
      case 'lg':
        return { circleSize: 160, strokeWidth: 12, fontSize: 'text-3xl' }
    }
  }

  const sizeConfig = getSizeConfig(size)
  const percentage = Math.round(normalizedScore * 100)
  const color = getColor(normalizedScore)
  const textColorClass = getTextColorClass(normalizedScore)
  const levelText = getLevelText(normalizedScore)

  return (
    <div className="flex flex-col items-center gap-2">
      <CircularProgress
        progress={percentage}
        size={sizeConfig.circleSize}
        strokeWidth={sizeConfig.strokeWidth}
        color={color}>
        <div className={`flex flex-col items-center ${textColorClass}`}>
          <span className={`font-bold ${sizeConfig.fontSize}`}>{percentage}%</span>
        </div>
      </CircularProgress>
      {showLabel && (
        <div className="text-center">
          <p className={`text-sm font-medium ${textColorClass}`}>{levelText}</p>
        </div>
      )}
    </div>
  )
}

export const parseModelSizeGB = (size: string): number => {
  if (!size) return 0
  const match = size.trim().match(/^([\d.]+)\s*([A-Za-z]+)$/)
  if (!match) return 0
  const value = parseFloat(match[1])
  const unit = match[2].toUpperCase()
  if (unit === 'GB') return value
  if (unit === 'MB') return value / 1024
  if (unit === 'TB') return value * 1024
  return value
}

export const canModelFit = (currentUsedGb: number, modelSizeGb: number, availableGb: number): { fits: boolean; reason?: string } => {
  if (availableGb <= 0) return { fits: true }
  const total = currentUsedGb + modelSizeGb
  if (total <= availableGb) return { fits: true }
  const over = Math.max(0, total - availableGb)
  return {
    fits: false,
    reason: `Requires ${total.toFixed(1)}GB total; over by ${over.toFixed(1)}GB (available ${availableGb.toFixed(1)}GB)`
  }
}


export function getChargeColor(charge, limit) {
  if (!Number.isFinite(charge) || !Number.isFinite(limit) || limit <= 0) {
    return 0xffffff
  }

  const ratio = Math.max(-1, Math.min(1, charge / limit))

  if (ratio > 0) {
    const red = Math.round(255 - (255 - 59) * ratio)
    const green = Math.round(255 - (255 - 130) * ratio)
    return rgbToHex(red, green, 255)
  }

  const absRatio = Math.abs(ratio)
  const green = Math.round(255 - (255 - 68) * absRatio)
  const blue = Math.round(255 - (255 - 68) * absRatio)
  return rgbToHex(255, green, blue)
}

export function getChargeCssColor(charge, limit) {
  return `#${getChargeColor(charge, limit).toString(16).padStart(6, '0')}`
}

function rgbToHex(red, green, blue) {
  return (red << 16) | (green << 8) | blue
}

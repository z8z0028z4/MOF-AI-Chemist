export function getViewerStyleSpec(mode, colorscheme) {
  if (mode === 'space-filling') {
    return {
      sphere: colorscheme ? { scale: 0.9, colorscheme } : { scale: 0.9 },
    }
  }

  if (mode === 'ball-stick') {
    return {
      stick: colorscheme ? { radius: 0.15, colorscheme } : { radius: 0.15 },
      sphere: colorscheme ? { scale: 0.28, colorscheme } : { scale: 0.28 },
    }
  }

  return {
    stick: colorscheme ? { radius: 0.2, colorscheme } : { radius: 0.2 },
  }
}

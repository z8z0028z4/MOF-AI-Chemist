import React, { useEffect, useRef, useState } from 'react'
import { Alert, Spin } from 'antd'
import { getChargeColor } from '../../utils/mof/chargeColor'
import { getViewerStyleSpec } from '../../utils/mof/viewerStyle'
import './CifChargeViewer.css'

const UNIT_CELL_STYLE = { box: { color: 0x475569, radius: 0.03 } }

const CifChargeViewer = ({
  cifText,
  charges = [],
  atomLabels = [],
  styleMode = 'stick',
  showSurface = true,
  surfaceType = 'VDW',
  surfaceOpacity = 0.5,
  height = 520,
}) => {
  const containerRef = useRef(null)
  const viewerRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function renderCif() {
      if (!containerRef.current || !cifText) {
        return
      }

      setLoading(true)
      setError('')

      try {
        const molModule = await import('3dmol')
        const threeDmol = molModule.default || molModule
        if (cancelled || !containerRef.current) {
          return
        }

        if (!viewerRef.current) {
          viewerRef.current = threeDmol.createViewer(containerRef.current, {
            backgroundColor: 'white',
          })
        }

        const viewer = viewerRef.current
        viewer.clear()
        viewer.removeAllSurfaces?.()

        const model = viewer.addModel(cifText, 'cif')
        viewer.addUnitCell(model, UNIT_CELL_STYLE)

        applyCharges(model, charges, atomLabels)
        viewer.setStyle({}, getViewerStyleSpec(styleMode, charges.length ? undefined : 'Jmol'))
        applyChargeSurface(viewer, threeDmol, model, charges, showSurface, surfaceType, surfaceOpacity)
        viewer.zoomTo()
        viewer.render()
      } catch (renderError) {
        if (!cancelled) {
          setError(renderError?.message || 'CIF structure could not be rendered.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    renderCif()

    return () => {
      cancelled = true
    }
  }, [atomLabels, charges, cifText, showSurface, styleMode, surfaceOpacity, surfaceType])

  useEffect(() => {
    if (!containerRef.current) {
      return undefined
    }

    const resizeObserver = new ResizeObserver(() => {
      viewerRef.current?.resize?.()
      viewerRef.current?.render?.()
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  return (
    <div className="mof-viewer-shell" style={{ height }}>
      {loading && (
        <div className="mof-viewer-loading">
          <Spin />
        </div>
      )}
      {error && (
        <Alert
          className="mof-viewer-error"
          type="error"
          message="CIF render failed"
          description={error}
          showIcon
        />
      )}
      <div ref={containerRef} className="mof-viewer-canvas" />
    </div>
  )
}

function applyCharges(model, charges, atomLabels) {
  if (!model?.atoms?.length || !charges.length) {
    return
  }

  const maxAbsCharge = charges.reduce((maxValue, charge) => {
    return Math.max(maxValue, Math.abs(charge))
  }, 0.0001)

  model.atoms.forEach((atom, index) => {
    const charge = charges[index]
    if (!Number.isFinite(charge)) {
      return
    }
    atom.partialCharge = charge
    atom.label = atomLabels[index] || atom.label || `${atom.elem}${index + 1}`
    atom.color = getChargeColor(charge, maxAbsCharge)
  })
}

function applyChargeSurface(viewer, threeDmol, model, charges, showSurface, surfaceType, surfaceOpacity) {
  if (!showSurface || !model?.atoms?.length || !charges.length) {
    return
  }

  const maxAbsCharge = charges.reduce((maxValue, charge) => {
    return Math.max(maxValue, Math.abs(charge))
  }, 0.0001)

  const surfaceEnum = threeDmol.SurfaceType?.[surfaceType] || threeDmol.SurfaceType?.VDW
  if (!surfaceEnum) {
    return
  }

  viewer.addSurface(surfaceEnum, {
    opacity: surfaceOpacity,
    colorfunc: (atom) => getChargeColor(atom.partialCharge || 0, maxAbsCharge),
  })
}

export default CifChargeViewer

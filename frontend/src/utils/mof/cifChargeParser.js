export function parseCifCharges(cifText) {
  if (typeof cifText !== 'string' || cifText.trim() === '') {
    return { charges: [], atomLabels: [], hasChargeColumn: false }
  }

  const lines = cifText.split(/\r?\n/)
  const charges = []
  const atomLabels = []
  let hasChargeColumn = false

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim()
    if (line !== 'loop_') {
      continue
    }

    const headers = []
    let cursor = index + 1
    while (cursor < lines.length) {
      const headerLine = lines[cursor].trim()
      if (!headerLine.startsWith('_')) {
        break
      }
      headers.push(headerLine)
      cursor += 1
    }

    const hasAtomSiteFields = headers.some((header) => header.startsWith('_atom_site_'))
    if (!hasAtomSiteFields) {
      continue
    }

    const chargeColumn = headers.findIndex((header) => header === '_atom_site_charge')
    const labelColumn = headers.findIndex((header) => header === '_atom_site_label')
    if (chargeColumn !== -1) {
      hasChargeColumn = true
    }

    while (cursor < lines.length) {
      const row = lines[cursor].trim()
      if (row === '' || row.startsWith('#')) {
        cursor += 1
        continue
      }
      if (row === 'loop_' || row.startsWith('data_') || row.startsWith('_')) {
        break
      }

      const tokens = tokenizeCifRow(row)
      if (tokens.length >= headers.length) {
        atomLabels.push(labelColumn >= 0 ? tokens[labelColumn] || '' : '')
        if (chargeColumn >= 0) {
          const charge = Number.parseFloat(tokens[chargeColumn])
          if (Number.isFinite(charge)) {
            charges.push(charge)
          }
        }
      }
      cursor += 1
    }

    index = cursor - 1
  }

  return { charges, atomLabels, hasChargeColumn }
}

export function summarizeCharges(charges, atomLabels = []) {
  if (!Array.isArray(charges) || charges.length === 0) {
    return {
      atomsCount: 0,
      maxAbsCharge: 0,
      minCharge: 0,
      maxCharge: 0,
      sumCharge: 0,
      sumAbsCharge: 0,
      maxPosLabel: '',
      maxNegLabel: '',
    }
  }

  return charges.reduce(
    (summary, charge, index) => {
      const label = atomLabels[index] || `Atom ${index + 1}`
      const next = {
        ...summary,
        atomsCount: summary.atomsCount + 1,
        sumCharge: summary.sumCharge + charge,
        sumAbsCharge: summary.sumAbsCharge + Math.abs(charge),
      }

      if (Math.abs(charge) > next.maxAbsCharge) {
        next.maxAbsCharge = Math.abs(charge)
      }
      if (charge > next.maxCharge) {
        next.maxCharge = charge
        next.maxPosLabel = label
      }
      if (charge < next.minCharge) {
        next.minCharge = charge
        next.maxNegLabel = label
      }
      return next
    },
    {
      atomsCount: 0,
      maxAbsCharge: 0,
      minCharge: 0,
      maxCharge: 0,
      sumCharge: 0,
      sumAbsCharge: 0,
      maxPosLabel: '',
      maxNegLabel: '',
    }
  )
}

function tokenizeCifRow(row) {
  const tokens = []
  const pattern = /'([^']*)'|"([^"]*)"|(\S+)/g
  let match = pattern.exec(row)
  while (match) {
    tokens.push(match[1] ?? match[2] ?? match[3])
    match = pattern.exec(row)
  }
  return tokens
}

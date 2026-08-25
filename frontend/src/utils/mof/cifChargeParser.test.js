import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { getChargeColor } from './chargeColor.js'
import { parseCifCharges, summarizeCharges } from './cifChargeParser.js'

describe('parseCifCharges', () => {
  it('detects atom-site charges and labels', () => {
    const cif = `
data_demo
loop_
  _atom_site_type_symbol
  _atom_site_label
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  _atom_site_charge
  C C1 0.1 0.2 0.3 -0.25
  Zn Zn1 0.4 0.5 0.6 0.75
`

    const parsed = parseCifCharges(cif)

    assert.equal(parsed.hasChargeColumn, true)
    assert.deepEqual(parsed.atomLabels, ['C1', 'Zn1'])
    assert.deepEqual(parsed.charges, [-0.25, 0.75])
  })

  it('returns empty charges when no charge column exists', () => {
    const cif = `
data_demo
loop_
  _atom_site_type_symbol
  _atom_site_label
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  O O1 0.1 0.2 0.3
`

    const parsed = parseCifCharges(cif)

    assert.equal(parsed.hasChargeColumn, false)
    assert.deepEqual(parsed.atomLabels, ['O1'])
    assert.deepEqual(parsed.charges, [])
  })

  it('handles quoted labels and ignores malformed partial rows', () => {
    const cif = `
data_demo
loop_
  _atom_site_type_symbol
  _atom_site_label
  _atom_site_charge
  C 'C alpha' -0.1
  broken-row
  H "H beta" 0.1
`

    const parsed = parseCifCharges(cif)

    assert.deepEqual(parsed.atomLabels, ['C alpha', 'H beta'])
    assert.deepEqual(parsed.charges, [-0.1, 0.1])
  })
})

describe('summarizeCharges', () => {
  it('summarizes net and extreme charges', () => {
    const summary = summarizeCharges([-0.4, 0.1, 0.6], ['O1', 'C1', 'Zn1'])

    assert.equal(summary.atomsCount, 3)
    assert.equal(summary.maxAbsCharge, 0.6)
    assert.equal(summary.minCharge, -0.4)
    assert.equal(summary.maxCharge, 0.6)
    assert.equal(summary.maxNegLabel, 'O1')
    assert.equal(summary.maxPosLabel, 'Zn1')
    assert.equal(Number(summary.sumCharge.toFixed(6)), 0.3)
  })
})

describe('getChargeColor', () => {
  it('maps negative, neutral, and positive charge colors', () => {
    assert.equal(getChargeColor(-1, 1), 0xff4444)
    assert.equal(getChargeColor(0, 1), 0xffffff)
    assert.equal(getChargeColor(1, 1), 0x3b82ff)
  })

  it('clamps out-of-range charge ratios', () => {
    assert.equal(getChargeColor(-10, 1), 0xff4444)
    assert.equal(getChargeColor(10, 1), 0x3b82ff)
  })
})

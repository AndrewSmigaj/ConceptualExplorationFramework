// What a cloud can be coloured by, and how.
//   group    a categorical field: one colour per value (identity slots or ordinal ramp)
//   scale    one numeric value on a diverging blue <-> red scale around a neutral centre
//   blend    two numeric values at once: a 3 x 3 bivariate key, one axis into cyan and
//            the other into magenta, both high where they meet
// Every option is built from the dataset's declarations; nothing here names a domain.

import type { Index } from './data'
import { median } from './data'
import { chrome, scheme } from './theme.svelte'
import type { Idea, Ref } from './types'

export interface ColorOption {
  id: string
  label: string
  ref: Ref
  /** The scorer a per-scorer field or a rubric dimension is read for. */
  scorer?: string
  numeric: boolean
}

/** Every field and scored dimension a cloud can be coloured by. */
export function colorOptions(idx: Index): ColorOption[] {
  const out: ColorOption[] = []
  const models = idx.ds.scorers.filter((s) =>
    idx.ds.ideas.some((i) => i.scorings?.[s.id]?.dims),
  )
  for (const f of idx.ds.fields) {
    if (f.kind === 'text') continue
    const numeric = f.kind === 'metric'
    if (f.kind === 'facet' && !f.values) continue
    if (f.per_scorer) {
      for (const s of idx.ds.scorers) {
        if (!idx.ds.ideas.some((i) => i.per_scorer?.[s.id]?.[f.id] !== undefined)) continue
        out.push({ id: `${f.id}@${s.id}`, label: `${f.label} · ${s.label}`, ref: { per_scorer: f.id }, scorer: s.id, numeric })
      }
    } else {
      const ref: Ref = numeric ? { metric: f.id } : { field: f.id }
      out.push({ id: f.id, label: f.label, ref, numeric })
    }
  }
  for (const s of models) {
    for (const d of idx.dims.values()) {
      out.push({ id: `dim:${d.id}@${s.id}`, label: `${d.label} · ${s.label}`, ref: { dim: d.id }, scorer: s.id, numeric: true })
    }
  }
  return out
}

// --- one value: diverging blue <-> red ---------------------------------------------
// The dataviz reference diverging pair (blue <-> red, neutral centre). Each arm, read
// from the centre outwards, passes the validator as an ordinal ramp in its mode, and
// every step (the grey centre too) clears 2:1 against the chart surface, so points
// near the centre stay visible.

const DIVERGING = {
  light: ['#184f95', '#3987e5', '#86b6ef', '#a9a8a1', '#ec9291', '#e34948', '#a8302f'],
  dark: ['#86b6ef', '#3987e5', '#1c5cab', '#5f5e59', '#a84645', '#e66767', '#f3b5b4'],
}

export interface ScaleRange {
  min: number
  max: number
  mid: number
}

/** A Plotly colour scale over [min, max] with the neutral grey placed at `mid`. Each arm
 * spans its own side, so the bar never shows values the data cannot take. */
export function divergingScale(range: ScaleRange, reverse = false): [number, string][] {
  const steps = DIVERGING[scheme.dark ? 'dark' : 'light']
  const ordered = reverse ? [...steps].reverse() : steps
  const span = range.max - range.min || 1
  const p = Math.min(0.95, Math.max(0.05, (range.mid - range.min) / span))
  const half = (ordered.length - 1) / 2
  return ordered.map((c, i) => [i <= half ? (i / half) * p : p + ((i - half) / half) * (1 - p), c])
}

/** The colour range: the declared range if there is one, else the data's; centred on
 * the median or on the middle of the range. */
export function scaleRange(values: number[], declared: [number, number] | undefined, centre: 'median' | 'middle'): ScaleRange {
  const lo = declared?.[0] ?? Math.min(...values)
  const hi = declared?.[1] ?? Math.max(...values)
  const mid = centre === 'median' ? (median(values) ?? (lo + hi) / 2) : (lo + hi) / 2
  return { min: lo, max: hi, mid }
}

// --- two values: 3 x 3 bivariate key -----------------------------------------------
// Rows: the first value low -> high (into cyan). Columns: the second (into magenta).
// Bilinear in OKLab between four corners: a visible neutral (both low), cyan, magenta,
// and deep indigo (both high). Every class clears 2:1 on its surface; neighbours sit
// at about 7.5 Delta E, so the key, hover values and table view carry the reading too.
// Classes are tertiles, so each band holds a third of the ideas.

const BIVARIATE = {
  light: [
    ['#a9a8a1', '#ba7c9f', '#c2459b'],
    ['#72a2a5', '#7e779e', '#804896'],
    ['#0e9aa7', '#346d9c', '#3b3f8f'],
  ],
  dark: [
    ['#5f5e59', '#a06784', '#e069b0'],
    ['#5f8f8f', '#958ab0', '#c17fd0'],
    ['#4cc3c9', '#7eabdd', '#9d8ff0'],
  ],
}

export function bivariateKey(): string[][] {
  return BIVARIATE[scheme.dark ? 'dark' : 'light']
}

export function bivariateColor(a: number, b: number): string {
  return bivariateKey()[a][b]
}

/** Tertile cut points, and the band (0, 1, 2) of a value. */
export function tertiles(values: number[]): { cuts: [number, number]; band: (v: number) => number } {
  const s = [...values].sort((x, y) => x - y)
  const at = (q: number) => s[Math.min(s.length - 1, Math.floor(q * s.length))]
  const cuts: [number, number] = [at(1 / 3), at(2 / 3)]
  return { cuts, band: (v) => (v < cuts[0] ? 0 : v < cuts[1] ? 1 : 2) }
}

export function numericValue(idx: Index, opt: ColorOption, idea: Idea): number | null {
  const v = idx.value(opt.ref, idea, opt.scorer)
  return typeof v === 'number' ? v : null
}

export function noValueColor(): string {
  return chrome().other
}

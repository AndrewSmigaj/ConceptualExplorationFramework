// Reading a dataset generically: labels, values by reference, filters, bins.
// Nothing here knows any domain; every name comes from the dataset's declarations.

import type { Dataset, Dimension, Edge, EdgeKind, Field, Idea, Ref, Scorer, Where } from './types'

export type Value = number | string | null

export class Index {
  readonly fields = new Map<string, Field>()
  readonly scorers = new Map<string, Scorer>()
  readonly dims = new Map<string, Dimension>()
  readonly generators = new Map<string, string>()
  readonly ideas = new Map<string, Idea>()
  readonly children = new Map<string, string[]>()
  readonly edgeKinds = new Map<string, EdgeKind>()
  private readonly edgesByIdea = new Map<string, Edge[]>()
  private readonly runLabels = new Map<string, string>()

  constructor(readonly ds: Dataset) {
    for (const f of ds.fields) this.fields.set(f.id, f)
    for (const s of ds.scorers) this.scorers.set(s.id, s)
    for (const d of ds.meta.rubric?.dimensions ?? []) this.dims.set(d.id, d)
    for (const g of ds.generators) this.generators.set(g.id, g.label)
    for (const i of ds.ideas) {
      this.ideas.set(i.id, i)
      for (const p of i.parents ?? []) this.children.set(p, [...(this.children.get(p) ?? []), i.id])
    }
    for (const k of ds.edge_kinds ?? []) this.edgeKinds.set(k.id, k)
    for (const e of ds.edges ?? []) {
      for (const end of [e.source, e.target]) {
        this.edgesByIdea.set(end, [...(this.edgesByIdea.get(end) ?? []), e])
      }
    }
    for (const r of ds.runs ?? []) {
      this.runLabels.set(r.id, r.label)
    }
  }

  /** Every edge touching an idea, with the idea at the other end. */
  edgesOf(id: string): { edge: Edge; other: string }[] {
    return (this.edgesByIdea.get(id) ?? []).map((edge) => ({
      edge,
      other: edge.source === id ? edge.target : edge.source,
    }))
  }

  runLabel(id: string | undefined): string | undefined {
    return id ? (this.runLabels.get(id) ?? id) : undefined
  }

  get headline(): Dimension | undefined {
    const all = [...this.dims.values()]
    return all.find((d) => d.headline) ?? all[0]
  }

  scorerLabel(id: string): string {
    return this.scorers.get(id)?.label ?? id
  }

  generatorLabel(id: string): string {
    return this.generators.get(id) ?? id
  }

  /** Every entity that has an identity colour: generators first, then human scorers. */
  get entities(): string[] {
    const humans = this.ds.scorers.filter((s) => s.kind === 'human').map((s) => s.id)
    return [...this.generators.keys(), ...humans]
  }

  /** The entity a scorer is: its generator if it shares one, else itself. */
  entityOfScorer(id: string): string {
    return this.scorers.get(id)?.generator ?? id
  }

  valueLabel(fieldId: string, value: Value): string {
    if (value === null || value === undefined) return '—'
    return this.fields.get(fieldId)?.values?.find((v) => v.id === value)?.label ?? String(value)
  }

  valueDescription(fieldId: string, value: Value): string | undefined {
    return this.fields.get(fieldId)?.values?.find((v) => v.id === value)?.description
  }

  refLabel(ref: Ref): string {
    if (ref.label) return ref.label
    if ('metric' in ref) return this.fields.get(ref.metric)?.label ?? ref.metric
    if ('field' in ref) return this.fields.get(ref.field)?.label ?? ref.field
    if ('per_scorer' in ref) return this.fields.get(ref.per_scorer)?.label ?? ref.per_scorer
    if ('dim' in ref) return this.dims.get(ref.dim)?.label ?? ref.dim
    return ref.dim_product.map((d) => this.dims.get(d)?.label ?? d).join(' × ')
  }

  refDescription(ref: Ref): string | undefined {
    if ('metric' in ref) return this.fields.get(ref.metric)?.description
    if ('field' in ref) return this.fields.get(ref.field)?.description
    if ('per_scorer' in ref) return this.fields.get(ref.per_scorer)?.description
    if ('dim' in ref) return this.dims.get(ref.dim)?.description
    return undefined
  }

  /** The value range a reference can take, when the dataset declares one. */
  refRange(ref: Ref): [number, number] | undefined {
    if ('dim' in ref) {
      const d = this.dims.get(ref.dim)
      return d ? [d.min, d.max] : undefined
    }
    if ('dim_product' in ref) {
      const [a, b] = ref.dim_product.map((id) => this.dims.get(id))
      if (!a || !b) return undefined
      const corners = [a.min * b.min, a.min * b.max, a.max * b.min, a.max * b.max]
      return [Math.min(...corners), Math.max(...corners)]
    }
    return undefined
  }

  /** The field a categorical reference reads, for labels and value order. */
  refField(ref: Ref): Field | undefined {
    if ('field' in ref) return this.fields.get(ref.field)
    if ('per_scorer' in ref) return this.fields.get(ref.per_scorer)
    return undefined
  }

  value(ref: Ref, idea: Idea, scorer?: string): Value {
    if ('metric' in ref) return idea.metrics?.[ref.metric] ?? null
    if ('field' in ref) return idea.facets?.[ref.field] ?? null
    if (scorer === undefined) return null
    if ('per_scorer' in ref) return idea.per_scorer?.[scorer]?.[ref.per_scorer] ?? null
    const dims = idea.scorings?.[scorer]?.dims
    if (!dims) return null
    if ('dim' in ref) return dims[ref.dim] ?? null
    const [a, b] = ref.dim_product.map((d) => dims[d])
    return a === undefined || b === undefined ? null : a * b
  }

  matches(where: Where | undefined, idea: Idea): boolean {
    if (!where) return true
    return Object.entries(where).every(([key, want]) => {
      if (key.startsWith('metric:')) {
        const v = idea.metrics?.[key.slice(7)]
        const [lo, hi] = want as [number, number]
        return typeof v === 'number' && v >= lo && v <= hi
      }
      const got = key === 'author' ? idea.author : idea.facets?.[key]
      const allowed = Array.isArray(want) ? want : [want]
      return got !== undefined && got !== null && allowed.includes(got)
    })
  }
}

export interface Bin {
  x: number
  y: number
  n: number
  /** Half-width of an approximate 95% interval on the mean of y. */
  ci: number
  xLow: number
  xHigh: number
}

/** Equal-count bins along x, each with the mean of y and a 95% interval. */
export function binnedMeans(points: { x: number; y: number }[], bins: number): Bin[] {
  const sorted = [...points].sort((a, b) => a.x - b.x)
  const k = Math.max(1, Math.min(bins, Math.floor(sorted.length / 3)))
  const out: Bin[] = []
  for (let b = 0; b < k; b++) {
    const chunk = sorted.slice(
      Math.round((b * sorted.length) / k),
      Math.round(((b + 1) * sorted.length) / k),
    )
    if (chunk.length === 0) continue
    const mean = (vs: number[]) => vs.reduce((s, v) => s + v, 0) / vs.length
    const ys = chunk.map((p) => p.y)
    const my = mean(ys)
    const sd =
      ys.length > 1 ? Math.sqrt(ys.reduce((s, v) => s + (v - my) ** 2, 0) / (ys.length - 1)) : 0
    out.push({
      x: mean(chunk.map((p) => p.x)),
      y: my,
      n: chunk.length,
      ci: (1.96 * sd) / Math.sqrt(ys.length),
      xLow: chunk[0].x,
      xHigh: chunk[chunk.length - 1].x,
    })
  }
  return out
}

/** A stable offset in [-1, 1] for an id, so jitter does not jump between renders. */
export function stableJitter(id: string): number {
  let h = 2166136261
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) / 4294967295) * 2 - 1
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null
  const s = [...values].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

/** Short hover text: the start of an idea's text, wrapped for a tooltip. */
export function snippet(text: string, max = 180, width = 60): string {
  const cut = text.length > max ? `${text.slice(0, max).replace(/\s+\S*$/, '')}…` : text
  const lines: string[] = []
  let line = ''
  for (const word of cut.split(/\s+/)) {
    if ((line + ' ' + word).trim().length > width) {
      lines.push(line)
      line = word
    } else line = (line + ' ' + word).trim()
  }
  if (line) lines.push(line)
  return lines.join('<br>')
}

export function fmt(v: number | null | undefined, digits = 2): string {
  return v === null || v === undefined || Number.isNaN(v) ? '—' : v.toFixed(digits)
}

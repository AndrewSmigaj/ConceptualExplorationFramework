// Table columns built from what a dataset declares: every facet, metric and text, every
// per-scorer field for each scorer, and every rubric dimension for each scorer.

import type { Index } from './data'
import { fmt } from './data'
import type { Idea } from './types'

export interface Column {
  id: string
  label: string
  title?: string
  numeric: boolean
  /** Ordered categories stored as numbers: sort by number, chart as these labels. */
  ordinal?: { id: number | string; label: string }[]
  value: (idea: Idea) => string | number | null
  show: (idea: Idea) => string
}

export function columnsFor(idx: Index): Column[] {
  const cols: Column[] = [
    { id: 'text', label: 'Idea', numeric: false, value: (i) => i.text, show: (i) => i.text },
    {
      id: 'author',
      label: 'Written by',
      numeric: false,
      value: (i) => idx.generatorLabel(i.author ?? ''),
      show: (i) => idx.generatorLabel(i.author ?? ''),
    },
  ]
  for (const f of idx.ds.fields) {
    if (f.per_scorer) continue
    if (f.kind === 'facet') {
      cols.push({
        id: `facet:${f.id}`,
        label: f.label,
        title: f.description,
        numeric: false,
        value: (i) => idx.valueLabel(f.id, i.facets?.[f.id] ?? null),
        show: (i) => (i.facets?.[f.id] == null ? '' : idx.valueLabel(f.id, i.facets[f.id])),
      })
    } else if (f.kind === 'metric') {
      cols.push({
        id: `metric:${f.id}`,
        label: f.label,
        title: f.description,
        numeric: true,
        value: (i) => i.metrics?.[f.id] ?? null,
        show: (i) => {
          const v = i.metrics?.[f.id]
          return v == null ? '' : Number.isInteger(v) ? String(v) : fmt(v)
        },
      })
    } else {
      cols.push({
        id: `text:${f.id}`,
        label: f.label,
        title: f.description,
        numeric: false,
        value: (i) => i.texts?.[f.id] ?? null,
        show: (i) => i.texts?.[f.id] ?? '',
      })
    }
  }
  const scored = idx.ds.scorers.filter((s) => idx.ds.ideas.some((i) => i.scorings?.[s.id]?.dims))
  for (const f of idx.ds.fields.filter((f) => f.per_scorer)) {
    for (const s of idx.ds.scorers) {
      if (!idx.ds.ideas.some((i) => i.per_scorer?.[s.id]?.[f.id] !== undefined)) continue
      const numeric = f.kind === 'metric'
      cols.push({
        id: `per:${f.id}@${s.id}`,
        label: `${f.label} · ${s.label}`,
        title: f.description,
        numeric: numeric || !!f.ordered,
        ordinal: !numeric && f.ordered ? (f.values ?? []).map((v) => ({ id: v.id, label: v.label })) : undefined,
        value: (i) => {
          const v = i.per_scorer?.[s.id]?.[f.id] ?? null
          return numeric || f.ordered ? (v as number | null) : idx.valueLabel(f.id, v)
        },
        show: (i) => {
          const v = i.per_scorer?.[s.id]?.[f.id] ?? null
          return v == null ? '' : numeric ? fmt(v as number) : idx.valueLabel(f.id, v)
        },
      })
    }
  }
  for (const d of idx.dims.values()) {
    for (const s of scored) {
      cols.push({
        id: `dim:${d.id}@${s.id}`,
        label: `${d.label} · ${s.label}`,
        title: d.description,
        numeric: true,
        value: (i) => i.scorings?.[s.id]?.dims?.[d.id] ?? null,
        show: (i) => fmt(i.scorings?.[s.id]?.dims?.[d.id]),
      })
    }
  }
  const clustering = Object.values(idx.ds.clusterings ?? {})[0]
  if (clustering) {
    const terms = new Map(clustering.clusters.map((c) => [c.id, (c.terms ?? []).slice(0, 2).join(', ')]))
    cols.push({
      id: 'cluster',
      label: 'Cluster',
      numeric: false,
      value: (i) => {
        const k = clustering.assignments[i.id]
        return k === undefined || k < 0 ? null : `${k} · ${terms.get(k) ?? ''}`
      },
      show: (i) => {
        const k = clustering.assignments[i.id]
        return k === undefined || k < 0 ? '' : `${k} · ${terms.get(k) ?? ''}`
      },
    })
  }
  return cols
}

/** The column to sort by at first: the headline dimension of the first scorer. */
export function defaultSort(idx: Index, cols: Column[]): string | undefined {
  const head = idx.headline?.id
  return cols.find((c) => head !== undefined && c.id.startsWith(`dim:${head}@`))?.id
}

/** A sensible first set: the idea, its first facet, the headline dimension per scorer,
 * each per-scorer facet, and a couple of metrics. */
export function defaultColumns(idx: Index, cols: Column[]): string[] {
  const head = idx.headline?.id
  const firstFacet = idx.ds.fields.find((f) => f.kind === 'facet' && !f.per_scorer)
  const perScorerFacet = (c: Column) => {
    if (!c.id.startsWith('per:')) return false
    return idx.fields.get(c.id.slice(4).split('@')[0])?.kind === 'facet'
  }
  const wanted = (c: Column) =>
    ['text', 'author', 'cluster', `facet:${firstFacet?.id}`].includes(c.id) ||
    (head !== undefined && c.id.startsWith(`dim:${head}@`)) ||
    perScorerFacet(c)
  return cols.filter(wanted).map((c) => c.id)
}

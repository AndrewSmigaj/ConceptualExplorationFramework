// Drawing the idea cloud from a projection, in 2D or 3D, coloured by a group, a
// gradient, or a blend of two values. Shared by projection presets and Explore.

import { valueColors } from './colors'
import {
  bivariateColor,
  type ColorOption,
  divergingScale,
  noValueColor,
  numericValue,
  scaleRange,
  type ScaleRange,
  tertiles,
} from './colorby'
import { fmt, type Index, snippet } from './data'
import { axis, baseLayout, chrome, type Layout } from './theme.svelte'
import type { Idea, Projection, Where } from './types'

export interface Mark {
  label: string
  where: Where
  symbol: string
}

export type Coloring =
  | {
      mode: 'group'
      label: string
      groups: { key: string; label: string; color: string; description?: string }[]
      groupOf: (i: Idea) => string | null
    }
  | {
      mode: 'scale'
      label: string
      valueOf: (i: Idea) => number | null
      range: ScaleRange
      colorscale: [number, string][]
    }
  | {
      mode: 'blend'
      labels: [string, string]
      valuesOf: (i: Idea) => [number, number] | null
      cuts: [[number, number], [number, number]]
      bandsOf: (i: Idea) => [number, number] | null
    }

export interface ColorChoice {
  primary: ColorOption
  /** A second numeric value to blend with the first. */
  secondary?: ColorOption
  centre: 'median' | 'middle'
  reverse: boolean
}

/** Resolve a colour choice against the ideas being shown. */
export function resolveColoring(idx: Index, ideas: Idea[], choice: ColorChoice): Coloring {
  const { primary, secondary } = choice
  if (!primary.numeric) {
    const field = idx.refField(primary.ref)
    const colors = valueColors(field)
    return {
      mode: 'group',
      label: primary.label,
      groups: (field?.values ?? []).map((v) => ({
        key: String(v.id),
        label: v.label,
        color: colors.get(v.id) ?? noValueColor(),
        description: v.description,
      })),
      groupOf: (i) => {
        const v = idx.value(primary.ref, i, primary.scorer)
        return v === null ? null : String(v)
      },
    }
  }
  const a = (i: Idea) => numericValue(idx, primary, i)
  if (secondary?.numeric) {
    const b = (i: Idea) => numericValue(idx, secondary, i)
    const ta = tertiles(ideas.map(a).filter((v): v is number => v !== null))
    const tb = tertiles(ideas.map(b).filter((v): v is number => v !== null))
    return {
      mode: 'blend',
      labels: [primary.label, secondary.label],
      cuts: [ta.cuts, tb.cuts],
      valuesOf: (i) => {
        const [x, y] = [a(i), b(i)]
        return x === null || y === null ? null : [x, y]
      },
      bandsOf: (i) => {
        const [x, y] = [a(i), b(i)]
        return x === null || y === null ? null : [ta.band(x), tb.band(y)]
      },
    }
  }
  const values = ideas.map(a).filter((v): v is number => v !== null)
  const range = scaleRange(values, idx.refRange(primary.ref), choice.centre)
  return {
    mode: 'scale',
    label: primary.label,
    valueOf: a,
    range,
    colorscale: divergingScale(range, choice.reverse),
  }
}

/** The projections a dataset has, so a view can offer method x dimensions. */
export function projectionChoices(idx: Index, allowed?: string[]) {
  const all = Object.entries(idx.ds.projections ?? {}).filter(
    ([id]) => !allowed || allowed.includes(id),
  )
  const methods = [...new Set(all.map(([, p]) => p.method))]
  const find = (method: string, dims: number) =>
    all.find(([, p]) => p.method === method && p.dims === dims)?.[0]
  return { methods, find, dims: [...new Set(all.map(([, p]) => p.dims))].sort().reverse() }
}

export function methodLabel(method: string): string {
  return method === 'pca' ? 'PCA' : method === 'umap' ? 'UMAP' : method
}

/**
 * Scatter traces for the ideas under a colouring. Ideas matching a mark are drawn with
 * its shape; each mark gets one neutral legend entry. `context` ideas are drawn first,
 * faint and grey, behind everything else.
 */
export function cloudTraces(
  idx: Index,
  proj: Projection,
  ideas: Idea[],
  coloring: Coloring,
  marks: Mark[] = [],
  context: Idea[] = [],
): Layout[] {
  const c = chrome()
  const three = proj.dims === 3
  const type = three ? 'scatter3d' : 'scatter'
  // In 3D a marked shape reads large already, so it is not enlarged further.
  const size = (marked: boolean) => (three ? 4 : marked ? 10 : 8)
  const traces: Layout[] = []
  const markOf = (i: Idea) => marks.findIndex((m) => idx.matches(m.where, i))
  const placed = (list: Idea[]) => list.filter((i) => proj.coords[i.id])
  const xyz = (list: Idea[]) => ({
    x: list.map((i) => proj.coords[i.id][0]),
    y: list.map((i) => proj.coords[i.id][1]),
    ...(three ? { z: list.map((i) => proj.coords[i.id][2]) } : {}),
  })
  const hover = (i: Idea, line: string) =>
    `<b>${line}</b> · ${idx.generatorLabel(i.author ?? '')}` +
    (markOf(i) >= 0 ? ` · <i>${marks[markOf(i)].label}</i>` : '') +
    `<br>${snippet(i.text)}`

  /** One trace per mark shape for a set of ideas; `marker` supplies the colour. */
  function shaped(
    list: Idea[],
    name: string,
    legend: { group: string; show: boolean },
    color: (members: Idea[]) => Layout,
    line: (i: Idea) => string,
    faint = false,
  ) {
    const all = placed(list)
    const markIdx = all.map(markOf)
    for (let m = -1; m < marks.length; m++) {
      const members = all.filter((_, n) => markIdx[n] === m)
      if (members.length === 0 && (m >= 0 || !legend.show)) continue
      traces.push({
        type,
        mode: 'markers',
        name,
        legendgroup: legend.group,
        showlegend: legend.show && m === -1,
        ...xyz(members),
        customdata: members.map((i) => i.id),
        text: members.map((i) => hover(i, line(i))),
        hovertemplate: '%{text}<extra></extra>',
        hoverinfo: faint ? 'skip' : undefined,
        marker: {
          ...color(members),
          size: size(m >= 0),
          symbol: m >= 0 ? marks[m].symbol : 'circle',
          opacity: faint ? 0.15 : 0.85,
          line: { color: c.surface, width: three ? 0.5 : 1 },
        },
      })
    }
  }

  if (context.length) {
    shaped(context, 'Other ideas', { group: 'context', show: true }, () => ({ color: c.other }), () => 'Other', true)
  }

  if (coloring.mode === 'group') {
    const byGroup = new Map<string | null, Idea[]>()
    for (const i of ideas) {
      const g = coloring.groupOf(i)
      byGroup.set(g, [...(byGroup.get(g) ?? []), i])
    }
    for (const g of coloring.groups) {
      const members = byGroup.get(g.key) ?? []
      if (members.length) shaped(members, g.label, { group: g.key, show: true }, () => ({ color: g.color }), () => g.label)
    }
    const none = byGroup.get(null) ?? []
    if (none.length) shaped(none, 'No value', { group: 'none', show: true }, () => ({ color: noValueColor() }), () => 'No value')
  } else if (coloring.mode === 'scale') {
    const withValue = ideas.filter((i) => coloring.valueOf(i) !== null)
    let first = true
    shaped(
      withValue,
      coloring.label,
      { group: 'scale', show: false },
      (members) => {
        const out = {
          color: members.map((i) => coloring.valueOf(i)),
          colorscale: coloring.colorscale,
          cmin: coloring.range.min,
          cmax: coloring.range.max,
          showscale: first,
          colorbar: {
            title: { text: coloring.label, side: 'right', font: { color: c.secondary, size: 12 } },
            thickness: 12,
            len: 0.7,
            outlinewidth: 0,
            tickfont: { color: c.muted, size: 11 },
          },
        }
        first = false
        return out
      },
      (i) => `${coloring.label} ${fmt(coloring.valueOf(i))}`,
    )
    const none = ideas.filter((i) => coloring.valueOf(i) === null)
    if (none.length) shaped(none, 'No value', { group: 'none', show: true }, () => ({ color: noValueColor() }), () => 'No value')
  } else {
    const classes = new Map<string, Idea[]>()
    const none: Idea[] = []
    for (const i of ideas) {
      const b = coloring.bandsOf(i)
      if (!b) none.push(i)
      else classes.set(b.join(','), [...(classes.get(b.join(',')) ?? []), i])
    }
    for (const [key, members] of classes) {
      const [ba, bb] = key.split(',').map(Number)
      shaped(
        members,
        key,
        { group: `blend-${key}`, show: false },
        () => ({ color: bivariateColor(ba, bb) }),
        (i) => {
          const v = coloring.valuesOf(i)!
          return `${coloring.labels[0]} ${fmt(v[0])} · ${coloring.labels[1]} ${fmt(v[1])}`
        },
      )
    }
    if (none.length) shaped(none, 'No value', { group: 'none', show: true }, () => ({ color: noValueColor() }), () => 'No value')
  }

  for (const m of marks) {
    traces.push({
      type,
      mode: 'markers',
      name: m.label,
      ...(three ? { x: [null], y: [null], z: [null] } : { x: [null], y: [null] }),
      // A legend swatch needs to be readable even where the plotted marks are small.
      marker: { color: c.muted, symbol: m.symbol, size: 9, line: { color: c.surface, width: 1 } },
      hoverinfo: 'skip',
    })
  }
  return traces
}

/** Axis titles and layout: PCA axes carry their share of variance; UMAP axes have no units. */
export function cloudLayout(proj: Projection, extra: Layout = {}): Layout {
  const c = chrome()
  const linear = proj.method === 'pca'
  const variance = proj.explained_variance ?? []
  const title = (k: number) =>
    linear
      ? `Component ${k + 1} (${((variance[k] ?? 0) * 100).toFixed(1)}%)`
      : `${methodLabel(proj.method)} ${k + 1}`
  const ax = (k: number) =>
    axis({
      title: { text: title(k) },
      showticklabels: linear,
      showgrid: linear,
      ticks: linear ? 'outside' : '',
    })
  if (proj.dims === 3) {
    const ax3 = (k: number) => ({
      ...ax(k),
      showbackground: false,
      gridcolor: c.grid,
      zerolinecolor: c.grid,
      showspikes: false,
    })
    return baseLayout({
      margin: { l: 0, r: 0, t: 40, b: 0 },
      scene: {
        xaxis: ax3(0),
        yaxis: ax3(1),
        zaxis: ax3(2),
        bgcolor: c.surface,
        aspectmode: 'cube',
        dragmode: 'orbit',
        camera: { eye: { x: 1.15, y: 1.15, z: 0.75 } },
      },
      ...extra,
    })
  }
  return baseLayout({ xaxis: ax(0), yaxis: ax(1), margin: { l: 56, r: 16, t: 64, b: 52 }, ...extra })
}

/** Thin lines from each shown idea to each of its shown parents: lineage at a glance. */
export function lineageTrace(proj: Projection, ideas: Idea[], shown: Set<string>, highlight?: string): Layout | null {
  const c = chrome()
  const three = proj.dims === 3
  const xs: (number | null)[] = []
  const ys: (number | null)[] = []
  const zs: (number | null)[] = []
  for (const i of ideas) {
    for (const p of i.parents ?? []) {
      if (!shown.has(p) || !proj.coords[p] || !proj.coords[i.id]) continue
      if (highlight && p !== highlight && i.id !== highlight) continue
      const [a, b] = [proj.coords[p], proj.coords[i.id]]
      xs.push(a[0], b[0], null)
      ys.push(a[1], b[1], null)
      if (three) zs.push(a[2], b[2], null)
    }
  }
  if (!xs.length) return null
  return {
    type: three ? 'scatter3d' : 'scatter',
    mode: 'lines',
    name: 'Lineage',
    x: xs,
    y: ys,
    ...(three ? { z: zs } : {}),
    line: { color: highlight ? c.secondary : c.axis, width: highlight ? 3 : 1.5 },
    opacity: highlight ? 0.9 : 0.5,
    hoverinfo: 'skip',
  }
}

/** Text labels at given positions, e.g. cluster names at cluster centres. */
export function labelTrace(proj: Projection, labels: { text: string; at: number[] }[]): Layout {
  const c = chrome()
  const three = proj.dims === 3
  return {
    type: three ? 'scatter3d' : 'scatter',
    mode: 'text',
    name: 'Labels',
    showlegend: false,
    x: labels.map((l) => l.at[0]),
    y: labels.map((l) => l.at[1]),
    ...(three ? { z: labels.map((l) => l.at[2]) } : {}),
    text: labels.map((l) => l.text),
    textfont: { color: c.primary, size: 12 },
    hoverinfo: 'skip',
  }
}

/** The mean position of a set of ideas in a projection. */
export function centroid(proj: Projection, ids: string[]): number[] | null {
  const pts = ids.map((i) => proj.coords[i]).filter(Boolean)
  if (!pts.length) return null
  return pts[0].map((_, k) => pts.reduce((s, p) => s + p[k], 0) / pts.length)
}

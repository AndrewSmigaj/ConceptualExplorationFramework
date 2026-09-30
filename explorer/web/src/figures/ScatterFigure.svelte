<script lang="ts">
  import Plot from '../components/Plot.svelte'
  import { valueColors } from '../lib/colors'
  import { type Bin, binnedMeans, fmt, type Index, snippet, stableJitter } from '../lib/data'
  import { axis, baseLayout, chrome, identityColor, type Layout, scheme } from '../lib/theme.svelte'
  import type { Idea, Preset, Ref, Where } from '../lib/types'

  interface Spec {
    panels: string[]
    x: Ref[]
    y: Ref[]
    /** "author": one line per generator. A reference: one line per value of that facet. */
    split?: 'author' | Ref
    bins?: number
    jitter?: number
    filters?: { id: string; label: string; where: Where }[]
  }

  let { idx, preset }: { idx: Index; preset: Preset } = $props()

  const spec = $derived(preset.spec as unknown as Spec)
  let xi = $state(0)
  let yi = $state(0)
  let active = $state<Record<string, boolean>>({})
  let showTable = $state(false)
  let plot = $state<Plot>()

  interface Group {
    key: string
    label: string
    color: string
    of: (idea: Idea, scorer: string) => boolean
  }

  function groups(): Group[] {
    const split = spec.split
    if (split === 'author') {
      return [...idx.generators.keys()].map((g) => ({
        key: g,
        label: `Written by ${idx.generatorLabel(g)}`,
        color: identityColor(g, idx.entities),
        of: (i) => i.author === g,
      }))
    }
    if (split) {
      const field = idx.refField(split)
      const colors = valueColors(field)
      return (field?.values ?? []).map((v) => ({
        key: String(v.id),
        label: v.label,
        color: colors.get(v.id) ?? chrome().other,
        of: (i, s) => idx.value(split, i, s) === v.id,
      }))
    }
    return [{ key: 'all', label: 'All', color: identityColor('', []), of: () => true }]
  }

  const figure = $derived.by(() => {
    void scheme.dark
    const xRef = spec.x[xi] ?? spec.x[0]
    const yRef = spec.y[yi] ?? spec.y[0]
    const jitter = spec.jitter ?? 0
    const c = chrome()
    const ideas = idx.ds.ideas.filter((i) =>
      (spec.filters ?? []).every((f) => !active[f.id] || idx.matches(f.where, i)),
    )
    const gs = groups()
    const traces: Layout[] = []
    const rows: { panel: string; group: string; bin: Bin }[] = []
    const layout = baseLayout({
      grid: { rows: 1, columns: spec.panels.length, pattern: 'independent', xgap: 0.08 },
      margin: { l: 56, r: 16, t: 96, b: 56 },
      annotations: [] as Layout[],
    })
    const yRange = idx.refRange(yRef)
    const pad = jitter + 0.03

    spec.panels.forEach((scorer, p) => {
      const ax = p === 0 ? '' : String(p + 1)
      for (const g of gs) {
        const pts = ideas
          .filter((i) => g.of(i, scorer))
          .map((i) => ({ i, x: idx.value(xRef, i, scorer), y: idx.value(yRef, i, scorer) }))
          .filter((d): d is { i: Idea; x: number; y: number } =>
            typeof d.x === 'number' && typeof d.y === 'number')
        if (pts.length === 0) continue
        traces.push({
          type: 'scatter',
          mode: 'markers',
          xaxis: `x${ax}`,
          yaxis: `y${ax}`,
          name: g.label,
          legendgroup: g.key,
          showlegend: false,
          x: pts.map((d) => d.x),
          y: pts.map((d) => d.y + stableJitter(d.i.id) * jitter),
          text: pts.map(
            (d) =>
              `<b>${g.label}</b><br>${idx.refLabel(yRef)} ${fmt(d.y)} · ` +
              `${idx.refLabel(xRef)} ${fmt(d.x)}<br>${snippet(d.i.text)}`,
          ),
          hovertemplate: '%{text}<extra></extra>',
          marker: { color: g.color, size: 5, opacity: 0.3 },
        })
        const bins = binnedMeans(pts, spec.bins ?? 8)
        bins.forEach((bin) => rows.push({ panel: idx.scorerLabel(scorer), group: g.label, bin }))
        traces.push({
          type: 'scatter',
          mode: 'lines+markers',
          xaxis: `x${ax}`,
          yaxis: `y${ax}`,
          name: g.label,
          legendgroup: g.key,
          showlegend: p === 0,
          x: bins.map((b) => b.x),
          y: bins.map((b) => b.y),
          error_y: { type: 'data', array: bins.map((b) => b.ci), color: g.color, thickness: 1.5, width: 0 },
          text: bins.map(
            (b) =>
              `<b>${g.label}</b><br>mean ${fmt(b.y)} ± ${fmt(b.ci)} (n=${b.n})<br>` +
              `${idx.refLabel(xRef)} ${fmt(b.xLow)}–${fmt(b.xHigh)}`,
          ),
          hovertemplate: '%{text}<extra></extra>',
          line: { color: g.color, width: 2 },
          marker: { color: g.color, size: 8, line: { color: c.surface, width: 2 } },
        })
      }
      layout[`xaxis${ax}`] = axis({ title: { text: idx.refLabel(xRef) } })
      layout[`yaxis${ax}`] = axis({
        title: { text: p === 0 ? idx.refLabel(yRef) : '' },
        range: yRange ? [yRange[0] - pad, yRange[1] + pad] : undefined,
        matches: p === 0 ? undefined : 'y',
      })
      layout.annotations.push({
        text: `<b>Scored by ${idx.scorerLabel(scorer)}</b>`,
        xref: `x${ax} domain`,
        yref: `y${ax} domain`,
        x: 0,
        y: 1.02,
        xanchor: 'left',
        yanchor: 'bottom',
        showarrow: false,
        font: { color: c.primary, size: 13 },
      })
    })
    layout.legend = { ...layout.legend, y: 1.12 }
    return { traces, layout, rows, n: ideas.length }
  })
</script>

<div class="controls">
  {#if spec.x.length > 1}
    <label class="control">
      Across
      <select bind:value={xi}>
        {#each spec.x as r, k (k)}<option value={k}>{idx.refLabel(r)}</option>{/each}
      </select>
    </label>
  {/if}
  {#if spec.y.length > 1}
    <label class="control">
      Score
      <select bind:value={yi}>
        {#each spec.y as r, k (k)}<option value={k}>{idx.refLabel(r)}</option>{/each}
      </select>
    </label>
  {/if}
  {#each spec.filters ?? [] as f (f.id)}
    <label class="control"><input type="checkbox" bind:checked={active[f.id]} /> {f.label}</label>
  {/each}
  <span class="spacer"></span>
  <span class="tools">
    <label class="control"><input type="checkbox" bind:checked={showTable} /> Table</label>
    <button class="btn" onclick={() => plot?.download('png')}>PNG</button>
    <button class="btn" onclick={() => plot?.download('svg')}>SVG</button>
  </span>
</div>

{#if idx.refDescription(spec.x[xi] ?? spec.x[0])}
  <p class="note">{idx.refLabel(spec.x[xi] ?? spec.x[0])}: {idx.refDescription(spec.x[xi] ?? spec.x[0])}</p>
{/if}

<Plot bind:this={plot} data={figure.traces} layout={figure.layout} filename={preset.id} height={560} />
<p class="note">
  {figure.n.toLocaleString()} ideas. Faint dots are single ideas (nudged vertically so equal
  scores do not hide each other); lines are means of equal-count bins with 95% intervals.
</p>

{#if showTable}
  <table class="data">
    <thead>
      <tr>
        <th>Scorer</th>
        <th>Line</th>
        <th class="num">From</th>
        <th class="num">To</th>
        <th class="num">Ideas</th>
        <th class="num">Mean score</th>
        <th class="num">± 95%</th>
      </tr>
    </thead>
    <tbody>
      {#each figure.rows as r, k (k)}
        <tr>
          <td>{r.panel}</td>
          <td>{r.group}</td>
          <td class="num">{fmt(r.bin.xLow)}</td>
          <td class="num">{fmt(r.bin.xHigh)}</td>
          <td class="num">{r.bin.n}</td>
          <td class="num">{fmt(r.bin.y)}</td>
          <td class="num">{fmt(r.bin.ci)}</td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  .note {
    color: var(--muted);
    font-size: 0.9em;
    margin: 6px 0;
    max-width: 90ch;
  }
</style>

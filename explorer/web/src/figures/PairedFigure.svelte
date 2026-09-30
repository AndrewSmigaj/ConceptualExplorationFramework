<script lang="ts">
  import Plot from '../components/Plot.svelte'
  import { fmt, type Index, snippet, stableJitter } from '../lib/data'
  import { axis, baseLayout, chrome, identityColor, type Layout, scheme } from '../lib/theme.svelte'
  import type { Idea, Preset, Ref } from '../lib/types'

  interface Spec {
    panels: string[]
    /** The scorer every panel's scorer is compared against. */
    reference: string
    /** A per-scorer facet: the groups along the x axis, read for each panel's scorer. */
    x: Ref
    y: Ref[]
  }

  let { idx, preset }: { idx: Index; preset: Preset } = $props()

  const spec = $derived(preset.spec as unknown as Spec)
  let yi = $state(0)
  let showTable = $state(false)
  let plot = $state<Plot>()

  const field = $derived(idx.refField(spec.x))
  const refLabel = $derived(idx.scorerLabel(spec.reference))

  const figure = $derived.by(() => {
    void scheme.dark
    const yRef = spec.y[yi] ?? spec.y[0]
    const c = chrome()
    const values = field?.values ?? []
    const refColor = identityColor(idx.entityOfScorer(spec.reference), idx.entities)
    const rated = idx.ds.ideas.filter((i) => idx.value(yRef, i, spec.reference) !== null)
    const traces: Layout[] = []
    const rows: { panel: string; group: string; idea: Idea; ref: number; other: number }[] = []
    const layout = baseLayout({
      grid: { rows: 1, columns: spec.panels.length, pattern: 'independent', xgap: 0.08 },
      margin: { l: 56, r: 16, t: 96, b: 84 },
      annotations: [] as Layout[],
    })
    const range = idx.refRange(yRef)

    spec.panels.forEach((scorer, p) => {
      const ax = p === 0 ? '' : String(p + 1)
      const color = identityColor(idx.entityOfScorer(scorer), idx.entities)
      const pairs = rated
        .map((i) => ({
          i,
          g: values.findIndex((v) => v.id === idx.value(spec.x, i, scorer)),
          ref: idx.value(yRef, i, spec.reference) as number,
          other: idx.value(yRef, i, scorer),
        }))
        .filter((d): d is { i: Idea; g: number; ref: number; other: number } =>
          d.g >= 0 && typeof d.other === 'number')
      const centre = (d: { i: Idea; g: number }) => d.g + stableJitter(d.i.id) * 0.22
      // Connectors first, so the dots sit on top of them.
      traces.push({
        type: 'scatter',
        mode: 'lines',
        xaxis: `x${ax}`,
        yaxis: `y${ax}`,
        x: pairs.flatMap((d) => [centre(d) - 0.06, centre(d) + 0.06, null]),
        y: pairs.flatMap((d) => [d.ref, d.other, null]),
        line: { color: c.axis, width: 1.5 },
        hoverinfo: 'skip',
        showlegend: false,
      })
      const dots = (who: 'ref' | 'other', name: string, col: string, dx: number, legend: boolean) => ({
        type: 'scatter',
        mode: 'markers',
        xaxis: `x${ax}`,
        yaxis: `y${ax}`,
        name,
        legendgroup: name,
        showlegend: legend,
        x: pairs.map((d) => centre(d) + dx),
        y: pairs.map((d) => d[who]),
        text: pairs.map(
          (d) =>
            `<b>${refLabel} ${fmt(d.ref)} · ${idx.scorerLabel(scorer)} ${fmt(d.other)}</b><br>` +
            (d.i.scorings?.[spec.reference]?.flags?.length
              ? `<i>${refLabel}: ${d.i.scorings[spec.reference].flags!.join(', ')}</i><br>`
              : '') +
            `${snippet(d.i.text)}`,
        ),
        hovertemplate: '%{text}<extra></extra>',
        marker: {
          color: col,
          size: 10,
          // A flagged rating (e.g. corrected after reveal) is drawn open, and says why on hover.
          symbol: pairs.map((d) =>
            who === 'ref' && d.i.scorings?.[spec.reference]?.flags?.length ? 'circle-open' : 'circle'),
          line: { color: who === 'ref' ? col : c.surface, width: 2 },
        },
      })
      traces.push(dots('ref', refLabel, refColor, -0.06, p === 0))
      traces.push(dots('other', idx.scorerLabel(scorer), color, 0.06, true))
      pairs.forEach((d) =>
        rows.push({ panel: idx.scorerLabel(scorer), group: values[d.g].label, idea: d.i, ref: d.ref, other: d.other }),
      )

      const ticktext = values.map((v, g) => {
        const inGroup = pairs.filter((d) => d.g === g)
        if (inGroup.length === 0) return `${v.label}<br><span>none rated</span>`
        const gap = inGroup.reduce((s, d) => s + (d.other - d.ref), 0) / inGroup.length
        return `${v.label}<br><span>n=${inGroup.length} · mean gap ${gap >= 0 ? '+' : ''}${fmt(gap)}</span>`
      })
      layout[`xaxis${ax}`] = axis({
        tickvals: values.map((_, g) => g),
        ticktext,
        range: [-0.5, values.length - 0.5],
        showgrid: false,
      })
      layout[`yaxis${ax}`] = axis({
        title: { text: p === 0 ? idx.refLabel(yRef) : '' },
        range: range ? [range[0] - 0.04, range[1] + 0.04] : undefined,
        matches: p === 0 ? undefined : 'y',
      })
      layout.annotations.push({
        text: `<b>Scored by ${idx.scorerLabel(scorer)}</b> and by ${refLabel}`,
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
    return { traces, layout, rows, rated: rated.length }
  })
</script>

<div class="controls">
  {#if spec.y.length > 1}
    <label class="control">
      Score
      <select bind:value={yi}>
        {#each spec.y as r, k (k)}<option value={k}>{idx.refLabel(r)}</option>{/each}
      </select>
    </label>
  {/if}
  <span class="spacer"></span>
  <span class="tools">
    <label class="control"><input type="checkbox" bind:checked={showTable} /> Table</label>
    <button class="btn" onclick={() => plot?.download('png')}>PNG</button>
    <button class="btn" onclick={() => plot?.download('svg')}>SVG</button>
  </span>
</div>

{#if figure.rated === 0}
  <p class="note">No revealed ratings by {refLabel} yet. They appear here once a rating session is revealed.</p>
{:else}
  <Plot bind:this={plot} data={figure.traces} layout={figure.layout} filename={preset.id} height={560} />
  <p class="note">
    {figure.rated} ideas rated by {refLabel}. Each line joins one idea's two scores; "mean gap" is the
    other scorer minus {refLabel}, so a negative gap means the model scored lower.
  </p>
  {#if showTable}
    <table class="data">
      <thead>
        <tr>
          <th>Scorer</th>
          <th>{field?.label}</th>
          <th>Idea</th>
          <th class="num">{refLabel}</th>
          <th class="num">Scorer</th>
          <th class="num">Gap</th>
        </tr>
      </thead>
      <tbody>
        {#each figure.rows as r, k (k)}
          <tr>
            <td>{r.panel}</td>
            <td>{r.group}</td>
            <td class="text">{r.idea.text}</td>
            <td class="num">{fmt(r.ref)}</td>
            <td class="num">{fmt(r.other)}</td>
            <td class="num">{r.other - r.ref >= 0 ? '+' : ''}{fmt(r.other - r.ref)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
{/if}

<style>
  .note {
    color: var(--muted);
    font-size: 0.9em;
    margin: 6px 0;
    max-width: 90ch;
  }

  td.text {
    max-width: 60ch;
    font-size: 0.92em;
  }
</style>

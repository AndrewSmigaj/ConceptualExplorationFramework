<script lang="ts">
  import Plot from '../components/Plot.svelte'
  import { valueColors } from '../lib/colors'
  import { fmt, type Index, median } from '../lib/data'
  import { axis, baseLayout, chrome, type Layout, scheme } from '../lib/theme.svelte'
  import type { Idea, Preset, Ref } from '../lib/types'

  type Column =
    | { kind: 'count'; label?: string }
    | { kind: 'per_scorer_counts'; per_scorer: string; scorers: string[] }
    | { kind: 'median'; ref: Ref; label?: string }

  interface Spec {
    rows: { field: string }
    columns: Column[]
    footnotes?: string[]
  }

  let { idx, preset }: { idx: Index; preset: Preset } = $props()

  const spec = $derived(preset.spec as unknown as Spec)
  const rowField = $derived(idx.fields.get(spec.rows.field))

  /** Header cells, flattened: per-scorer count columns expand to one per scorer and value. */
  const headers = $derived.by(() => {
    const out: { group?: string; label: string; title?: string; cell: (ideas: Idea[]) => string }[] = []
    for (const col of spec.columns) {
      if (col.kind === 'count') {
        out.push({ label: col.label ?? 'Ideas', cell: (ideas) => ideas.length.toLocaleString() })
      } else if (col.kind === 'median') {
        out.push({
          label: col.label ?? `Median ${idx.refLabel(col.ref).toLowerCase()}`,
          cell: (ideas) =>
            fmt(median(ideas.map((i) => idx.value(col.ref, i)).filter((v): v is number => typeof v === 'number')), 0),
        })
      } else {
        const field = idx.fields.get(col.per_scorer)
        for (const s of col.scorers) {
          for (const v of field?.values ?? []) {
            out.push({
              group: `${field?.label ?? col.per_scorer} · ${idx.scorerLabel(s)}`,
              label: v.label,
              title: v.description,
              cell: (ideas) =>
                ideas.filter((i) => i.per_scorer?.[s]?.[col.per_scorer] === v.id).length.toLocaleString(),
            })
          }
        }
      }
    }
    return out
  })

  const groupSpans = $derived.by(() => {
    const spans: { label: string; span: number }[] = []
    for (const h of headers) {
      const label = h.group ?? ''
      const last = spans[spans.length - 1]
      if (last && last.label === label) last.span++
      else spans.push({ label, span: 1 })
    }
    return spans
  })

  const rows = $derived(
    (rowField?.values ?? [])
      .map((v) => ({
        label: v.label,
        title: v.description,
        ideas: idx.ds.ideas.filter((i) => i.facets?.[spec.rows.field] === v.id),
      }))
      .filter((r) => r.ideas.length > 0),
  )

  // The table's figure: for each per-scorer count column, stacked bars of each row's
  // split, one panel per scorer. Counts show size; shares show the mix.
  let shares = $state(false)
  let plot = $state<Plot>()

  const chart = $derived.by(() => {
    void scheme.dark
    const col = spec.columns.find((c) => c.kind === 'per_scorer_counts')
    if (!col || col.kind !== 'per_scorer_counts') return null
    const field = idx.fields.get(col.per_scorer)
    const values = field?.values ?? []
    const colors = valueColors(field)
    const c = chrome()
    const labels = rows.map((r) => r.label)
    const traces: Layout[] = []
    const layout = baseLayout({
      grid: { rows: 1, columns: col.scorers.length, pattern: 'independent', xgap: 0.06 },
      barmode: 'stack',
      bargap: 0.45,
      margin: { l: 150, r: 16, t: 96, b: 52 },
      annotations: [] as Layout[],
    })
    col.scorers.forEach((s, p) => {
      const ax = p === 0 ? '' : String(p + 1)
      for (const v of values) {
        const counts = rows.map((r) => r.ideas.filter((i) => i.per_scorer?.[s]?.[col.per_scorer] === v.id).length)
        const totals = rows.map((r) => r.ideas.length)
        traces.push({
          type: 'bar',
          orientation: 'h',
          xaxis: `x${ax}`,
          yaxis: `y${ax}`,
          name: v.label,
          legendgroup: String(v.id),
          showlegend: p === 0,
          y: labels,
          x: counts.map((n, k) => (shares ? (totals[k] ? n / totals[k] : 0) : n)),
          text: counts.map((n, k) => `<b>${v.label}</b><br>${labels[k]}: ${n} of ${totals[k]} (${totals[k] ? Math.round((100 * n) / totals[k]) : 0}%)`),
          hovertemplate: '%{text}<extra></extra>',
          textposition: 'none',
          marker: { color: colors.get(v.id), line: { color: c.surface, width: 2 } },
        })
      }
      layout[`xaxis${ax}`] = axis({
        title: { text: shares ? 'Share of the arm' : 'Ideas' },
        tickformat: shares ? '.0%' : ',d',
        range: shares ? [0, 1] : undefined,
      })
      layout[`yaxis${ax}`] = axis({
        autorange: 'reversed',
        showgrid: false,
        showticklabels: p === 0,
        matches: p === 0 ? undefined : 'y',
      })
      layout.annotations.push({
        text: `<b>${field?.label ?? col.per_scorer} · ${idx.scorerLabel(s)}</b>`,
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
    layout.legend = { ...layout.legend, y: 1.14 }
    return { traces, layout }
  })

  function csv(): string {
    const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s)
    const head = [rowField?.label ?? '', ...headers.map((h) => (h.group ? `${h.group}: ${h.label}` : h.label))]
    const body = [...rows, { label: 'Total', ideas: idx.ds.ideas }].map((r) => [
      r.label,
      ...headers.map((h) => h.cell(r.ideas).replace(/,/g, '')),
    ])
    return [head, ...body].map((line) => line.map(esc).join(',')).join('\n')
  }

  function downloadCsv() {
    const url = URL.createObjectURL(new Blob([csv()], { type: 'text/csv' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: `${preset.id}.csv` })
    a.click()
    URL.revokeObjectURL(url)
  }
</script>

<div class="controls">
  {#if chart}
    <span class="seg" role="group" aria-label="Bar length">
      <button class:on={!shares} onclick={() => (shares = false)}>Counts</button>
      <button class:on={shares} onclick={() => (shares = true)}>Shares</button>
    </span>
  {/if}
  <span class="spacer"></span>
  <span class="tools">
    {#if chart}
      <button class="btn" onclick={() => plot?.download('png')}>PNG</button>
      <button class="btn" onclick={() => plot?.download('svg')}>SVG</button>
    {/if}
    <button class="btn" onclick={downloadCsv}>CSV</button>
  </span>
</div>

{#if chart}
  <Plot bind:this={plot} data={chart.traces} layout={chart.layout} filename={preset.id} height={Math.max(360, 60 * rows.length + 160)} />
{/if}

<div class="scroll">
  <table class="data">
    <thead>
      {#if groupSpans.some((g) => g.label)}
        <tr>
          <th></th>
          {#each groupSpans as g, k (k)}<th class="group" colspan={g.span}>{g.label}</th>{/each}
        </tr>
      {/if}
      <tr>
        <th>{rowField?.label}</th>
        {#each headers as h, k (k)}<th class="num" title={h.title}>{h.label}</th>{/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as r (r.label)}
        <tr>
          <td title={r.title}>{r.label}</td>
          {#each headers as h, k (k)}<td class="num">{h.cell(r.ideas)}</td>{/each}
        </tr>
      {/each}
      <tr class="total">
        <td>Total</td>
        {#each headers as h, k (k)}<td class="num">{h.cell(idx.ds.ideas)}</td>{/each}
      </tr>
    </tbody>
  </table>
</div>

{#if spec.footnotes?.length}
  <ol class="footnotes">
    {#each spec.footnotes as f, k (k)}<li>{f}</li>{/each}
  </ol>
{/if}

{#each spec.columns as col, k (k)}
  {#if col.kind === 'per_scorer_counts'}
    {@const field = idx.fields.get(col.per_scorer)}
    <dl class="legend-notes">
      {#each field?.values ?? [] as v (v.id)}
        {#if v.description}<dt>{v.label}</dt><dd>{v.description}</dd>{/if}
      {/each}
    </dl>
  {/if}
{/each}

<style>
  .scroll {
    overflow-x: auto;
  }

  th.group {
    text-align: center;
    color: var(--text);
    border-bottom: 1px solid var(--muted);
  }

  th[title],
  td[title] {
    cursor: help;
  }

  .footnotes {
    color: var(--muted);
    font-size: 0.9em;
    max-width: 90ch;
    padding-left: 20px;
  }

  .legend-notes {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 12px;
    font-size: 0.9em;
    margin: 8px 0;
  }

  .legend-notes dt {
    font-weight: 600;
  }

  .legend-notes dd {
    margin: 0;
    color: var(--muted);
  }
</style>

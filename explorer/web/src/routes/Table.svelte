<script lang="ts">
  import DetailPanel from '../components/DetailPanel.svelte'
  import Plot from '../components/Plot.svelte'
  import { type Column, columnsFor, defaultColumns, defaultSort } from '../lib/columns'
  import { Index } from '../lib/data'
  import { href } from '../lib/router.svelte'
  import { clearPick, picked } from '../lib/selection.svelte'
  import { loadDataset, loadMeta } from '../lib/store'
  import { axis, baseLayout, categorical8, chrome, type Layout, scheme } from '../lib/theme.svelte'
  import type { Idea, Meta } from '../lib/types'

  let idx = $state<Index | null>(null)
  let meta = $state<Meta | null>(null)
  let error = $state('')
  let cols = $state<Column[]>([])
  let shownCols = $state<string[]>([])
  Promise.all([loadDataset(), loadMeta()])
    .then(([ds, m]) => {
      idx = new Index(ds)
      meta = m
      cols = columnsFor(idx)
      shownCols = defaultColumns(idx, cols)
      sortId = defaultSort(idx, cols) ?? ''

    })
    .catch((e) => (error = e.message))

  let query = $state('')
  let sortId = $state('')
  let descending = $state(true)
  let limit = $state(200)
  let selected = $state<string | null>(null)

  const visibleCols = $derived(shownCols.map((id) => cols.find((c) => c.id === id)).filter((c): c is Column => !!c))
  const sortCol = $derived(cols.find((c) => c.id === sortId) ?? visibleCols.find((c) => c.numeric))

  const rows = $derived.by(() => {
    if (!idx) return []
    const only = picked.current ? new Set(picked.current.ids) : null
    const q = query.trim().toLowerCase()
    let out = idx.ds.ideas.filter(
      (i) =>
        (!only || only.has(i.id)) &&
        (!q || i.text.toLowerCase().includes(q) || (i.essence ?? '').toLowerCase().includes(q)),
    )
    const c = sortCol
    if (c) {
      const dir = descending ? -1 : 1
      out = [...out].sort((a, b) => {
        const [x, y] = [c.value(a), c.value(b)]
        if (x === null || x === '') return 1
        if (y === null || y === '') return -1
        return (x < y ? -1 : x > y ? 1 : 0) * dir
      })
    }
    return out
  })

  function sortBy(c: Column) {
    if (sortCol?.id === c.id) descending = !descending
    else {
      sortId = c.id
      descending = c.numeric
    }
  }

  // The table's figure: how the sort column is spread across the rows in view.
  const chart = $derived.by(() => {
    void scheme.dark
    const c = sortCol
    if (!c || !rows.length) return null
    const ch = chrome()
    if (c.ordinal) {
      const counts = c.ordinal.map((o) => rows.filter((r) => c.value(r) === o.id).length)
      return {
        traces: [
          {
            type: 'bar',
            x: c.ordinal.map((o) => o.label),
            y: counts,
            marker: { color: categorical8(0), line: { color: ch.surface, width: 1 } },
            hovertemplate: '%{x}: %{y} ideas<extra></extra>',
          },
        ] as Layout[],
        layout: baseLayout({
          xaxis: axis({ title: { text: c.label }, type: 'category' }),
          yaxis: axis({ title: { text: 'Ideas' } }),
          bargap: 0.5,
          margin: { l: 56, r: 16, t: 16, b: 48 },
          showlegend: false,
        }),
      }
    }
    if (c.numeric) {
      const xs = rows.map((r) => c.value(r)).filter((v): v is number => typeof v === 'number')
      return {
        traces: [
          {
            type: 'histogram',
            x: xs,
            nbinsx: 24,
            marker: { color: categorical8(0), line: { color: ch.surface, width: 1 } },
            hovertemplate: '%{x}: %{y} ideas<extra></extra>',
          },
        ] as Layout[],
        layout: baseLayout({
          xaxis: axis({ title: { text: c.label } }),
          yaxis: axis({ title: { text: 'Ideas' } }),
          bargap: 0.05,
          margin: { l: 56, r: 16, t: 16, b: 48 },
          showlegend: false,
        }),
      }
    }
    const counts = new Map<string, number>()
    for (const r of rows) {
      const v = String(c.value(r) ?? '—')
      counts.set(v, (counts.get(v) ?? 0) + 1)
    }
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12)
    return {
      traces: [
        {
          type: 'bar',
          orientation: 'h',
          y: top.map(([k]) => (k.length > 60 ? `${k.slice(0, 57)}…` : k)),
          x: top.map(([, n]) => n),
          marker: { color: categorical8(0), line: { color: ch.surface, width: 1 } },
          hovertemplate: '%{y}: %{x} ideas<extra></extra>',
        },
      ] as Layout[],
      layout: baseLayout({
        xaxis: axis({ title: { text: 'Ideas' } }),
        yaxis: axis({ autorange: 'reversed', showgrid: false, automargin: true }),
        bargap: 0.35,
        margin: { l: 16, r: 16, t: 16, b: 48 },
        showlegend: false,
      }),
    }
  })

  function csv(): string {
    const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s)
    const head = ['id', ...visibleCols.map((c) => c.label)]
    const body = rows.map((r) => [r.id, ...visibleCols.map((c) => c.show(r))])
    return [head, ...body].map((line) => line.map((x) => esc(String(x))).join(',')).join('\n')
  }

  function downloadCsv() {
    const url = URL.createObjectURL(new Blob([csv()], { type: 'text/csv' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: 'ideas.csv' })
    a.click()
    URL.revokeObjectURL(url)
  }

  const held = $derived(meta?.sessions.filter((s) => !s.revealed && s.held_back > 0) ?? [])
  const selectedIdea = $derived<Idea | undefined>(selected && idx ? idx.ideas.get(selected) : undefined)
</script>

{#if error}
  <p class="error">Could not load the data: {error}</p>
{:else if !idx}
  <p class="muted">Loading…</p>
{:else}
  <div class="page" class:with-detail={!!selectedIdea}>
    <section class="main">
      {#each held as s (s.id)}
        <p class="banner">{s.held_back} ideas held back until <b>{s.id}</b> is revealed.</p>
      {/each}
      {#if picked.current}
        <p class="banner">
          Showing <b>{picked.current.label}</b> ({picked.current.ids.length} ideas).
          <button class="btn" onclick={clearPick}>Show all</button>
          <a class="btn" href={href('/explore')}>Back to Explore</a>
        </p>
      {/if}

      <div class="controls">
        <input class="search" type="search" placeholder="Search text and essence" bind:value={query} />
        <details class="chooser">
          <summary class="btn">Columns ({visibleCols.length})</summary>
          <div class="choices">
            {#each cols as c (c.id)}
              <label title={c.title}>
                <input
                  type="checkbox"
                  checked={shownCols.includes(c.id)}
                  onchange={(e) =>
                    (shownCols = e.currentTarget.checked
                      ? [...shownCols, c.id]
                      : shownCols.filter((x) => x !== c.id))}
                />
                {c.label}
              </label>
            {/each}
          </div>
        </details>
        <span class="spacer"></span>
        <span class="muted">{rows.length.toLocaleString()} ideas</span>
        <button class="btn" onclick={downloadCsv}>CSV</button>
      </div>

      {#if chart && sortCol}
        <h2 class="chart-title">{sortCol.label} across these {rows.length.toLocaleString()} ideas</h2>
        <Plot data={chart.traces} layout={chart.layout} filename="table-{sortCol.id}" height={220} />
      {/if}

      <div class="scroll">
        <table class="data">
          <thead>
            <tr>
              {#each visibleCols as c (c.id)}
                <th class:num={c.numeric} title={c.title}>
                  <button class="sort" onclick={() => sortBy(c)}>
                    {c.label}{#if sortCol?.id === c.id}{descending ? ' ↓' : ' ↑'}{/if}
                  </button>
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each rows.slice(0, limit) as r (r.id)}
              <tr class:on={selected === r.id} onclick={() => (selected = r.id)}>
                {#each visibleCols as c (c.id)}
                  <td class:num={c.numeric} class:text={c.id === 'text'}>{c.show(r)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if rows.length > limit}
        <button class="btn more" onclick={() => (limit += 400)}>Show more ({rows.length - limit} left)</button>
      {/if}
    </section>

    {#if selectedIdea}
      <DetailPanel {idx} idea={selectedIdea} onselect={(id) => (selected = id)} onclose={() => (selected = null)} />
    {/if}
  </div>
{/if}

<style>
  .page {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .page.with-detail {
    grid-template-columns: minmax(0, 1fr) 380px;
  }

  .main {
    min-width: 0;
  }

  .banner {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 10px;
    padding: 6px 10px;
    border-radius: var(--radius);
    background: var(--accent-soft);
    font-size: 0.92em;
  }

  .search {
    font: inherit;
    padding: 5px 8px;
    min-width: 260px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
  }

  .chooser {
    position: relative;
  }

  .chooser summary {
    list-style: none;
  }

  .choices {
    position: absolute;
    z-index: 5;
    top: 34px;
    left: 0;
    width: 360px;
    max-height: 420px;
    overflow: auto;
    padding: 8px 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  }

  .choices label {
    display: flex;
    gap: 6px;
    font-size: 0.9em;
    padding: 2px 0;
  }

  .chart-title {
    font-size: 0.92rem;
    margin: 4px 0;
    color: var(--muted);
  }

  .scroll {
    overflow-x: auto;
  }

  .sort {
    border: none;
    background: none;
    font: inherit;
    font-weight: 600;
    color: inherit;
    cursor: pointer;
    padding: 0;
    text-align: inherit;
  }

  tbody tr {
    cursor: pointer;
  }

  tbody tr:hover {
    background: var(--bg);
  }

  tbody tr.on {
    background: var(--accent-soft);
  }

  td.text {
    min-width: 360px;
    max-width: 60ch;
  }

  .more {
    margin: 10px 0;
  }

  .muted {
    color: var(--muted);
  }

  .error {
    color: var(--danger);
  }
</style>

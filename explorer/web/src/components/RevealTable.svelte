<script lang="ts">
  import { api } from '../lib/api'
  import { invalidate } from '../lib/store'
  import { Index } from '../lib/data'
  import { axis, baseLayout, chrome, identityColor, type Layout, scheme } from '../lib/theme.svelte'
  import type { Dataset, Field, KeyRow } from '../lib/types'
  import Plot from './Plot.svelte'
  import RatingForm, { complete, type Draft } from './RatingForm.svelte'

  let {
    rows,
    dataset,
    sessionId,
    onchange,
  }: { rows: KeyRow[]; dataset: Dataset; sessionId: string; onchange: () => void } = $props()

  const idx = $derived(new Index(dataset))

  const dims = $derived(dataset.meta.rubric?.dimensions ?? [])
  const headline = $derived(dims.find((d) => d.headline) ?? dims[0])
  const human = $derived(rows[0]?.human_scorer)
  const scorers = $derived([
    ...dataset.scorers.filter((s) => s.id === human),
    ...dataset.scorers.filter((s) => s.id !== human && rows.some((r) => r.scorings[s.id])),
  ])
  const perScorerFacets = $derived(
    dataset.fields.filter((f) => f.per_scorer && f.kind === 'facet' && f.values),
  )

  function valueOf(field: Field, value: string | number | null | undefined) {
    return field.values?.find((v) => v.id === value)
  }

  const itemNumber = $derived(Object.fromEntries(rows.map((r, n) => [r.slot, n + 1])))
  const repeats = $derived(
    rows
      .filter((r) => r.repeat_of)
      .map((r) => ({ first: rows.find((x) => x.slot === r.repeat_of)!, again: r })),
  )

  /** Mean absolute difference between first and repeated ratings, per dimension. */
  function consistency(dim: string): number {
    const gaps = repeats.map(
      ({ first, again }) =>
        Math.abs((first.scorings[human]?.[dim] ?? NaN) - (again.scorings[human]?.[dim] ?? NaN)),
    )
    return gaps.reduce((a, b) => a + b, 0) / gaps.length
  }

  function fmt(v: number | undefined | null): string {
    return v === undefined || v === null ? '—' : v.toFixed(2)
  }

  // --- the results as a figure: every item's scores on one dimension, joined per item ---
  let dimId = $state('')
  const dim = $derived(dims.find((d) => d.id === dimId) ?? headline)

  const results = $derived.by(() => {
    void scheme.dark
    const c = chrome()
    const labels = rows.map((r, n) => `Item ${n + 1}` + (r.repeat_of ? ' (repeat)' : ''))
    const traces: Layout[] = [
      {
        type: 'scatter',
        mode: 'lines',
        x: rows.flatMap((r) => {
          const vs = scorers.map((s) => r.scorings[s.id]?.[dim.id]).filter((v): v is number => v != null)
          return [Math.min(...vs), Math.max(...vs), null]
        }),
        y: labels.flatMap((_, n) => [n, n, null]),
        line: { color: c.axis, width: 2 },
        hoverinfo: 'skip',
        showlegend: false,
      },
      // Each scorer sits a little above or below the row line, so equal scores never hide
      // one another.
      ...scorers.map((s, k) => ({
        type: 'scatter',
        mode: 'markers',
        name: s.id === human ? `${s.label} (you)` : s.label,
        x: rows.map((r) => r.scorings[s.id]?.[dim.id] ?? null),
        y: rows.map((_, n) => n + (k - (scorers.length - 1) / 2) * 0.22),
        text: rows.map(
          (r, n) =>
            `<b>${labels[n]}</b> · ${s.label} ${fmt(r.scorings[s.id]?.[dim.id])}` +
            (s.id === human && r.correction ? `<br>corrected after reveal: ${r.correction.reason}` : ''),
        ),
        hovertemplate: '%{text}<extra></extra>',
        marker: {
          color: identityColor(idx.entityOfScorer(s.id), idx.entities),
          size: 11,
          symbol: rows.map((r) => (s.id === human && r.correction ? 'circle-open' : 'circle')),
          line: { color: c.surface, width: 2 },
        },
      })),
    ]
    const layout = baseLayout({
      xaxis: axis({ title: { text: dim.label }, range: [dim.min - 0.03, dim.max + 0.03] }),
      yaxis: axis({
        autorange: 'reversed',
        showgrid: false,
        tickvals: labels.map((_, n) => n),
        ticktext: labels,
        zeroline: false,
      }),
      margin: { l: 110, r: 16, t: 48, b: 52 },
    })
    return { traces, layout, height: 110 + 26 * rows.length }
  })

  const consistencyChart = $derived.by(() => {
    void scheme.dark
    if (!repeats.length) return null
    const color = identityColor(idx.entityOfScorer(human), idx.entities)
    return {
      traces: [
        {
          type: 'bar',
          orientation: 'h',
          y: dims.map((d) => d.label),
          x: dims.map((d) => consistency(d.id)),
          text: dims.map((d) => `<b>${d.label}</b><br>mean difference ${fmt(consistency(d.id))} over ${repeats.length} repeats`),
          hovertemplate: '%{text}<extra></extra>',
          textposition: 'none',
          marker: { color, line: { color: chrome().surface, width: 2 } },
        },
      ],
      layout: baseLayout({
        xaxis: axis({ title: { text: 'Mean difference between your two ratings' }, rangemode: 'tozero' }),
        yaxis: axis({ autorange: 'reversed', showgrid: false }),
        bargap: 0.45,
        margin: { l: 110, r: 16, t: 24, b: 52 },
        showlegend: false,
      }),
    }
  })

  // --- typo corrections ---
  let correcting = $state<string | null>(null)
  let draft = $state<Draft>({ values: {}, recognised: false, note: '' })
  let reason = $state('')
  let saving = $state(false)
  let error = $state('')

  function startCorrection(r: KeyRow) {
    const mine = r.scorings[human] ?? {}
    draft = {
      values: Object.fromEntries(Object.entries(mine).map(([k, v]) => [k, String(v)])),
      recognised: r.recognised,
      note: r.note,
    }
    reason = ''
    error = ''
    correcting = r.slot
  }

  async function saveCorrection(slot: string) {
    const dimsOut = complete(draft, dims)
    if (!dimsOut || !reason.trim()) return
    saving = true
    try {
      await api.correct(sessionId, slot, { dims: dimsOut, reason })
      invalidate()
      correcting = null
      onchange()
    } catch (e) {
      error = (e as Error).message
    } finally {
      saving = false
    }
  }

  const DIRECTION: Record<string, string> = {
    lower: 'lower is better',
    neutral: 'not a quality measure',
  }
</script>

<section class="reveal">
  <h1>Results</h1>
  <p class="muted">
    Your ratings beside the models'. Each item now shows where it came from. Ratings are locked.
  </p>

  <div class="controls">
    <label class="control">
      Score
      <select bind:value={() => dim.id, (v) => (dimId = v)}>
        {#each dims as d (d.id)}<option value={d.id}>{d.label}</option>{/each}
      </select>
    </label>
  </div>
  <Plot data={results.traces} layout={results.layout} filename="{sessionId}-results" height={results.height} />
  <p class="muted small">
    Each row is one item; the grey line spans the scores it received. An open circle is a rating
    corrected after the reveal.
  </p>

  <table class="summary">
    <thead>
      <tr>
        <th>Item</th>
        <th>Where it came from</th>
        {#each scorers as s (s.id)}<th class="num">{s.label}</th>{/each}
        <th>Seen before</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as r, n (r.slot)}
        <tr>
          <td>{n + 1}</td>
          <td>
            {r.stratum_label ?? r.stratum ?? ''}
            {#if r.repeat_of}<span class="muted">· repeat of item {itemNumber[r.repeat_of]}</span>{/if}
          </td>
          {#each scorers as s (s.id)}
            <td class="num" class:you={s.id === human}>{fmt(r.scorings[s.id]?.[headline.id])}</td>
          {/each}
          <td>{r.recognised ? 'yes' : ''}{r.correction ? ' · corrected' : ''}</td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="muted small">Scores shown: {headline.label.toLowerCase()}. Open an item for every dimension.</p>

  {#if repeats.length}
    <section class="consistency">
      <h2>Your consistency</h2>
      <p class="muted">
        {repeats.length} items came back later, unmarked. How far your two ratings of the same item
        were apart is the yardstick for how big a gap between you and a model has to be to mean
        anything.
      </p>
      {#if consistencyChart}
        <Plot data={consistencyChart.traces} layout={consistencyChart.layout} filename="{sessionId}-consistency" height={320} />
      {/if}
      <table>
        <thead>
          <tr>
            <th>Dimension</th>
            <th class="num">Mean difference</th>
            {#each repeats as { first, again } (again.slot)}
              <th class="num">Items {itemNumber[first.slot]} → {itemNumber[again.slot]}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each dims as d (d.id)}
            <tr class:headline={d.id === headline.id}>
              <td>{d.label}</td>
              <td class="num">{fmt(consistency(d.id))}</td>
              {#each repeats as { first, again } (again.slot)}
                <td class="num">
                  {fmt(first.scorings[human]?.[d.id])} → {fmt(again.scorings[human]?.[d.id])}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  {#each rows as r, n (r.slot)}
    <details class="card">
      <summary>
        <strong>Item {n + 1}</strong>
        <span class="muted">{r.stratum_label ?? r.stratum ?? ''}</span>
      </summary>
      <blockquote>{r.text}</blockquote>
      {#if r.note}<p><em>Your note:</em> {r.note}</p>{/if}
      {#if r.correction}
        <p class="corrected">
          Corrected after the reveal: {r.correction.reason}. Was
          {Object.entries(r.correction.replaces).map(([k, v]) => `${dims.find((d) => d.id === k)?.label ?? k} ${fmt(v)}`).join(', ')}.
        </p>
      {/if}

      <table class="dims">
        <thead>
          <tr>
            <th>Dimension</th>
            {#each scorers as s (s.id)}<th class="num">{s.label}</th>{/each}
          </tr>
        </thead>
        <tbody>
          {#each dims as d (d.id)}
            <tr class:headline={d.id === headline.id}>
              <td>
                {d.label}
                {#if d.direction && DIRECTION[d.direction]}
                  <span class="muted small">({DIRECTION[d.direction]})</span>
                {/if}
              </td>
              {#each scorers as s (s.id)}
                <td class="num" class:you={s.id === human}>{fmt(r.scorings[s.id]?.[d.id])}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>

      {#each perScorerFacets as f (f.id)}
        <div class="facet">
          <span class="facet-name" title={f.description}>{f.label}</span>
          {#each Object.entries(r.per_scorer) as [scorer, values] (scorer)}
            {@const v = valueOf(f, values[f.id])}
            {#if v}
              <span class="chip" title={v.description}>
                {dataset.scorers.find((s) => s.id === scorer)?.label ?? scorer}: {v.label}
              </span>
            {/if}
          {/each}
        </div>
      {/each}

      {#if correcting === r.slot}
        <div class="correct">
          <h3>Correct a typo</h3>
          <p class="muted small">
            For a value you mistyped, not a change of mind: you have now seen the models' scores.
            The original stays in the log, and the corrected rating is marked wherever it is used.
          </p>
          <RatingForm dimensions={dims} bind:draft />
          <label class="reason">
            <span>What was the typo?</span>
            <input type="text" maxlength="500" bind:value={reason} placeholder="e.g. typed 0.2 for overall, meant 0.7" />
          </label>
          {#if error}<p class="error">{error}</p>{/if}
          <div class="actions">
            <button class="btn primary" disabled={saving || !reason.trim() || !complete(draft, dims)} onclick={() => saveCorrection(r.slot)}>
              Save correction
            </button>
            <button class="btn" onclick={() => (correcting = null)}>Cancel</button>
          </div>
        </div>
      {:else}
        <button class="btn" onclick={() => startCorrection(r)}>Correct a typo</button>
      {/if}
    </details>
  {/each}

  {#each perScorerFacets as f (f.id)}
    <section class="legend">
      <h2>{f.label}</h2>
      {#if f.description}<p class="muted">{f.description}</p>{/if}
      <dl>
        {#each f.values ?? [] as v (v.id)}
          <dt>{v.label}</dt>
          <dd>{v.description ?? ''}</dd>
        {/each}
      </dl>
    </section>
  {/each}
</section>

<style>
  .reveal h1 {
    font-size: 1.3rem;
    margin-bottom: 4px;
  }

  table {
    border-collapse: collapse;
    margin: 12px 0;
    background: var(--surface);
  }

  th,
  td {
    padding: 6px 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }

  th {
    font-weight: 600;
    font-size: 0.92em;
  }

  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .you {
    font-weight: 600;
    color: var(--accent);
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 14px;
    margin: 8px 0;
  }

  .card summary {
    cursor: pointer;
    display: flex;
    gap: 12px;
  }

  blockquote {
    margin: 10px 0;
    padding-left: 12px;
    border-left: 3px solid var(--accent);
  }

  .headline td {
    font-weight: 600;
  }

  .facet {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 6px 0;
  }

  .facet-name {
    font-weight: 600;
    text-decoration: underline dotted;
    cursor: help;
  }

  .chip {
    padding: 2px 10px;
    border-radius: 999px;
    background: var(--accent-soft);
    cursor: help;
  }

  .consistency {
    margin: 20px 0;
  }

  .consistency h2 {
    font-size: 1rem;
  }

  .corrected {
    padding: 6px 10px;
    border-left: 3px solid var(--muted);
    color: var(--muted);
    font-size: 0.92em;
  }

  .correct {
    margin-top: 10px;
    padding: 12px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
  }

  .correct h3 {
    font-size: 0.95rem;
  }

  .reason {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 10px;
  }

  .reason input {
    font: inherit;
    padding: 6px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }

  .btn.primary {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--surface);
  }

  .error {
    color: var(--danger);
  }

  .legend {
    margin-top: 24px;
    max-width: 80ch;
  }

  .legend h2 {
    font-size: 1rem;
  }

  dt {
    font-weight: 600;
    margin-top: 8px;
  }

  dd {
    margin: 2px 0 0 0;
    color: var(--muted);
  }

  .muted {
    color: var(--muted);
  }

  .small {
    font-size: 0.88em;
  }
</style>

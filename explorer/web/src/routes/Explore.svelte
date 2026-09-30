<script lang="ts">
  import { onDestroy } from 'svelte'
  import BivariateKey from '../components/BivariateKey.svelte'
  import ColorControls from '../components/ColorControls.svelte'
  import DetailPanel from '../components/DetailPanel.svelte'
  import Plot from '../components/Plot.svelte'
  import {
    centroid,
    cloudLayout,
    cloudTraces,
    labelTrace,
    lineageTrace,
    methodLabel,
    projectionChoices,
    resolveColoring,
  } from '../lib/cloud'
  import { colorOptions } from '../lib/colorby'
  import { fmt, Index } from '../lib/data'
  import { href } from '../lib/router.svelte'
  import { clearPick, pick, picked } from '../lib/selection.svelte'
  import { loadDataset, loadMeta } from '../lib/store'
  import { chrome, type Layout, scheme } from '../lib/theme.svelte'
  import type { Idea, Meta } from '../lib/types'

  // The selected idea lives in the address (#/explore/<id>), so any idea can be linked to.
  let { ideaId }: { ideaId?: string } = $props()

  let idx = $state<Index | null>(null)
  let meta = $state<Meta | null>(null)
  let error = $state('')
  Promise.all([loadDataset(), loadMeta()])
    .then(([ds, m]) => {
      idx = new Index(ds)
      meta = m
    })
    .catch((e) => (error = e.message))

  // --- view ---
  let method = $state('')
  let dims = $state(3)
  const choices = $derived(idx ? projectionChoices(idx) : null)
  const projectionId = $derived.by(() => {
    if (!choices) return undefined
    const m = method || (choices.methods.includes('umap') ? 'umap' : choices.methods[0])
    return choices.find(m, dims) ?? choices.find(m, choices.dims[0])
  })
  const proj = $derived(projectionId ? idx?.ds.projections?.[projectionId] : undefined)

  // --- layers: the values of one facet, added in order to watch the space fill ---
  const facets = $derived(idx ? idx.ds.fields.filter((f) => f.kind === 'facet' && !f.per_scorer && f.values) : [])
  let layerFieldId = $state('')
  const layerField = $derived(facets.find((f) => f.id === layerFieldId) ?? facets[0])
  const layerValues = $derived(layerField?.values ?? [])
  let layerOn = $state<Record<string, boolean>>({})
  const isOn = (v: string | number) => layerOn[String(v)] ?? true
  let faintOthers = $state(true)
  let layerTimer: ReturnType<typeof setInterval> | null = null

  function showFirst(k: number) {
    layerOn = Object.fromEntries(layerValues.map((v, i) => [String(v.id), i < k]))
  }
  function shownCount(): number {
    const on = layerValues.map((v) => isOn(v.id))
    const k = on.indexOf(false)
    return k === -1 ? layerValues.length : k
  }
  function addNext() {
    showFirst(Math.min(layerValues.length, shownCount() + 1))
  }
  function playLayers() {
    stopAll()
    showFirst(1)
    layerTimer = setInterval(() => {
      const k = shownCount()
      if (k >= layerValues.length) stopAll()
      else showFirst(k + 1)
    }, 1400)
  }

  // --- growth: a metric the dataset declares as a production order, replayed from its
  // first value ---
  const growthFields = $derived(
    idx ? idx.ds.fields.filter((f) => f.kind === 'metric' && !f.per_scorer && f.sequence) : [],
  )
  let growthFieldId = $state('')
  const growthField = $derived(growthFields.find((f) => f.id === growthFieldId) ?? growthFields[0])
  const growthRange = $derived.by(() => {
    if (!growthField || !idx) return null
    const vals = idx.ds.ideas.map((i) => i.metrics?.[growthField.id]).filter((v): v is number => typeof v === 'number')
    return { min: Math.min(...vals), max: Math.max(...vals) }
  })
  let growthLimit = $state<number | null>(null)
  const growthAt = $derived(growthLimit ?? growthRange?.max ?? 0)
  let growthTimer: ReturnType<typeof setInterval> | null = null
  function playGrowth() {
    if (!growthRange) return
    stopAll()
    growthLimit = growthRange.min
    growthTimer = setInterval(() => {
      if ((growthLimit ?? 0) >= growthRange!.max) stopAll()
      else growthLimit = (growthLimit ?? 0) + 1
    }, 1200)
  }

  function stopAll() {
    if (layerTimer) clearInterval(layerTimer)
    if (growthTimer) clearInterval(growthTimer)
    layerTimer = growthTimer = null
  }
  onDestroy(stopAll)

  // --- filters and search ---
  let query = $state('')
  let filterOff = $state<Record<string, Record<string, boolean>>>({})
  const filterCount = $derived(Object.values(filterOff).reduce((n, m) => n + Object.values(m).filter(Boolean).length, 0))
  function passesFilters(i: Idea): boolean {
    for (const [fid, off] of Object.entries(filterOff)) {
      const v = i.facets?.[fid]
      if (v !== undefined && v !== null && off[String(v)]) return false
    }
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      if (!i.text.toLowerCase().includes(q) && !(i.essence ?? '').toLowerCase().includes(q)) return false
    }
    return true
  }

  // --- colour ---
  const options = $derived(idx ? colorOptions(idx) : [])
  let primary = $state('')
  let secondary = $state('')
  let centre = $state<'median' | 'middle'>('median')
  let reverse = $state(false)
  const primaryId = $derived(primary || (layerField ? layerField.id : options[0]?.id))

  // --- clusters, lineage, selection ---
  const clustering = $derived(idx ? Object.values(idx.ds.clusterings ?? {})[0] : undefined)
  let clusterFocus = $state<number | null>(null)
  let clusterLabels = $state(false)
  let lineage = $state(false)
  const selected = $derived(ideaId ?? null)
  function select(id: string | null) {
    location.hash = href(id ? `/explore/${id}` : '/explore')
  }

  const view = $derived.by(() => {
    void scheme.dark
    if (!idx || !proj) return null
    const c = chrome()
    const passing = idx.ds.ideas.filter(passesFilters)
    const grown = (i: Idea) =>
      !growthField || typeof i.metrics?.[growthField.id] !== 'number' || (i.metrics![growthField.id] as number) <= growthAt
    const inLayer = (i: Idea) => !layerField || isOn(i.facets?.[layerField.id] ?? '')
    const inCluster = (i: Idea) => clusterFocus === null || clustering?.assignments[i.id] === clusterFocus
    const only = picked.current ? new Set(picked.current.ids) : null
    const inPick = (i: Idea) => !only || only.has(i.id)
    const focus = (i: Idea) => inLayer(i) && inCluster(i) && inPick(i)
    const shown = passing.filter((i) => grown(i) && focus(i))
    const context = faintOthers ? passing.filter((i) => grown(i) && !focus(i)) : []

    const p = options.find((o) => o.id === primaryId)
    if (!p) return null
    const coloring = resolveColoring(idx, shown, {
      primary: p,
      secondary: options.find((o) => o.id === secondary),
      centre,
      reverse,
    })
    const traces: Layout[] = cloudTraces(idx, proj, shown, coloring, [], context)
    const shownIds = new Set(shown.map((i) => i.id))
    if (lineage || selected) {
      const t = lineageTrace(proj, shown, shownIds, lineage ? undefined : (selected ?? undefined))
      if (t) traces.unshift(t)
    }
    if (clusterLabels && clustering) {
      const labels = clustering.clusters
        .map((cl) => {
          const members = shown.filter((i) => clustering.assignments[i.id] === cl.id).map((i) => i.id)
          const at = members.length >= 3 ? centroid(proj, members) : null
          return at ? { text: `${cl.id} · ${(cl.terms ?? []).slice(0, 2).join(', ')}`, at } : null
        })
        .filter((l): l is { text: string; at: number[] } => l !== null)
      traces.push(labelTrace(proj, labels))
    }
    if (selected && proj.coords[selected]) {
      const at = proj.coords[selected]
      const three = proj.dims === 3
      traces.push({
        type: three ? 'scatter3d' : 'scatter',
        mode: 'markers',
        name: 'Selected',
        showlegend: false,
        x: [at[0]],
        y: [at[1]],
        ...(three ? { z: [at[2]] } : {}),
        marker: { size: three ? 12 : 18, symbol: 'circle-open', color: c.primary, line: { width: 3, color: c.primary } },
        hoverinfo: 'skip',
      })
    }
    const layout = cloudLayout(proj, { uirevision: projectionId, legend: { orientation: 'h', x: 0, y: 1.02, yanchor: 'bottom', font: { color: c.secondary, size: 12 } } })
    return { traces, layout, coloring, shownIds: shown.map((i) => i.id), shown: shown.length, context: context.length, total: idx.ds.ideas.length }
  })

  const selectedIdea = $derived(selected && idx ? idx.ideas.get(selected) : undefined)
  const held = $derived(meta?.sessions.filter((s) => !s.revealed && s.held_back > 0) ?? [])
  const layerCounts = $derived.by(() => {
    const counts = new Map<string, number>()
    if (!idx || !layerField) return counts
    for (const i of idx.ds.ideas) {
      const v = String(i.facets?.[layerField.id] ?? '')
      counts.set(v, (counts.get(v) ?? 0) + 1)
    }
    return counts
  })
</script>

{#if error}
  <p class="error">Could not load the data: {error}</p>
{:else if !idx || !choices}
  <p class="muted">Loading…</p>
{:else}
  <div class="explore" class:with-detail={!!selectedIdea}>
    <aside class="side">
      {#each held as s (s.id)}
        <p class="held">{s.held_back} ideas held back until <b>{s.id}</b> is revealed.</p>
      {/each}

      <section>
        <h2>Space</h2>
        <div class="row">
          <span class="seg" role="group" aria-label="Layout method">
            {#each choices.methods as m (m)}
              <button class:on={(method || (choices.methods.includes('umap') ? 'umap' : choices.methods[0])) === m} onclick={() => (method = m)}>{methodLabel(m)}</button>
            {/each}
          </span>
          <span class="seg" role="group" aria-label="Dimensions">
            {#each choices.dims as d (d)}
              <button class:on={dims === d} onclick={() => (dims = d)}>{d}D</button>
            {/each}
          </span>
        </div>
        {#if proj?.params?.placed}
          <p class="note">Map fitted on {proj.params.fitted_on} ideas; {proj.params.placed} newer ones placed into it without moving the rest.</p>
        {/if}
        {#if proj?.method === 'pca' && proj.explained_variance}
          <p class="note">Axes explain {proj.explained_variance.map((v) => `${(v * 100).toFixed(1)}%`).join(', ')} of the variance.</p>
        {:else if proj?.method === 'umap'}
          <p class="note">UMAP keeps neighbours close but distorts distances; check a pattern in PCA before trusting it.</p>
        {/if}
      </section>

      {#if layerField}
        <section>
          <h2>Layers</h2>
          <label class="control">
            by
            <select bind:value={() => layerField.id, (v) => { layerFieldId = v; layerOn = {} }}>
              {#each facets as f (f.id)}<option value={f.id}>{f.label}</option>{/each}
            </select>
          </label>
          <ul class="checks">
            {#each layerValues as v (v.id)}
              <li>
                <label title={v.description}>
                  <input type="checkbox" checked={isOn(v.id)} onchange={(e) => (layerOn[String(v.id)] = e.currentTarget.checked)} />
                  {v.label} <span class="muted">{layerCounts.get(String(v.id)) ?? 0}</span>
                </label>
              </li>
            {/each}
          </ul>
          <div class="row">
            <button class="btn" onclick={() => showFirst(1)}>First only</button>
            <button class="btn" onclick={addNext}>Add next</button>
            <button class="btn" onclick={playLayers}>▶ Play</button>
            <button class="btn" onclick={() => { stopAll(); layerOn = {} }}>All</button>
          </div>
          <label class="control"><input type="checkbox" bind:checked={faintOthers} /> Show the rest faintly</label>
        </section>
      {/if}

      {#if growthField && growthRange}
        <section>
          <h2 title={growthField.description}>Growth by {growthField.label.toLowerCase()}</h2>
          {#if growthFields.length > 1}
            <select bind:value={() => growthField.id, (v) => (growthFieldId = v)}>
              {#each growthFields as f (f.id)}<option value={f.id}>{f.label}</option>{/each}
            </select>
          {/if}
          <div class="row">
            <input
              type="range"
              min={growthRange.min}
              max={growthRange.max}
              step="1"
              value={growthAt}
              oninput={(e) => { stopAll(); growthLimit = Number(e.currentTarget.value) }}
              aria-label="Show up to"
            />
            <span>up to {growthAt}</span>
            <button class="btn" onclick={playGrowth}>▶ Play</button>
          </div>
        </section>
      {/if}

      <section>
        <h2>Colour</h2>
        <div class="stack">
          <ColorControls {options} bind:primary={() => primaryId, (v) => (primary = v)} bind:secondary bind:centre bind:reverse />
        </div>
      </section>

      <section>
        <h2>Show</h2>
        <label class="control"><input type="checkbox" bind:checked={lineage} /> Lines from each idea to what it grew from</label>
        {#if clustering}
          <label class="control"><input type="checkbox" bind:checked={clusterLabels} /> Cluster labels</label>
        {/if}
      </section>

      <section>
        <h2>Filter {#if filterCount}<span class="muted">({filterCount} hidden)</span>{/if}</h2>
        <input class="search" type="search" placeholder="Search text and essence" bind:value={query} />
        {#each facets.filter((f) => f.id !== layerField?.id) as f (f.id)}
          <details>
            <summary title={f.description}>{f.label}</summary>
            <ul class="checks">
              {#each f.values ?? [] as v (v.id)}
                <li>
                  <label title={v.description}>
                    <input
                      type="checkbox"
                      checked={!filterOff[f.id]?.[String(v.id)]}
                      onchange={(e) => (filterOff[f.id] = { ...filterOff[f.id], [String(v.id)]: !e.currentTarget.checked })}
                    />
                    {v.label}
                  </label>
                </li>
              {/each}
            </ul>
          </details>
        {/each}
      </section>

      {#if clustering}
        <section>
          <h2>Clusters <span class="muted">({clustering.clusters.length})</span></h2>
          <p class="note">{clustering.label ?? clustering.method}. Click one to focus on it.</p>
          <ul class="clusters">
            {#each clustering.clusters as cl (cl.id)}
              <li>
                <button class:on={clusterFocus === cl.id} onclick={() => (clusterFocus = clusterFocus === cl.id ? null : cl.id)}>
                  <span class="num">{cl.size}</span> {(cl.terms ?? []).join(', ') || `cluster ${cl.id}`}
                </button>
              </li>
            {/each}
          </ul>
        </section>
      {/if}
    </aside>

    <section class="stage">
      {#if picked.current}
        <p class="pick">
          Showing <b>{picked.current.label}</b> ({picked.current.ids.length} ideas).
          <button class="btn" onclick={clearPick}>Show all</button>
        </p>
      {/if}
      {#if view}
        <p class="count">
          <button
            class="btn to-table"
            onclick={() => {
              pick(`${view.shown} ideas from Explore`, view.shownIds)
              location.hash = href('/table')
            }}>Open these in the table</button>
          {view.shown.toLocaleString()} of {view.total.toLocaleString()} ideas shown{#if view.context}, {view.context.toLocaleString()} faint{/if}.
          {#if proj?.dims === 3}<span class="muted">Drag to rotate, scroll to zoom, click a point for details.</span>{:else}<span class="muted">Click a point for details.</span>{/if}
        </p>
        <Plot data={view.traces} layout={view.layout} filename="explore" height={760} viewKey={projectionId} onpointclick={(id) => select(id)} />
        {#if view.coloring.mode === 'blend'}
          <BivariateKey labels={view.coloring.labels} cuts={view.coloring.cuts} />
        {:else if view.coloring.mode === 'scale'}
          <p class="note">Blue is low, red is high{reverse ? ' (flipped)' : ''}; grey is {fmt(view.coloring.range.mid)} ({centre === 'median' ? 'the median' : 'the middle of the scale'}).</p>
        {/if}
      {/if}
    </section>

    {#if selectedIdea}
      <DetailPanel
        {idx}
        idea={selectedIdea}
        onselect={(id) => select(id)}
        onclose={() => select(null)}
        cluster={clustering && clustering.assignments[selectedIdea.id] >= 0
          ? clustering.clusters.find((c) => c.id === clustering.assignments[selectedIdea.id])
          : null}
      />
    {/if}
  </div>
{/if}

<style>
  .explore {
    display: grid;
    grid-template-columns: 290px minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .explore.with-detail {
    grid-template-columns: 290px minmax(0, 1fr) 380px;
  }

  @media (max-width: 1100px) {
    .explore,
    .explore.with-detail {
      grid-template-columns: 1fr;
    }
  }

  .side {
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-height: calc(100vh - 100px);
    overflow: auto;
    padding-right: 4px;
  }

  .side section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .side h2 {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .stack :global(.control) {
    display: flex;
    flex-wrap: wrap;
  }

  .stack :global(select) {
    max-width: 100%;
  }

  .checks {
    list-style: none;
    margin: 0;
    padding: 0;
    font-size: 0.92em;
  }

  .checks label {
    display: flex;
    gap: 6px;
    align-items: baseline;
    padding: 1px 0;
  }

  .search {
    font: inherit;
    padding: 5px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
  }

  details summary {
    cursor: pointer;
    font-size: 0.92em;
  }

  .clusters {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .clusters button {
    display: flex;
    gap: 8px;
    width: 100%;
    text-align: left;
    border: none;
    background: none;
    padding: 3px 4px;
    border-radius: 4px;
    font: inherit;
    font-size: 0.9em;
    color: var(--text);
    cursor: pointer;
  }

  .clusters button:hover {
    background: var(--surface);
  }

  .clusters button.on {
    background: var(--accent-soft);
    font-weight: 600;
  }

  .num {
    color: var(--muted);
    min-width: 2.5em;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .stage {
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 12px;
    min-width: 0;
  }

  .count {
    margin: 4px 0;
    font-size: 0.92em;
  }

  .to-table {
    float: right;
  }

  .pick {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 4px 0;
    padding: 6px 10px;
    border-radius: var(--radius);
    background: var(--accent-soft);
    font-size: 0.92em;
  }

  .note {
    color: var(--muted);
    font-size: 0.86em;
    margin: 2px 0;
  }

  .held {
    margin: 0;
    padding: 6px 10px;
    border-radius: var(--radius);
    background: var(--accent-soft);
    font-size: 0.88em;
  }

  .muted {
    color: var(--muted);
  }

  .error {
    color: var(--danger);
  }
</style>

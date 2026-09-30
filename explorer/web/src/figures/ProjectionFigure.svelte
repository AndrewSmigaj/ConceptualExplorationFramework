<script lang="ts">
  import BivariateKey from '../components/BivariateKey.svelte'
  import ColorControls from '../components/ColorControls.svelte'
  import Plot from '../components/Plot.svelte'
  import { cloudLayout, cloudTraces, type Mark, methodLabel, projectionChoices, resolveColoring } from '../lib/cloud'
  import { colorOptions } from '../lib/colorby'
  import { fmt, type Index } from '../lib/data'
  import { scheme } from '../lib/theme.svelte'
  import type { Preset, Ref } from '../lib/types'

  interface Spec {
    projections: string[]
    scorers?: string[]
    color: Ref
    marks?: Mark[]
  }

  let { idx, preset }: { idx: Index; preset: Preset } = $props()

  const spec = $derived(preset.spec as unknown as Spec)
  const choices = $derived(projectionChoices(idx, spec.projections))
  let method = $state('')
  let dims = $state(3)
  const projectionId = $derived(
    choices.find(method || choices.methods[0], dims) ?? choices.find(method || choices.methods[0], choices.dims[0]),
  )

  const options = $derived(colorOptions(idx))
  const presetColor = $derived.by(() => {
    const ref = spec.color
    const scorer = spec.scorers?.[0]
    return options.find(
      (o) => JSON.stringify(o.ref) === JSON.stringify(ref) && (o.scorer ?? undefined) === scorer,
    )?.id
  })
  let primary = $state('')
  let secondary = $state('')
  let centre = $state<'median' | 'middle'>('median')
  let reverse = $state(false)
  const primaryId = $derived(primary || presetColor || options[0]?.id)
  let showTable = $state(false)
  let plot = $state<Plot>()

  const figure = $derived.by(() => {
    void scheme.dark
    const proj = projectionId ? idx.ds.projections?.[projectionId] : undefined
    const p = options.find((o) => o.id === primaryId)
    if (!proj || !p) return null
    const s = options.find((o) => o.id === secondary)
    const coloring = resolveColoring(idx, idx.ds.ideas, { primary: p, secondary: s, centre, reverse })
    return {
      proj,
      coloring,
      traces: cloudTraces(idx, proj, idx.ds.ideas, coloring, spec.marks ?? []),
      layout: cloudLayout(proj),
    }
  })

  /** The same colouring as numbers: counts per group, per fifth, or per blend class. */
  const table = $derived.by(() => {
    if (!figure) return null
    const { coloring } = figure
    const ideas = idx.ds.ideas
    if (coloring.mode === 'group') {
      return {
        head: [coloring.label, 'Ideas'],
        rows: coloring.groups.map((g) => [g.label, String(ideas.filter((i) => coloring.groupOf(i) === g.key).length)]),
      }
    }
    if (coloring.mode === 'scale') {
      const vs = ideas.map(coloring.valueOf).filter((v): v is number => v !== null).sort((a, b) => a - b)
      const fifths = [0, 1, 2, 3, 4].map((q) => vs.slice(Math.floor((q * vs.length) / 5), Math.floor(((q + 1) * vs.length) / 5)))
      return {
        head: [`${coloring.label} (fifths)`, 'From', 'To', 'Ideas'],
        rows: fifths.map((f, q) => [`${q + 1} of 5`, fmt(f[0]), fmt(f[f.length - 1]), String(f.length)]),
      }
    }
    const count = (a: number, b: number) =>
      ideas.filter((i) => coloring.bandsOf(i)?.join(',') === `${a},${b}`).length
    const band = ['low', 'middle', 'high']
    return {
      head: [`${coloring.labels[0]} ↓ / ${coloring.labels[1]} →`, ...band],
      rows: [2, 1, 0].map((a) => [band[a], ...[0, 1, 2].map((b) => String(count(a, b)))]),
    }
  })
</script>

<div class="controls">
  {#if choices.methods.length > 1}
    <span class="seg" role="group" aria-label="Layout method">
      {#each choices.methods as m (m)}
        <button class:on={(method || choices.methods[0]) === m} onclick={() => (method = m)}>{methodLabel(m)}</button>
      {/each}
    </span>
  {/if}
  {#if choices.dims.length > 1}
    <span class="seg" role="group" aria-label="Dimensions">
      {#each choices.dims as d (d)}
        <button class:on={dims === d} onclick={() => (dims = d)}>{d}D</button>
      {/each}
    </span>
  {/if}
  <ColorControls {options} bind:primary={() => primaryId, (v) => (primary = v)} bind:secondary bind:centre bind:reverse />
  <span class="spacer"></span>
  <span class="tools">
    <label class="control"><input type="checkbox" bind:checked={showTable} /> Table</label>
    <button class="btn" onclick={() => plot?.download('png')}>PNG</button>
    <button class="btn" onclick={() => plot?.download('svg')}>SVG</button>
  </span>
</div>

{#if !figure}
  <p class="muted">This dataset has no layout yet. Run <code>explorer enrich</code>.</p>
{:else}
  <Plot bind:this={plot} data={figure.traces} layout={figure.layout} filename={preset.id} height={680} viewKey={projectionId} />
  {#if figure.proj.dims === 3}
    <p class="note">Drag to rotate, scroll to zoom, double-click to reset.</p>
  {/if}
  {#if figure.coloring.mode === 'blend'}
    <BivariateKey labels={figure.coloring.labels} cuts={figure.coloring.cuts} />
  {:else if figure.coloring.mode === 'group'}
    <dl class="legend-notes">
      {#each figure.coloring.groups as g (g.key)}
        {#if g.description}<dt>{g.label}</dt><dd>{g.description}</dd>{/if}
      {/each}
    </dl>
  {:else}
    <p class="note">
      Blue is low, red is high{reverse ? ' (flipped)' : ''}; grey is the centre, {fmt(figure.coloring.range.mid)}
      ({centre === 'median' ? 'the median' : 'the middle of the scale'}).
    </p>
  {/if}
  {#if showTable && table}
    <table class="data">
      <thead><tr>{#each table.head as h, k (k)}<th class:num={k > 0}>{h}</th>{/each}</tr></thead>
      <tbody>
        {#each table.rows as r, k (k)}
          <tr>{#each r as cell, j (j)}<td class:num={j > 0}>{cell}</td>{/each}</tr>
        {/each}
      </tbody>
    </table>
  {/if}
{/if}

<style>
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

  .note {
    color: var(--muted);
    font-size: 0.9em;
    margin: 4px 0;
  }

  .muted {
    color: var(--muted);
  }
</style>

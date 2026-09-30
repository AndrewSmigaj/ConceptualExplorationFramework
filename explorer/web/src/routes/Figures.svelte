<script lang="ts">
  import PairedFigure from '../figures/PairedFigure.svelte'
  import ProjectionFigure from '../figures/ProjectionFigure.svelte'
  import ScatterFigure from '../figures/ScatterFigure.svelte'
  import TableFigure from '../figures/TableFigure.svelte'
  import { Index } from '../lib/data'
  import { href } from '../lib/router.svelte'
  import { loadDataset, loadMeta } from '../lib/store'
  import type { Meta } from '../lib/types'

  let { presetId }: { presetId?: string } = $props()

  let idx = $state<Index | null>(null)
  let meta = $state<Meta | null>(null)
  let error = $state('')

  Promise.all([loadDataset(), loadMeta()])
    .then(([ds, m]) => {
      idx = new Index(ds)
      meta = m
    })
    .catch((e) => (error = e.message))

  const presets = $derived(idx?.ds.presets ?? [])
  const preset = $derived(presets.find((p) => p.id === presetId) ?? presets[0])
  const held = $derived(meta?.sessions.filter((s) => !s.revealed && s.held_back > 0) ?? [])
</script>

{#if error}
  <p class="error">Could not load the data: {error}</p>
{:else if !idx}
  <p class="muted">Loading…</p>
{:else if presets.length === 0}
  <p class="muted">This dataset defines no figures.</p>
{:else}
  <div class="layout">
    <nav class="list" aria-label="Figures">
      {#each presets as p (p.id)}
        <a href={href(`/figures/${p.id}`)} class:current={p.id === preset?.id}>{p.title}</a>
      {/each}
    </nav>

    <section class="figure">
      {#each held as s (s.id)}
        <p class="held">
          {s.held_back} ideas are held back until rating session <b>{s.id}</b> is revealed
          ({s.rated} of {s.total} rated), so figures here leave them out for now.
        </p>
      {/each}

      {#if preset}
        <h1>{preset.title}</h1>
        {#if preset.caption}<p class="caption">{preset.caption}</p>{/if}
        {#key preset.id}
          {#if preset.kind === 'projection'}
            <ProjectionFigure {idx} {preset} />
          {:else if preset.kind === 'scatter'}
            <ScatterFigure {idx} {preset} />
          {:else if preset.kind === 'table'}
            <TableFigure {idx} {preset} />
          {:else if preset.kind === 'paired'}
            <PairedFigure {idx} {preset} />
          {/if}
        {/key}
      {/if}
    </section>
  </div>
{/if}

<style>
  .layout {
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }

  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 1fr;
    }
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: sticky;
    top: 12px;
  }

  .list a {
    padding: 8px 10px;
    border-radius: var(--radius);
    color: var(--text);
    text-decoration: none;
    font-size: 0.93em;
  }

  .list a:hover {
    background: var(--surface);
  }

  .list a.current {
    background: var(--accent-soft);
    font-weight: 600;
  }

  .figure {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px 20px;
    min-width: 0;
  }

  .figure h1 {
    font-size: 1.15rem;
    margin-bottom: 4px;
  }

  .caption {
    color: var(--muted);
    margin: 0 0 4px;
    max-width: 90ch;
  }

  .held {
    margin: 0 0 12px;
    padding: 8px 12px;
    border-radius: var(--radius);
    background: var(--accent-soft);
    font-size: 0.92em;
  }

  .muted {
    color: var(--muted);
  }

  .error {
    color: var(--danger);
  }
</style>

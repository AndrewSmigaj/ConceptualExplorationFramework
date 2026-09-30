<script lang="ts">
  import { bivariateKey } from '../lib/colorby'
  import { fmt } from '../lib/data'
  import { scheme } from '../lib/theme.svelte'

  let { labels, cuts }: { labels: [string, string]; cuts: [[number, number], [number, number]] } = $props()

  // Row index is the first value's band, column the second's; draw the first rising upward.
  const grid = $derived((void scheme.dark, bivariateKey()))
  const bands = (c: [number, number]) => [`below ${fmt(c[0])}`, `${fmt(c[0])}–${fmt(c[1])}`, `${fmt(c[1])} and up`]
</script>

<div class="key" role="group" aria-label="Colour key for two values">
  <div class="body">
    <div class="ylabel">{labels[0]} →</div>
    <div class="grid">
      {#each [2, 1, 0] as a (a)}
        {#each [0, 1, 2] as b (b)}
          <span
            class="cell"
            style:background={grid[a][b]}
            title="{labels[0]}: {bands(cuts[0])[a]}; {labels[1]}: {bands(cuts[1])[b]}"
          ></span>
        {/each}
      {/each}
    </div>
  </div>
  <div class="xlabel">{labels[1]} →</div>
  <p class="bands">
    Thirds of each: {labels[0]} cut at {fmt(cuts[0][0])} and {fmt(cuts[0][1])}; {labels[1]} at
    {fmt(cuts[1][0])} and {fmt(cuts[1][1])}. Hover a square for its range.
  </p>
</div>

<style>
  .key {
    margin: 8px 0;
    display: inline-flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.85em;
    color: var(--muted);
  }

  .body {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .ylabel {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(3, 22px);
    gap: 2px;
  }

  .cell {
    width: 22px;
    height: 22px;
    cursor: help;
  }

  .xlabel {
    margin-left: 22px;
  }

  .bands {
    margin: 2px 0 0;
    max-width: 60ch;
  }
</style>

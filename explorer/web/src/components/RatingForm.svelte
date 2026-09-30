<script lang="ts" module>
  import type { Dimension, Dims } from '../lib/types'

  export interface Draft {
    values: Record<string, string>
    recognised: boolean
    note: string
  }

  /** The value as a number if it is complete and in range, else an explanation. */
  export function parse(raw: string, d: Dimension): number | string {
    if (raw.trim() === '') return 'Needed'
    const n = Number(raw)
    if (!Number.isFinite(n)) return 'Not a number'
    if (n < d.min || n > d.max) return `From ${d.min} to ${d.max}`
    return n
  }

  export function complete(draft: Draft, dims: Dimension[]): Dims | null {
    const out: Dims = {}
    for (const d of dims) {
      const v = parse(draft.values[d.id] ?? '', d)
      if (typeof v !== 'number') return null
      out[d.id] = v
    }
    return out
  }

  /** Eleven evenly spaced values across a dimension's range. */
  function steps(d: Dimension): number[] {
    return Array.from({ length: 11 }, (_, i) => Math.round((d.min + ((d.max - d.min) * i) / 10) * 1000) / 1000)
  }

  function short(v: number): string {
    return v === 0 || v === 1 ? String(v) : String(v).replace(/^0\./, '.')
  }
</script>

<script lang="ts">
  let {
    dimensions,
    draft = $bindable(),
    locked = false,
    descriptions = true,
    onsubmit,
  }: {
    dimensions: Dimension[]
    draft: Draft
    locked?: boolean
    /** Show each dimension's wording under its name. */
    descriptions?: boolean
    onsubmit?: () => void
  } = $props()

  let touched = $state<Record<string, boolean>>({})
  let form: HTMLDivElement
  let noteOpen = $state(false)

  function inputs(): HTMLInputElement[] {
    return [...form.querySelectorAll<HTMLInputElement>('input[type="number"]')]
  }

  // Enter moves to the next value; on the last one it submits.
  function onEnter(e: KeyboardEvent) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const all = inputs()
    const at = all.indexOf(e.currentTarget as HTMLInputElement)
    if (at < all.length - 1) all[at + 1].focus()
    else onsubmit?.()
  }

  function choose(d: Dimension, v: number, n: number) {
    draft.values[d.id] = String(v)
    touched[d.id] = true
    // Move on, so a row of clicks runs straight down the list.
    const next = inputs()[n + 1]
    next?.focus({ preventScroll: true })
  }
</script>

<div class="form" bind:this={form}>
  {#each dimensions as d, n (d.id)}
    {@const raw = draft.values[d.id] ?? ''}
    {@const check = parse(raw, d)}
    {@const showError = typeof check === 'string' && (touched[d.id] || raw !== '')}
    <div class="dim" class:invalid={showError} class:done={typeof check === 'number'}>
      <label class="name" for="dim-{d.id}">{d.label}</label>
      <div class="scale" role="group" aria-label="{d.label}: pick a value">
        {#each steps(d) as v (v)}
          <button
            type="button"
            tabindex="-1"
            class:on={raw !== '' && Number(raw) === v}
            disabled={locked}
            onclick={() => choose(d, v, n)}>{short(v)}</button
          >
        {/each}
      </div>
      <input
        id="dim-{d.id}"
        type="number"
        inputmode="decimal"
        min={d.min}
        max={d.max}
        step="0.05"
        placeholder="—"
        disabled={locked}
        value={raw}
        oninput={(e) => (draft.values[d.id] = e.currentTarget.value)}
        onblur={() => (touched[d.id] = true)}
        onkeydown={onEnter}
        aria-describedby={descriptions && d.description ? `desc-${d.id}` : undefined}
      />
      {#if showError}<span class="error">{check}</span>{/if}
      {#if descriptions && d.description}<p class="desc" id="desc-{d.id}">{d.description}</p>{/if}
    </div>
  {/each}

  <div class="extras">
    <label class="check">
      <input type="checkbox" disabled={locked} bind:checked={draft.recognised} />
      I have seen this one before
    </label>
    {#if noteOpen || draft.note}
      <textarea rows="2" disabled={locked} bind:value={draft.note} placeholder="A note to yourself (optional)"></textarea>
    {:else}
      <button type="button" class="link" onclick={() => (noteOpen = true)}>Add a note</button>
    {/if}
  </div>
</div>

<style>
  .form {
    display: flex;
    flex-direction: column;
  }

  .dim {
    display: grid;
    grid-template-columns: 136px 1fr 64px;
    align-items: center;
    gap: 4px 12px;
    padding: 10px 4px;
    border-bottom: 1px solid var(--border);
  }

  .name {
    font-weight: 600;
    white-space: nowrap;
  }

  .dim.done .name::after {
    content: ' ✓';
    color: var(--accent);
    font-weight: 400;
  }

  .scale {
    display: grid;
    grid-template-columns: repeat(11, minmax(0, 1fr));
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }

  .scale button {
    font: inherit;
    font-size: 0.85em;
    font-variant-numeric: tabular-nums;
    padding: 6px 0;
    border: none;
    border-left: 1px solid var(--border);
    background: var(--surface);
    color: var(--muted);
    cursor: pointer;
  }

  .scale button:first-child {
    border-left: none;
  }

  .scale button:hover:not(:disabled) {
    background: var(--accent-soft);
    color: var(--text);
  }

  .scale button.on,
  .scale button.on:hover:not(:disabled) {
    background: var(--accent);
    color: var(--surface);
    font-weight: 600;
  }

  input[type='number'] {
    width: 64px;
    padding: 5px 6px;
    font: inherit;
    font-variant-numeric: tabular-nums;
    text-align: center;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
  }

  .dim.invalid input[type='number'] {
    border-color: var(--danger);
  }

  .error {
    grid-column: 2 / 4;
    color: var(--danger);
    font-size: 0.85em;
  }

  .desc {
    grid-column: 2 / 4;
    margin: 0;
    color: var(--muted);
    font-size: 0.88em;
    line-height: 1.45;
  }

  .extras {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 20px;
    padding: 12px 4px 0;
  }

  .check {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  textarea {
    flex-basis: 100%;
    font: inherit;
    padding: 6px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
    resize: vertical;
  }

  .link {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font: inherit;
    cursor: pointer;
  }

  @media (max-width: 700px) {
    .dim {
      grid-template-columns: 1fr 64px;
    }

    .scale {
      grid-column: 1 / 3;
      grid-row: 2;
    }
  }
</style>

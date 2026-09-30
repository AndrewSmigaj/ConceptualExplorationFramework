<script lang="ts">
  import { tick, untrack } from 'svelte'
  import RatingForm, { complete, type Draft, parse } from '../components/RatingForm.svelte'
  import RevealTable from '../components/RevealTable.svelte'
  import { api } from '../lib/api'
  import { href } from '../lib/router.svelte'
  import { invalidate } from '../lib/store'
  import type { BlindView, Dataset, KeyRow, SavedRating } from '../lib/types'

  let props: { sessionId: string } = $props()
  // Captured once: the page is keyed by session, and an answer arriving after the
  // reader has navigated away must still know which session it belongs to.
  const sessionId = untrack(() => props.sessionId)

  // --- small conveniences remembered in this browser (never the ratings themselves) ---
  function remembered<T>(key: string, fallback: T): T {
    try {
      const v = localStorage.getItem(`explorer:${key}`)
      return v === null ? fallback : (JSON.parse(v) as T)
    } catch {
      return fallback
    }
  }
  function remember(key: string, value: unknown) {
    try {
      if (value === null) localStorage.removeItem(`explorer:${key}`)
      else localStorage.setItem(`explorer:${key}`, JSON.stringify(value))
    } catch {
      // private window or storage blocked: the page works without it
    }
  }

  let view = $state<BlindView | null>(null)
  let error = $state('')
  let index = $state(0)
  let drafts = $state<Record<string, Draft>>({})
  let saving = $state(false)
  let flash = $state('')
  let confirming = $state(false)
  let revealing = $state(false)
  let key = $state<KeyRow[] | null>(null)
  let dataset = $state<Dataset | null>(null)
  let showArgument = $state(remembered('rate:argument', true))
  let showDescriptions = $state(remembered('rate:descriptions', true))

  $effect(() => remember('rate:argument', showArgument))
  $effect(() => remember('rate:descriptions', showDescriptions))

  const draftKey = (slot: string) => `rate:${sessionId}:draft:${slot}`

  function fromSaved(saved: SavedRating | undefined): Draft {
    if (!saved) return { values: {}, recognised: false, note: '' }
    return {
      values: Object.fromEntries(Object.entries(saved.dims).map(([k, v]) => [k, String(v)])),
      recognised: saved.recognised,
      note: saved.note,
    }
  }

  async function load() {
    try {
      view = await api.blind(sessionId)
      for (const item of view.items) {
        // An unsaved draft from an earlier visit wins over the saved rating.
        drafts[item.slot] = view.revealed
          ? fromSaved(view.saved[item.slot])
          : remembered(draftKey(item.slot), fromSaved(view.saved[item.slot]))
      }
      const firstUnsaved = view.items.findIndex((i) => !view!.saved[i.slot])
      index = firstUnsaved === -1 ? 0 : firstUnsaved
      if (view.revealed) await loadKey()
    } catch (e) {
      error = (e as Error).message
    }
  }

  async function loadKey() {
    ;[key, dataset] = await Promise.all([api.key(sessionId), api.dataset()])
  }

  load()

  const item = $derived(view ? view.items[index] : null)
  const total = $derived(view?.items.length ?? 0)
  const savedCount = $derived(view ? view.items.filter((i) => view!.saved[i.slot]).length : 0)
  const allSaved = $derived(view !== null && savedCount === total)
  const dims = $derived(view?.rubric.dimensions ?? [])

  function isDirty(slot: string): boolean {
    if (!view) return false
    const saved = fromSaved(view.saved[slot])
    const draft = drafts[slot]
    if (!draft) return false
    return (
      draft.recognised !== saved.recognised ||
      draft.note !== saved.note ||
      dims.some((d) => (draft.values[d.id] ?? '') !== (saved.values[d.id] ?? ''))
    )
  }

  // Keep unsaved drafts in this browser so a reload loses nothing.
  $effect(() => {
    if (!view || view.revealed) return
    for (const it of view.items) {
      const d = drafts[it.slot]
      remember(draftKey(it.slot), d && isDirty(it.slot) ? $state.snapshot(d) : null)
    }
  })

  const ready = $derived(item && view ? complete(drafts[item.slot], dims) : null)
  const dirty = $derived(item ? isDirty(item.slot) : false)
  const missing = $derived(
    item ? dims.filter((d) => typeof parse(drafts[item.slot]?.values[d.id] ?? '', d) !== 'number').length : 0,
  )

  async function go(n: number) {
    if (!view) return
    index = Math.max(0, Math.min(view.items.length - 1, n))
    flash = ''
    await tick()
    document.querySelector<HTMLElement>('.work')?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }

  async function save(next: boolean) {
    if (!view || !item || !ready || saving) return
    saving = true
    error = ''
    try {
      const draft = drafts[item.slot]
      const saved = await api.rate(sessionId, item.slot, {
        dims: ready,
        recognised: draft.recognised,
        note: draft.note,
      })
      view.saved[item.slot] = { dims: saved.dims, recognised: saved.recognised, note: saved.note }
      drafts[item.slot] = fromSaved(view.saved[item.slot])
      flash = `Item ${index + 1} saved`
      if (next) {
        const after = view.items.findIndex((i, n) => n > index && !view!.saved[i.slot])
        const any = view.items.findIndex((i) => !view!.saved[i.slot])
        if (after !== -1) await go(after)
        else if (any !== -1) await go(any)
        await tick()
        document.querySelector<HTMLInputElement>('.panel input[type="number"]')?.focus({ preventScroll: true })
      }
    } catch (e) {
      error = (e as Error).message
    } finally {
      saving = false
    }
  }

  async function reveal() {
    revealing = true
    try {
      await api.reveal(sessionId)
      invalidate()
      view!.revealed = true
      for (const it of view!.items) remember(draftKey(it.slot), null)
      await loadKey()
    } catch (e) {
      error = (e as Error).message
    } finally {
      revealing = false
      confirming = false
    }
  }

  function onKey(e: KeyboardEvent) {
    if (!view || view.revealed) return
    const typing = (e.target as HTMLElement)?.closest('input, textarea, select')
    if ((e.altKey || !typing) && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      e.preventDefault()
      go(index + (e.key === 'ArrowRight' ? 1 : -1))
    }
  }
</script>

<svelte:window
  onkeydown={onKey}
  onbeforeunload={(e) => {
    if (view && !view.revealed && view.items.some((i) => isDirty(i.slot))) e.preventDefault()
  }}
/>

{#if error}<p class="error" role="alert">{error}</p>{/if}

{#if view && key && dataset}
  <RevealTable rows={key} {dataset} {sessionId} onchange={loadKey} />
  <p><a href={href('/')}>Back to the start</a></p>
{:else if view && item}
  <div class="rate">
    <header class="head">
      <div class="title">
        <h1>Blind rating</h1>
        <span class="muted">{sessionId}</span>
      </div>
      <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax={total} aria-valuenow={savedCount}>
        <div class="bar"><span style:width="{(100 * savedCount) / total}%"></span></div>
        <span class="count">{savedCount} of {total} saved</span>
      </div>
    </header>

    <nav class="strip" aria-label="Items">
      {#each view.items as it, n (it.slot)}
        <button
          class="tick"
          class:current={n === index}
          class:saved={!!view.saved[it.slot]}
          class:dirty={isDirty(it.slot)}
          aria-current={n === index}
          aria-label="Item {n + 1}{view.saved[it.slot] ? ', saved' : ''}"
          title="Item {n + 1}{view.saved[it.slot] ? ' · saved' : ''}{isDirty(it.slot) ? ' · unsaved changes' : ''}"
          onclick={() => go(n)}
        ></button>
      {/each}
    </nav>

    {#if allSaved}
      <section class="finish">
        {#if confirming}
          <p>
            <b>Reveal the results?</b> You will see where each item came from and how the models scored
            it. Your ratings are locked after this.
          </p>
          <div class="row">
            <button class="btn primary" disabled={revealing} onclick={reveal}>Reveal now</button>
            <button class="btn" onclick={() => (confirming = false)}>Not yet</button>
          </div>
        {:else}
          <p><b>All {total} rated.</b> You can still change any of them until you reveal.</p>
          <button class="btn primary" onclick={() => (confirming = true)}>Finish and reveal</button>
        {/if}
      </section>
    {/if}

    <div class="body" class:with-argument={showArgument}>
      {#if showArgument}
        <aside class="argument">
          <div class="aside-head">
            <h2>{view.context[0]?.title ?? 'Context'}</h2>
            <button class="link" onclick={() => (showArgument = false)}>Hide</button>
          </div>
          {#each view.context as doc (doc.id)}
            <div class="doc">{doc.text}</div>
          {/each}
        </aside>
      {/if}

      <main class="work">
        <div class="item-head">
          <span class="which">Item {index + 1} of {total}</span>
          {#if view.saved[item.slot]}<span class="badge">saved</span>{/if}
          <span class="spacer"></span>
          {#if !showArgument}
            <button class="link" onclick={() => (showArgument = true)}>Show {view.context[0]?.title.toLowerCase() ?? 'context'}</button>
          {/if}
          <button class="link" onclick={() => (showDescriptions = !showDescriptions)}>
            {showDescriptions ? 'Hide' : 'Show'} dimension wording
          </button>
        </div>

        <blockquote class="text">{item.text}</blockquote>

        <section class="panel">
          {#key item.slot}
            <!-- A fresh form per item, so one item's warnings never show on the next. -->
            <RatingForm
              dimensions={dims}
              bind:draft={drafts[item.slot]}
              descriptions={showDescriptions}
              onsubmit={() => save(true)}
            />
          {/key}
        </section>

        <footer class="actions">
          <button class="btn" disabled={index === 0} onclick={() => go(index - 1)} title="Previous item (←)">←</button>
          <button class="btn primary" disabled={!ready || saving || !dirty} onclick={() => save(true)}>Save and next</button>
          <button class="btn" disabled={!ready || saving || !dirty} onclick={() => save(false)}>Save</button>
          <button class="btn" disabled={index === total - 1} onclick={() => go(index + 1)} title="Next item (→)">→</button>
          <span class="status" aria-live="polite">
            {#if saving}Saving…
            {:else if dirty && missing}{missing} of {dims.length} still to fill
            {:else if dirty}Ready to save
            {:else if flash}✓ {flash}
            {:else if view.saved[item.slot]}Saved{/if}
          </span>
        </footer>

        <p class="hint">
          Click a value or type one; Enter moves down and saves at the end. ← → move between items when
          you are not typing (Alt+← → anywhere). Unsaved changes are kept if you leave or reload.
        </p>
        <details class="rubric">
          <summary>The full rubric, exactly as the models received it</summary>
          <pre>{view.rubric.text}</pre>
        </details>
      </main>
    </div>
  </div>
{:else if !error}
  <p class="muted">Loading…</p>
{/if}

<style>
  .rate {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 32px;
  }

  .title {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .title h1 {
    font-size: 1.25rem;
  }

  .progress {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 240px;
    max-width: 520px;
  }

  .bar {
    flex: 1;
    height: 8px;
    border-radius: 999px;
    background: var(--border);
    overflow: hidden;
  }

  .bar span {
    display: block;
    height: 100%;
    background: var(--accent);
    transition: width 0.3s;
  }

  .count {
    font-variant-numeric: tabular-nums;
    color: var(--muted);
    white-space: nowrap;
  }

  .strip {
    display: flex;
    gap: 3px;
  }

  .tick {
    flex: 1;
    max-width: 28px;
    height: 12px;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--surface);
    cursor: pointer;
  }

  .tick.saved {
    background: var(--accent);
    border-color: var(--accent);
    opacity: 0.55;
  }

  .tick.dirty {
    background: var(--accent-soft);
    border-style: dashed;
    border-color: var(--accent);
  }

  .tick.current {
    opacity: 1;
    outline: 2px solid var(--text);
    outline-offset: 1px;
  }

  .finish {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 20px;
    padding: 12px 16px;
    border-radius: var(--radius);
    background: var(--accent-soft);
  }

  .finish p {
    margin: 0;
  }

  .body {
    display: grid;
    grid-template-columns: minmax(0, 860px);
    justify-content: center;
    gap: 24px;
    align-items: start;
  }

  .body.with-argument {
    grid-template-columns: minmax(260px, 1fr) minmax(0, 860px);
    justify-content: stretch;
  }

  @media (max-width: 1000px) {
    .body.with-argument {
      grid-template-columns: 1fr;
    }
  }

  .argument {
    position: sticky;
    top: 12px;
    max-height: calc(100vh - 40px);
    overflow: auto;
    padding: 12px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .aside-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .aside-head h2 {
    font-size: 0.95rem;
  }

  .doc {
    white-space: pre-wrap;
    font-size: 0.92em;
    line-height: 1.6;
  }

  .work {
    min-width: 0;
    scroll-margin-top: 12px;
  }

  .item-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .which {
    font-weight: 600;
  }

  .badge {
    font-size: 0.8em;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--text);
  }

  .text {
    margin: 0 0 14px;
    padding: 16px 18px;
    font-size: 1.12rem;
    line-height: 1.65;
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: var(--radius);
  }

  .panel {
    padding: 4px 16px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .actions {
    position: sticky;
    bottom: 0;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 0;
    background: var(--bg);
    border-top: 1px solid var(--border);
  }

  .status {
    margin-left: 8px;
    color: var(--muted);
    font-size: 0.92em;
  }

  .hint {
    color: var(--muted);
    font-size: 0.85em;
    margin: 6px 0;
  }

  .btn {
    padding: 7px 14px;
  }

  .btn:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .btn.primary {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--surface);
    font-weight: 600;
  }

  .link {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font: inherit;
    font-size: 0.92em;
    cursor: pointer;
  }

  .row {
    display: flex;
    gap: 8px;
  }

  .rubric pre {
    white-space: pre-wrap;
    font-size: 0.86em;
    background: var(--surface);
    padding: 10px;
    border-radius: var(--radius);
  }

  .muted {
    color: var(--muted);
  }

  .error {
    color: var(--danger);
  }
</style>

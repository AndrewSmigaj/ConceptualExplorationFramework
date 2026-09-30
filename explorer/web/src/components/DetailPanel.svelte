<script lang="ts">
  import { fmt, type Index, snippet } from '../lib/data'
  import type { Idea } from '../lib/types'

  let {
    idx,
    idea,
    onselect,
    onclose,
    cluster,
  }: {
    idx: Index
    idea: Idea
    onselect: (id: string) => void
    onclose: () => void
    cluster?: { id: number; terms?: string[] } | null
  } = $props()

  const facets = $derived(
    Object.entries(idea.facets ?? {}).map(([id, v]) => ({
      field: idx.fields.get(id),
      label: idx.valueLabel(id, v),
      description: idx.valueDescription(id, v),
    })),
  )
  const metrics = $derived(
    Object.entries(idea.metrics ?? {}).map(([id, v]) => ({ field: idx.fields.get(id), v })),
  )
  const texts = $derived(Object.entries(idea.texts ?? {}).filter(([, v]) => v))
  const scorers = $derived(idx.ds.scorers.filter((s) => idea.scorings?.[s.id]))
  const perScorer = $derived(idx.ds.fields.filter((f) => f.per_scorer))
  const perScorerIds = $derived(Object.keys(idea.per_scorer ?? {}))
  const dims = $derived([...idx.dims.values()])
  const kids = $derived(idx.children.get(idea.id) ?? [])
  const edges = $derived(idx.edgesOf(idea.id).filter((e) => idx.ideas.has(e.other)))
  const DIRECTION: Record<string, string> = { lower: 'lower is better', neutral: 'not a quality measure' }

  function short(id: string): string {
    const i = idx.ideas.get(id)
    return i ? snippet(i.text, 110, 999) : id
  }
</script>

<aside class="panel" aria-label="Idea details">
  <header>
    <span class="muted small">{[idx.generatorLabel(idea.author ?? ''), idx.runLabel(idea.run)].filter(Boolean).join(' · ')}</span>
    <button class="close" aria-label="Close details" onclick={onclose}>×</button>
  </header>

  <blockquote>{idea.text}</blockquote>
  {#if idea.essence}<p class="essence"><span class="muted">Essence:</span> {idea.essence}</p>{/if}

  <dl class="kv">
    {#each facets as f (f.field?.id)}
      {#if f.field}
        <dt title={f.field.description}>{f.field.label}</dt>
        <dd title={f.description}>{f.label}</dd>
      {/if}
    {/each}
    {#each metrics as m (m.field?.id)}
      {#if m.field && m.v !== null}
        <dt title={m.field.description}>{m.field.label}</dt>
        <dd>{Number.isInteger(m.v) ? m.v : fmt(m.v)}</dd>
      {/if}
    {/each}
    {#if cluster}
      <dt>Cluster</dt>
      <dd>{cluster.id}{#if cluster.terms?.length} · {cluster.terms.join(', ')}{/if}</dd>
    {/if}
  </dl>

  {#if perScorerIds.length && perScorer.length}
    <h3>For each judge</h3>
    <table class="data">
      <thead>
        <tr><th></th>{#each perScorerIds as s (s)}<th>{idx.scorerLabel(s)}</th>{/each}</tr>
      </thead>
      <tbody>
        {#each perScorer as f (f.id)}
          <tr>
            <td title={f.description}>{f.label}</td>
            {#each perScorerIds as s (s)}
              {@const v = idea.per_scorer?.[s]?.[f.id] ?? null}
              <td title={f.kind === 'facet' ? idx.valueDescription(f.id, v) : undefined}>
                {f.kind === 'facet' ? idx.valueLabel(f.id, v) : fmt(v as number | null)}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}

  {#if scorers.length}
    <h3>Scores</h3>
    <table class="data">
      <thead>
        <tr><th></th>{#each scorers as s (s.id)}<th class="num">{s.label}</th>{/each}</tr>
      </thead>
      <tbody>
        {#each dims as d (d.id)}
          <tr class:headline={d.headline}>
            <td>
              {d.label}
              {#if d.direction && DIRECTION[d.direction]}<span class="muted small"> ({DIRECTION[d.direction]})</span>{/if}
            </td>
            {#each scorers as s (s.id)}
              <td class="num">{fmt(idea.scorings?.[s.id]?.dims?.[d.id])}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
    {#each scorers as s (s.id)}
      {@const sc = idea.scorings?.[s.id]}
      {#if sc?.flags?.length || sc?.note}
        <p class="muted small">{s.label}: {sc.note ?? sc.flags?.join(', ')}</p>
      {/if}
    {/each}
  {/if}

  {#each texts as [id, text] (id)}
    <h3 title={idx.fields.get(id)?.description}>{idx.fields.get(id)?.label ?? id}</h3>
    <p class="small">{text}</p>
  {/each}

  {#if idea.parents?.length}
    <h3>Grew from</h3>
    {#each idea.parents as p (p)}
      {#if idx.ideas.has(p)}
        <button class="link" onclick={() => onselect(p)}>{short(p)}</button>
      {:else}
        <p class="muted small">An idea not shown right now.</p>
      {/if}
    {/each}
  {/if}

  {#if kids.length}
    <h3>Grew into {kids.length} {kids.length === 1 ? 'idea' : 'ideas'}</h3>
    <div class="list">
      {#each kids.slice(0, 40) as k (k)}
        {#if idx.ideas.has(k)}<button class="link" onclick={() => onselect(k)}>{short(k)}</button>{/if}
      {/each}
      {#if kids.length > 40}<p class="muted small">and {kids.length - 40} more</p>{/if}
    </div>
  {/if}

  {#if edges.length}
    <h3>Checked against</h3>
    <div class="list">
      {#each edges as { edge, other } (edge.source + edge.target)}
        {@const kind = idx.edgeKinds.get(edge.kind)}
        <div class="edge">
          <span class="kind" class:same={kind?.duplicate} title={kind?.description}>{kind?.label ?? edge.kind}</span>
          {#if edge.weight !== undefined}<span class="muted small">similarity {fmt(edge.weight)}</span>{/if}
          <button class="link" onclick={() => onselect(other)}>{short(other)}</button>
          {#if edge.note}<p class="muted small">{edge.note}</p>{/if}
        </div>
      {/each}
    </div>
  {/if}
</aside>

<style>
  .panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 14px;
    max-height: calc(100vh - 100px);
    overflow: auto;
    font-size: 0.92em;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .close {
    border: none;
    background: none;
    font-size: 1.4rem;
    line-height: 1;
    color: var(--muted);
    cursor: pointer;
  }

  blockquote {
    margin: 8px 0;
    padding: 8px 10px;
    border-left: 3px solid var(--accent);
    font-size: 1.02rem;
    line-height: 1.5;
  }

  .essence {
    margin: 4px 0 10px;
  }

  .kv {
    display: grid;
    /* Long field names wrap in a capped column, so values always have room. */
    grid-template-columns: minmax(90px, 42%) minmax(0, 1fr);
    gap: 3px 10px;
    margin: 8px 0;
  }

  .kv dt {
    color: var(--muted);
  }

  .kv dd {
    margin: 0;
  }

  [title] {
    cursor: help;
  }

  h3 {
    font-size: 0.95em;
    margin: 14px 0 4px;
  }

  .headline td {
    font-weight: 600;
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .link {
    display: block;
    text-align: left;
    border: none;
    background: none;
    padding: 2px 0;
    color: var(--accent);
    font: inherit;
    cursor: pointer;
  }

  .link:hover {
    text-decoration: underline;
  }

  .edge {
    border-top: 1px solid var(--border);
    padding-top: 6px;
  }

  .kind {
    font-size: 0.85em;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--bg);
    margin-right: 6px;
  }

  .kind.same {
    background: var(--accent-soft);
  }

  .muted {
    color: var(--muted);
  }

  .small {
    font-size: 0.9em;
  }
</style>

<script lang="ts">
  import { api } from '../lib/api'
  import { href } from '../lib/router.svelte'
  import type { Meta } from '../lib/types'

  let meta = $state<Meta | null>(null)
  let error = $state('')

  api
    .meta()
    .then((m) => (meta = m))
    .catch((e) => (error = e.message))
</script>

{#if error}
  <p class="error">Could not reach the server: {error}</p>
{:else if meta}
  <section class="intro">
    <h1>{meta.title}</h1>
    {#if meta.description}<p class="muted">{meta.description}</p>{/if}
    <p class="muted">{meta.ideas.toLocaleString()} ideas</p>
  </section>

  <section class="card">
    <h2>Blind rating</h2>
    {#if meta.sessions.length === 0}
      <p class="muted">This dataset has no rating sessions.</p>
    {:else}
      <ul class="sessions">
        {#each meta.sessions as s (s.id)}
          <li>
            <span class="name">{s.id}</span>
            <span class="muted">
              {#if s.revealed}revealed{:else}{s.rated} of {s.total} rated{/if}
            </span>
            <a class="button" href={href(`/rate/${s.id}`)}>
              {#if s.revealed}See results{:else if s.rated > 0}Continue rating{:else}Start rating{/if}
            </a>
          </li>
        {/each}
      </ul>
      <p class="muted small">
        Rate before looking at anything else in the data. Seeing where ideas came from, or how
        the models scored them, would bias the ratings.
      </p>
    {/if}
  </section>
{:else}
  <p class="muted">Loading…</p>
{/if}

<style>
  .intro {
    margin-bottom: 24px;
  }

  .intro h1 {
    font-size: 1.4rem;
    margin-bottom: 6px;
  }

  .intro p {
    margin: 4px 0;
    max-width: 70ch;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
    max-width: 720px;
  }

  .card h2 {
    font-size: 1.05rem;
    margin-bottom: 10px;
  }

  .sessions {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .sessions li {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 0;
  }

  .name {
    font-family: var(--mono);
  }

  .button {
    margin-left: auto;
    padding: 6px 14px;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--surface);
    text-decoration: none;
    font-weight: 500;
  }

  .muted {
    color: var(--muted);
  }

  .small {
    font-size: 0.9em;
  }

  .error {
    color: var(--danger);
  }
</style>

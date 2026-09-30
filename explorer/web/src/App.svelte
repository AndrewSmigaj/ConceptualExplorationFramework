<script lang="ts">
  import { href, match, route } from './lib/router.svelte'
  import Explore from './routes/Explore.svelte'
  import Figures from './routes/Figures.svelte'
  import Home from './routes/Home.svelte'
  import Rate from './routes/Rate.svelte'
  import Runs from './routes/Runs.svelte'
  import Table from './routes/Table.svelte'

  const rate = $derived(match('/rate/:id'))
  const figure = $derived(match('/figures/:id'))
  const exploreIdea = $derived(match('/explore/:id'))
  const section = $derived(route.path.split('/')[1] ?? '')
</script>

<header class="bar">
  <a class="brand" href={href('/')}>Idea Explorer</a>
  <nav>
    <a href={href('/')} class:current={section === ''}>Start</a>
    <a href={href('/explore')} class:current={section === 'explore'}>Explore</a>
    <a href={href('/table')} class:current={section === 'table'}>Table</a>
    <a href={href('/figures')} class:current={section === 'figures'}>Figures</a>
    <a href={href('/runs')} class:current={section === 'runs'}>Runs</a>
  </nav>
</header>

<main>
  {#if rate}
    {#key rate.id}
      <Rate sessionId={rate.id} />
    {/key}
  {:else if route.path === '/explore' || exploreIdea}
    <Explore ideaId={exploreIdea?.id} />
  {:else if route.path === '/table'}
    <Table />
  {:else if route.path === '/runs'}
    <Runs />
  {:else if figure || route.path === '/figures'}
    <Figures presetId={figure?.id} />
  {:else if route.path === '/'}
    <Home />
  {:else}
    <p class="muted">Nothing here. <a href={href('/')}>Back to the start.</a></p>
  {/if}
</main>

<style>
  .bar {
    display: flex;
    align-items: center;
    gap: 28px;
    padding: 10px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  .brand {
    font-weight: 600;
    color: var(--text);
    text-decoration: none;
  }

  nav {
    display: flex;
    gap: 4px;
  }

  nav a {
    padding: 4px 10px;
    border-radius: 6px;
    color: var(--muted);
    text-decoration: none;
  }

  nav a:hover {
    color: var(--text);
  }

  nav a.current {
    color: var(--text);
    background: var(--accent-soft);
  }

  main {
    padding: 20px;
    max-width: 1500px;
    margin: 0 auto;
  }

  .muted {
    color: var(--muted);
  }
</style>

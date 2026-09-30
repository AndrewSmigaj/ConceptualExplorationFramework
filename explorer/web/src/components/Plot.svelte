<script lang="ts" module>
  // Plotly is large, so it loads on first use and never on the rating screen.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let plotly: Promise<any> | null = null
  function loadPlotly() {
    plotly ??= import('plotly.js-dist-min').then((m) => m.default)
    return plotly
  }
</script>

<script lang="ts">
  import { onDestroy, onMount } from 'svelte'
  import type { Layout } from '../lib/theme.svelte'

  let {
    data,
    layout,
    filename,
    height = 520,
    onpointclick,
    viewKey,
  }: {
    data: Layout[]
    layout: Layout
    filename: string
    height?: number
    /** Called with a point's customdata (an idea id) when it is clicked. */
    onpointclick?: (id: string) => void
    /** While this stays the same, re-renders keep the viewer's rotation, zoom and pan.
     * Change it (say, to a different layout) to start from the default view. */
    viewKey?: string
  } = $props()

  let el: HTMLDivElement
  let error = $state('')
  const config = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'toggleSpikelines'],
  }

  let listening = false
  let lastViewKey: string | undefined

  $effect(() => {
    const d = data
    const l: Layout = { ...layout, height }
    const key = viewKey
    loadPlotly()
      .then(async (Plotly) => {
        if (key !== undefined) {
          // Plotly would otherwise reapply the layout's camera on every render; carry the
          // viewer's own camera over while the view is the same one.
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const scene = (el as any)._fullLayout?.scene?._scene
          if (key === lastViewKey && scene && l.scene) l.scene = { ...l.scene, camera: scene.getCamera() }
          l.uirevision = key
          lastViewKey = key
        }
        await Plotly.react(el, d, l, config)
        if (!listening) {
          listening = true
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          ;(el as any).on('plotly_click', (e: any) => {
            const id = e?.points?.[0]?.customdata
            if (typeof id === 'string') onpointclick?.(id)
          })
        }
      })
      .catch((e) => (error = `Could not draw the chart: ${e.message}`))
  })

  // Plotly sizes itself on window resizes only; a panel opening beside it changes the
  // container without one, so watch the container itself.
  let observer: ResizeObserver | undefined
  onMount(() => {
    observer = new ResizeObserver(() => {
      plotly?.then((Plotly) => el && el.isConnected && Plotly.Plots.resize(el))
    })
    observer.observe(el)
  })

  onDestroy(() => {
    observer?.disconnect()
    plotly?.then((Plotly) => el && Plotly.purge(el))
  })

  export async function download(format: 'png' | 'svg') {
    const Plotly = await loadPlotly()
    await Plotly.downloadImage(el, { format, filename, height, width: el.clientWidth, scale: 2 })
  }
</script>

{#if error}<p class="error">{error}</p>{/if}
<div class="plot" bind:this={el} style:height="{height}px"></div>

<style>
  .plot {
    width: 100%;
    overflow: hidden;
  }

  .error {
    color: var(--danger);
  }
</style>

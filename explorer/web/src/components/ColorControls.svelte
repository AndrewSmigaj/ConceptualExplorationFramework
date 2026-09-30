<script lang="ts">
  import type { ColorOption } from '../lib/colorby'

  let {
    options,
    primary = $bindable(),
    secondary = $bindable(),
    centre = $bindable(),
    reverse = $bindable(),
  }: {
    options: ColorOption[]
    primary: string
    secondary: string
    centre: 'median' | 'middle'
    reverse: boolean
  } = $props()

  const current = $derived(options.find((o) => o.id === primary))
  const groups = $derived([
    { label: 'Groups', items: options.filter((o) => !o.numeric) },
    { label: 'Values (red–blue gradient)', items: options.filter((o) => o.numeric) },
  ])
</script>

<label class="control">
  Colour by
  <select bind:value={primary}>
    {#each groups as g (g.label)}
      {#if g.items.length}
        <optgroup label={g.label}>
          {#each g.items as o (o.id)}<option value={o.id}>{o.label}</option>{/each}
        </optgroup>
      {/if}
    {/each}
  </select>
</label>

{#if current?.numeric}
  <label class="control">
    Blend with
    <select bind:value={secondary}>
      <option value="">nothing</option>
      {#each options.filter((o) => o.numeric && o.id !== primary) as o (o.id)}
        <option value={o.id}>{o.label}</option>
      {/each}
    </select>
  </label>
  {#if !secondary}
    <label class="control">
      Centre
      <select bind:value={centre}>
        <option value="median">median</option>
        <option value="middle">middle of scale</option>
      </select>
    </label>
    <label class="control"><input type="checkbox" bind:checked={reverse} /> Flip colours</label>
  {/if}
{/if}

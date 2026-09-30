// Colours for the values of a categorical field:
//   ordered values        the one-hue ordinal ramp
//   up to eight values    the eight-slot reference palette, fixed per value
//   more than eight       the first seven, and the rest folded into grey "other"

import { categorical8, chrome, ordinalColors } from './theme.svelte'
import type { Field } from './types'

export function valueColors(field: Field | undefined): Map<string | number, string> {
  const values = field?.values ?? []
  const out = new Map<string | number, string>()
  if (field?.ordered) {
    const ramp = ordinalColors(values.length)
    values.forEach((v, i) => out.set(v.id, ramp[i]))
  } else {
    values.forEach((v, i) => out.set(v.id, i < 7 || values.length === 8 ? categorical8(i) : chrome().other))
  }
  return out
}

export function otherColor(): string {
  return chrome().other
}

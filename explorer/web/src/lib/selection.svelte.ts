// The current selection, shared by Explore, Table and Runs: a named set of idea ids.
// Explore can send what it shows to the Table; a run can be shown in Explore.

export interface Selection {
  label: string
  ids: string[]
}

export const picked = $state<{ current: Selection | null }>({ current: null })

export function pick(label: string, ids: string[]): void {
  picked.current = { label, ids }
}

export function clearPick(): void {
  picked.current = null
}

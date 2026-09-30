// The dataset and meta, fetched once and shared by every data screen.

import { api } from './api'
import type { Dataset, Meta } from './types'

let dataset: Promise<Dataset> | null = null
let meta: Promise<Meta> | null = null

export function loadDataset(): Promise<Dataset> {
  dataset ??= api.dataset().catch((e) => {
    dataset = null
    throw e
  })
  return dataset
}

export function loadMeta(): Promise<Meta> {
  meta ??= api.meta().catch((e) => {
    meta = null
    throw e
  })
  return meta
}

/** Forget the cached data, after anything that changes it (a reveal, a correction). */
export function invalidate(): void {
  dataset = null
  meta = null
}

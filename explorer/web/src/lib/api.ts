import type { BlindView, Dataset, Dims, KeyRow, Meta, SavedRating } from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // not JSON; keep the status text
    }
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

const session = (id: string) => `/sessions/${encodeURIComponent(id)}`

export const api = {
  meta: () => call<Meta>('/meta'),
  dataset: () => call<Dataset>('/dataset'),
  blind: (id: string) => call<BlindView>(session(id)),
  rate: (id: string, slot: string, rating: { dims: Dims; recognised: boolean; note: string }) =>
    call<SavedRating & { slot: string; at: string }>(
      `${session(id)}/ratings/${encodeURIComponent(slot)}`,
      { method: 'PUT', body: JSON.stringify(rating) },
    ),
  correct: (id: string, slot: string, body: { dims: Dims; reason: string }) =>
    call<{ slot: string; dims: Dims; at: string }>(
      `${session(id)}/corrections/${encodeURIComponent(slot)}`,
      { method: 'PUT', body: JSON.stringify(body) },
    ),
  reveal: (id: string) => call<KeyRow[]>(`${session(id)}/reveal`, { method: 'POST' }),
  key: (id: string) => call<KeyRow[]>(`${session(id)}/key`),
}

// Hash routing: #/ and #/rate/<session>. Works identically under Vite and the Python server.

function current(): string {
  return decodeURIComponent(location.hash.replace(/^#/, '')) || '/'
}

export const route = $state({ path: current() })

window.addEventListener('hashchange', () => {
  route.path = current()
})

export function href(path: string): string {
  return `#${path}`
}

/** Match a pattern like '/rate/:id' against the current path; returns the params or null. */
export function match(pattern: string, path: string = route.path): Record<string, string> | null {
  const want = pattern.split('/').filter(Boolean)
  const got = path.split('/').filter(Boolean)
  if (want.length !== got.length) return null
  const params: Record<string, string> = {}
  for (let i = 0; i < want.length; i++) {
    if (want[i].startsWith(':')) params[want[i].slice(1)] = got[i]
    else if (want[i] !== got[i]) return null
  }
  return params
}

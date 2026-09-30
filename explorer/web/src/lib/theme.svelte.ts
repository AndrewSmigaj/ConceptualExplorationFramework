// Chart colours and chrome. Every hex here is from the dataviz reference palette and
// was run through its validator (categorical first three slots all-pairs, and the
// three-step ordinal ramp, in both modes). Dark mode is its own set of steps, not a flip.

const media = window.matchMedia('(prefers-color-scheme: dark)')

export const scheme = $state({ dark: media.matches })
media.addEventListener('change', (e) => (scheme.dark = e.matches))

/** Identity colours: generators and human scorers, in a fixed order. */
const CATEGORICAL = {
  light: ['#2a78d6', '#eb6834', '#1baf7a'],
  dark: ['#3987e5', '#d95926', '#199e70'],
}

/** The full eight-slot reference palette, in its validated order. */
const CATEGORICAL_8 = {
  light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'],
  dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'],
}

export function categorical8(slot: number): string {
  return CATEGORICAL_8[mode()][slot] ?? CHROME[mode()].other
}

/** One blue ramp for ordered categories, light end nearest the surface in each mode. */
const ORDINAL = {
  light: ['#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281'],
  dark: ['#184f95', '#1c5cab', '#256abf', '#2a78d6', '#3987e5', '#5598e7', '#6da7ec', '#86b6ef', '#9ec5f4'],
}

const CHROME = {
  light: {
    surface: '#fcfcfb',
    primary: '#0b0b0b',
    secondary: '#52514e',
    muted: '#898781',
    grid: '#e1e0d9',
    axis: '#c3c2b7',
    border: 'rgba(11,11,11,0.10)',
    other: '#898781',
  },
  dark: {
    surface: '#1a1a19',
    primary: '#ffffff',
    secondary: '#c3c2b7',
    muted: '#898781',
    grid: '#2c2c2a',
    axis: '#383835',
    border: 'rgba(255,255,255,0.10)',
    other: '#898781',
  },
}

const mode = () => (scheme.dark ? 'dark' : 'light')

export function chrome() {
  return CHROME[mode()]
}

/** The colour of an identity, by its position in a fixed entity list. Never cycled. */
export function identityColor(entity: string, entities: string[]): string {
  const slot = entities.indexOf(entity)
  return CATEGORICAL[mode()][slot] ?? CHROME[mode()].other
}

/** n evenly spaced steps of the ordinal ramp, from the familiar end to the far end. */
export function ordinalColors(n: number): string[] {
  const ramp = ORDINAL[mode()]
  if (n <= 1) return [ramp[4]]
  return Array.from({ length: n }, (_, i) => ramp[Math.round((i * (ramp.length - 1)) / (n - 1))])
}

const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

// Plotly's layout is an open object; keep it loosely typed at this one boundary.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Layout = Record<string, any>

export function axis(extra: Layout = {}): Layout {
  const c = chrome()
  return {
    gridcolor: c.grid,
    gridwidth: 1,
    linecolor: c.axis,
    linewidth: 1,
    showline: true,
    zeroline: false,
    ticks: 'outside',
    tickcolor: c.axis,
    ticklen: 4,
    tickfont: { color: c.muted, size: 12 },
    title: { font: { color: c.secondary, size: 13 } },
    automargin: true,
    ...extra,
  }
}

export function baseLayout(extra: Layout = {}): Layout {
  const c = chrome()
  return {
    paper_bgcolor: c.surface,
    plot_bgcolor: c.surface,
    font: { family: FONT, color: c.secondary, size: 13 },
    margin: { l: 56, r: 16, t: 48, b: 52 },
    hovermode: 'closest',
    hoverlabel: {
      bgcolor: c.surface,
      bordercolor: c.axis,
      font: { family: FONT, color: c.primary, size: 12 },
      align: 'left',
    },
    legend: {
      orientation: 'h',
      x: 0,
      xanchor: 'left',
      y: 1.02,
      yanchor: 'bottom',
      font: { color: c.secondary, size: 12 },
      itemclick: 'toggle',
    },
    ...extra,
  }
}

// Types for the dataset contract (explorer/schema/dataset.schema.json) and the API.
// The schema is the authority; these mirror the parts the frontend reads.

export type Id = string

export interface Dimension {
  id: Id
  label: string
  description?: string
  min: number
  max: number
  direction?: 'higher' | 'lower' | 'neutral'
  headline?: boolean
}

export interface Rubric {
  id?: Id
  sha256?: string
  text: string
  dimensions: Dimension[]
}

export interface ContextDoc {
  id: Id
  title: string
  text: string
}

export interface FieldValue {
  id: string | number
  label: string
  description?: string
}

export interface Field {
  id: Id
  label: string
  description?: string
  kind: 'facet' | 'metric' | 'text'
  per_scorer?: boolean
  values?: FieldValue[]
  ordered?: boolean
  unit?: string
  /** Metrics only: whole numbers giving the order ideas were produced in. */
  sequence?: boolean
}

export interface Scorer {
  id: Id
  label: string
  kind: 'model' | 'human'
  generator?: Id
}

export type Dims = Record<Id, number>

export interface Scoring {
  dims: Dims | null
  ref?: string
  note?: string
  /** Caveats a view must show with the scoring, e.g. "corrected after reveal". */
  flags?: string[]
}

export interface Idea {
  id: Id
  text: string
  essence?: string
  author?: Id
  parents?: Id[]
  run?: Id
  facets?: Record<Id, string | number | null>
  metrics?: Record<Id, number | null>
  texts?: Record<Id, string | null>
  per_scorer?: Record<Id, Record<Id, string | number | null>>
  scorings?: Record<Id, Scoring>
}

/** A value on an idea. per_scorer and dim refs are read for a given scorer. */
export type Ref = { label?: string } & (
  | { metric: Id }
  | { field: Id }
  | { per_scorer: Id }
  | { dim: Id }
  | { dim_product: [Id, Id] }
)

/** Keys: a facet id, "author", or "metric:<id>" with an inclusive [low, high]. */
export type Where = Record<string, string | number | (string | number)[]>

export interface Preset {
  id: Id
  title: string
  caption?: string
  kind: 'projection' | 'scatter' | 'table' | 'paired'
  // The spec's shape depends on the kind; each figure component narrows it.
  spec: Record<string, unknown>
}

export interface Projection {
  label?: string
  method: string
  dims: 2 | 3
  params?: { fitted_on?: number; placed?: number; [key: string]: unknown }
  explained_variance?: number[]
  coords: Record<Id, number[]>
}

export interface Clustering {
  label?: string
  method: string
  assignments: Record<Id, number>
  clusters: { id: number; size: number; terms?: string[] }[]
}

export interface EdgeKind {
  id: Id
  label: string
  description?: string
  duplicate?: boolean
}

export interface Edge {
  kind: Id
  source: Id
  target: Id
  weight?: number
  note?: string
}

export interface Dataset {
  schema_version: number
  meta: {
    id: Id
    title: string
    description?: string
    context?: ContextDoc[]
    rubric?: Rubric
  }
  scorers: Scorer[]
  generators: { id: Id; label: string }[]
  fields: Field[]
  ideas: Idea[]
  runs?: { id: Id; label: string; status: string; author?: Id; facets?: Record<Id, string | number | null>; counts?: Record<string, number>; note?: string }[]
  edge_kinds?: EdgeKind[]
  edges?: Edge[]
  presets?: Preset[]
  projections?: Record<Id, Projection>
  clusterings?: Record<Id, Clustering>
}

// --- API shapes (explorer/server.py, explorer/sessions.py) ---

export interface SessionSummary {
  id: Id
  total: number
  rated: number
  revealed: boolean
  /** Ideas withheld from every data view until this session is revealed. */
  held_back: number
}

export interface Meta {
  id: Id
  title: string
  description: string
  ideas: number
  sessions: SessionSummary[]
}

export interface SavedRating {
  dims: Dims
  recognised: boolean
  note: string
}

/** What a rater may see: nothing that identifies an item or where it came from. */
export interface BlindView {
  session: Id
  revealed: boolean
  context: ContextDoc[]
  rubric: { text: string; dimensions: Dimension[] }
  items: { slot: string; text: string }[]
  saved: Record<string, SavedRating>
}

export interface KeyRow {
  slot: string
  idea: Id
  text: string
  /** Set on a silent repeat: the slot where the same idea was first shown. */
  repeat_of: string | null
  stratum: string | null
  stratum_label: string | null
  author: Id | null
  facets: Record<Id, string | number | null>
  per_scorer: Record<Id, Record<Id, string | number | null>>
  scorings: Record<Id, Dims | null>
  human_scorer: Id
  recognised: boolean
  note: string
  /** Set when the human's rating was corrected after the reveal. */
  correction: { reason: string; after_reveal: boolean; replaces: Dims; replaces_at: string } | null
}

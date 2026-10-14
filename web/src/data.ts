export type Category = 'factual' | 'numeric' | 'multi_hop' | 'temporal' | 'unanswerable'

export interface Config {
  name: string
  description: string
  chunking: string
  chunk_size: number
  chunk_overlap: number
  retriever: string
  k: number
  embed_model: string
  model: string
  pipeline: string
  retrieval_only: boolean
}

export interface Summary {
  questions: number
  retrieval_recall: number | null
  retrieval_hit: number | null
  retrieval_mrr: number | null
  accuracy?: number | null
  answerable_accuracy?: number | null
  correct_refusals?: number | null
  false_refusals?: number | null
  citation_validity?: number | null
  cites_gold?: number | null
  latency_p50_ms?: number | null
  latency_p95_ms?: number | null
  tokens_per_question?: number | null
}

export interface Step {
  agent: string
  detail: string
  output: string
  latency_ms: number
}

export interface QuestionResult {
  id: string
  category: Category
  answer?: string
  citations?: string[]
  retrieved_docs: string[]
  retrieved_chunks?: string[]
  latency_ms?: number
  prompt_tokens?: number
  output_tokens?: number
  steps?: Step[]
  correct?: boolean
  abstained?: boolean
  missing?: string[][]
  citations_valid?: boolean | null
  cites_gold?: boolean | null
  retrieval_recall?: number
  retrieval_hit?: boolean
  retrieval_mrr?: number
}

export interface IndexEntry {
  config: Config
  ran_at: string
  duration_s: number
  summary: Summary
  by_category: Record<string, Summary>
}

export interface Result extends IndexEntry {
  questions: QuestionResult[]
}

export interface Question {
  id: string
  category: Category
  question: string
  gold_docs: string[]
  expect?: string[][]
  note?: string
}

export interface Doc {
  id: string
  title: string
  type: string
  effective: string
  supersedes: string | null
  body: string
}

export const CATEGORIES: Category[] = ['factual', 'numeric', 'multi_hop', 'temporal', 'unanswerable']
export const CATEGORY_LABEL: Record<Category, string> = {
  factual: 'Factual', numeric: 'Numeric', multi_hop: 'Multi-hop', temporal: 'Latest version', unanswerable: 'Unanswerable',
}

const base = import.meta.env.BASE_URL
const cache = new Map<string, Promise<unknown>>()

function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(`${base}data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`)
      return r.json()
    }))
  }
  return cache.get(path) as Promise<T>
}

export const loadIndex = () => load<IndexEntry[]>('index.json')
export const loadResult = (name: string) => load<Result>(`results/${name}.json`)
export const loadQuestions = () => load<Question[]>('questions.json')
export const loadCorpus = () => load<Doc[]>('corpus.json')

export const isDemo = import.meta.env.VITE_DEMO === 'true'

export interface AskResponse {
  question: string
  answer: string
  citations: string[]
  retrieved_docs: string[]
  latency_ms: number
  tokens: number
  steps: Step[]
}

export async function ask(question: string, config: string): Promise<AskResponse> {
  const r = await fetch('/api/ask', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, config }),
  })
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `HTTP ${r.status}`)
  return r.json()
}

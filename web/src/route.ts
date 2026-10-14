import { useEffect, useState } from 'react'

export type Page = 'overview' | 'questions' | 'ask' | 'corpus'
const PAGES: Page[] = ['overview', 'questions', 'ask', 'corpus']

export interface Route {
  page: Page
  params: URLSearchParams
}

function parse(): Route {
  const [path, query = ''] = window.location.hash.replace(/^#\/?/, '').split('?')
  return { page: (PAGES as string[]).includes(path) ? (path as Page) : 'overview', params: new URLSearchParams(query) }
}

export function useRoute(): Route {
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const onChange = () => setRoute(parse())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export function navigate(page: Page, params: Record<string, string | undefined> = {}) {
  const q = new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => !!e[1])).toString()
  window.location.hash = `/${page}${q ? `?${q}` : ''}`
}

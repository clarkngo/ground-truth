import { BarChartOutlined, BookOutlined, GithubOutlined, MessageOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { App as AntApp, ConfigProvider, Grid, Layout, Menu, Space, Spin, Tag, Tooltip, Typography, theme } from 'antd'
import { useEffect, useState, type ReactNode } from 'react'
import { isDemo, loadCorpus, loadIndex, loadQuestions, type Doc, type IndexEntry, type Question } from './data'
import { navigate, useRoute, type Page } from './route'
import { Ask } from './views/Ask'
import { Corpus } from './views/Corpus'
import { Overview } from './views/Overview'
import { Questions } from './views/Questions'

const NAV: { page: Page; label: string; icon: ReactNode; subtitle: string }[] = [
  { page: 'overview', label: 'Overview', icon: <BarChartOutlined />, subtitle: 'Every experiment scored against the same ground-truth questions' },
  { page: 'questions', label: 'Questions', icon: <UnorderedListOutlined />, subtitle: 'Every answer, with its citations, sources and agent steps' },
  { page: 'ask', label: 'Ask', icon: <MessageOutlined />, subtitle: 'Ask your own question against the corpus' },
  { page: 'corpus', label: 'Corpus', icon: <BookOutlined />, subtitle: 'The fictional university documents the system answers from' },
]

function usePrefersDark() {
  const query = '(prefers-color-scheme: dark)'
  const [dark, setDark] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = (e: MediaQueryListEvent) => setDark(e.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])
  return dark
}

export default function App() {
  const dark = usePrefersDark()
  return (
    <ConfigProvider theme={{
      algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: { colorPrimary: '#2f5bd3', borderRadius: 6 },
      components: { Layout: { headerBg: '#111318', siderBg: dark ? '#141414' : '#ffffff' } },
    }}>
      <AntApp><Shell /></AntApp>
    </ConfigProvider>
  )
}

function Shell() {
  const { token } = theme.useToken()
  const route = useRoute()
  const screens = Grid.useBreakpoint()
  const [data, setData] = useState<{ index: IndexEntry[]; questions: Question[]; corpus: Doc[] }>()
  const [error, setError] = useState<string>()

  useEffect(() => {
    Promise.all([loadIndex(), loadQuestions(), loadCorpus()])
      .then(([index, questions, corpus]) => setData({ index, questions, corpus }))
      .catch((e) => setError(String(e)))
  }, [])

  const current = NAV.find((n) => n.page === route.page)!
  const view = !data ? (error ? <Typography.Text type="danger">Could not load results: {error}</Typography.Text> : <Spin />) : (() => {
    switch (route.page) {
      case 'overview': return <Overview index={data.index} />
      case 'questions': return <Questions key={route.params.toString()} index={data.index} questions={data.questions} params={route.params} />
      case 'ask': return <Ask index={data.index} />
      case 'corpus': return <Corpus key={route.params.get('doc') ?? ''} corpus={data.corpus} params={route.params} />
    }
  })()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Header style={{ height: 52, lineHeight: '52px', padding: '0 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <img src={`${import.meta.env.BASE_URL}favicon.svg`} width={26} height={26} alt="" />
        <span style={{ color: '#fff', fontWeight: 700, fontSize: 17 }}>Ground Truth</span>
        {screens.md && <span style={{ color: 'rgba(255,255,255,.55)', fontSize: 13 }}>RAG and agents, measured</span>}
        <span style={{ flex: 1 }} />
        <Space size={14}>
          {isDemo ? (
            <Tooltip title="Static build: recorded results from real runs. Live questions need the local model server.">
              <Tag color="orange" style={{ marginInlineEnd: 0 }}>Static demo</Tag>
            </Tooltip>
          ) : <Tag color="green" style={{ marginInlineEnd: 0 }}>Live</Tag>}
          <a href="https://github.com/clarkngo/ground-truth" aria-label="Source on GitHub" style={{ color: '#fff', fontSize: 18 }}><GithubOutlined /></a>
        </Space>
      </Layout.Header>
      <Layout>
        <Layout.Sider width={190} collapsedWidth={56} collapsed={!screens.xl} trigger={null}
          style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}>
          <Menu mode="inline" selectedKeys={[route.page]} onClick={({ key }) => navigate(key as Page)}
            style={{ borderInlineEnd: 'none', paddingTop: 8 }}
            items={NAV.map((n) => ({ key: n.page, icon: n.icon, label: n.label }))} />
        </Layout.Sider>
        <Layout.Content style={{ padding: 16, background: token.colorBgLayout, minWidth: 0 }}>
          <div style={{ maxWidth: 1320, margin: '0 auto' }}>
            <div style={{ marginBottom: 12 }}>
              <Typography.Title level={4} style={{ margin: 0 }}>{current.label}</Typography.Title>
              <Typography.Text type="secondary" style={{ fontSize: 13 }}>{current.subtitle}</Typography.Text>
            </div>
            {view}
          </div>
        </Layout.Content>
      </Layout>
    </Layout>
  )
}

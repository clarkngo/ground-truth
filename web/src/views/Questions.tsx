import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons'
import { Card, Col, Empty, Row, Segmented, Select, Space, Table, Tag, Timeline, Tooltip, Typography, theme } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  CATEGORIES, CATEGORY_LABEL, loadResult, type Category, type IndexEntry, type Question, type QuestionResult, type Result,
} from '../data'
import { secs } from '../format'
import { navigate } from '../route'

type Outcome = 'all' | 'wrong' | 'changed'

function Verdict({ r }: { r?: QuestionResult }) {
  if (!r || r.correct === undefined) return <Typography.Text type="secondary">—</Typography.Text>
  return r.correct
    ? <Tag icon={<CheckCircleFilled />} color="success">correct</Tag>
    : <Tag icon={<CloseCircleFilled />} color="error">{r.abstained ? 'refused' : 'wrong'}</Tag>
}

/** Answer text with [doc-id] citations rendered as tags: green if gold, red if never retrieved. */
function AnswerText({ r, gold }: { r: QuestionResult; gold: string[] }) {
  const parts = (r.answer ?? '').split(/(\[[a-z0-9][a-z0-9.\-, ]*\])/g)
  return (
    <div className="answer">
      {parts.map((p, i) => {
        const m = p.match(/^\[(.+)\]$/)
        if (!m) return <span key={i}>{p}</span>
        return m[1].split(',').map((id) => id.trim()).map((id) => {
          const retrieved = r.retrieved_docs.includes(id)
          const color = gold.includes(id) ? 'green' : retrieved ? 'blue' : 'red'
          return (
            <Tooltip key={`${i}-${id}`} title={!retrieved ? 'Cited but never retrieved' : gold.includes(id) ? 'Gold source' : 'Retrieved, not gold'}>
              <Tag color={color} style={{ marginInline: 2, cursor: 'pointer' }} onClick={() => navigate('corpus', { doc: id })}>{id}</Tag>
            </Tooltip>
          )
        })
      })}
    </div>
  )
}

function Side({ title, r, q }: { title: ReactNode; r?: QuestionResult; q: Question }) {
  const { token } = theme.useToken()
  if (!r) return <Card size="small" title={title}><Empty description="Not in this run" /></Card>
  return (
    <Card size="small" title={<Space>{title}<Verdict r={r} /></Space>}
      extra={<Typography.Text type="secondary" style={{ fontSize: 12 }}>{secs(r.latency_ms)} · {(r.prompt_tokens ?? 0) + (r.output_tokens ?? 0)} tokens</Typography.Text>}>
      <AnswerText r={r} gold={q.gold_docs} />
      {!!r.missing?.length && (
        <div style={{ marginTop: 8, fontSize: 12, color: token.colorError }}>
          Missing: {r.missing.map((g) => g.map((a) => a.replace(/^re:/, '')).join(' / ')).join(' and ')}
        </div>
      )}
      <div style={{ marginTop: 10, fontSize: 12 }}>
        <Typography.Text type="secondary">Retrieved: </Typography.Text>
        {r.retrieved_docs.map((d) => <Tag key={d} color={q.gold_docs.includes(d) ? 'green' : undefined} style={{ marginBottom: 4 }}>{d}</Tag>)}
      </div>
      {r.steps && r.steps.length > 1 && (
        <div style={{ marginTop: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>Agent steps</Typography.Text>
          <Timeline style={{ marginTop: 8 }} items={r.steps.map((s) => ({
            color: s.agent === 'planner' ? 'gray' : s.agent === 'synthesizer' ? 'green' : 'blue',
            children: (
              <div style={{ fontSize: 12 }}>
                <strong>{s.agent}</strong> · {s.detail} · {secs(s.latency_ms)}
                <div className="answer" style={{ color: token.colorTextSecondary, marginTop: 2 }}>{s.output}</div>
              </div>
            ),
          }))} />
        </div>
      )}
    </Card>
  )
}

export function Questions({ index, questions, params }: { index: IndexEntry[]; questions: Question[]; params: URLSearchParams }) {
  const runs = index.filter((e) => !e.config.retrieval_only).map((e) => e.config.name)
  const [runA, setRunA] = useState(params.get('run') ?? (runs.includes('baseline') ? 'baseline' : runs[0]))
  const [runB, setRunB] = useState<string | undefined>(params.get('compare') ?? undefined)
  const [category, setCategory] = useState<Category | 'all'>((params.get('category') as Category) ?? 'all')
  const [outcome, setOutcome] = useState<Outcome>('all')
  const [results, setResults] = useState<Record<string, Result>>({})

  useEffect(() => {
    for (const name of [runA, runB]) {
      if (name && !results[name]) loadResult(name).then((r) => setResults((prev) => ({ ...prev, [name]: r })))
    }
  }, [runA, runB, results])

  const byId = (name?: string) => new Map((name && results[name]?.questions || []).map((r) => [r.id, r]))
  const a = useMemo(() => byId(runA), [runA, results]) // eslint-disable-line react-hooks/exhaustive-deps
  const b = useMemo(() => byId(runB), [runB, results]) // eslint-disable-line react-hooks/exhaustive-deps

  const rows = questions.filter((q) => {
    if (category !== 'all' && q.category !== category) return false
    if (outcome === 'wrong') return a.get(q.id)?.correct === false || (runB && b.get(q.id)?.correct === false)
    if (outcome === 'changed') return !!runB && a.get(q.id)?.correct !== b.get(q.id)?.correct
    return true
  })

  if (runs.length === 0) return <Empty description="No end-to-end results yet." />

  const columns: ColumnsType<Question> = [
    { title: 'ID', dataIndex: 'id', width: 60, render: (id: string) => <span className="mono">{id}</span> },
    { title: 'Type', dataIndex: 'category', width: 120, render: (c: Category) => <Tag>{CATEGORY_LABEL[c]}</Tag> },
    { title: 'Question', dataIndex: 'question' },
    { title: runA, key: 'a', width: 110, render: (_, q) => <Verdict r={a.get(q.id)} /> },
    ...(runB ? [{ title: runB, key: 'b', width: 110, render: (_: unknown, q: Question) => <Verdict r={b.get(q.id)} /> }] : []),
  ]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <Space wrap size="middle">
          <Space size={6}>Run <Select value={runA} onChange={setRunA} style={{ width: 190 }} options={runs.map((r) => ({ value: r, label: r }))} /></Space>
          <Space size={6}>Compare with <Select allowClear placeholder="none" value={runB} onChange={setRunB} style={{ width: 190 }}
            options={runs.filter((r) => r !== runA).map((r) => ({ value: r, label: r }))} /></Space>
          <Select value={category} onChange={setCategory} style={{ width: 160 }}
            options={[{ value: 'all', label: 'All types' }, ...CATEGORIES.map((c) => ({ value: c, label: CATEGORY_LABEL[c] }))]} />
          <Segmented<Outcome> value={outcome} onChange={setOutcome}
            options={[{ value: 'all', label: 'All' }, { value: 'wrong', label: 'Wrong' }, { value: 'changed', label: 'Changed', disabled: !runB }]} />
          <Typography.Text type="secondary">{rows.length} questions</Typography.Text>
        </Space>
      </Card>
      <Table<Question>
        rowKey="id" size="small" columns={columns} dataSource={rows} pagination={{ pageSize: 25, size: 'small' }} scroll={{ x: 700 }}
        expandable={{
          expandedRowRender: (q) => (
            <Space orientation="vertical" style={{ width: '100%' }}>
              <div style={{ fontSize: 13 }}>
                <Typography.Text type="secondary">Ground truth: </Typography.Text>
                {q.expect ? q.expect.map((g) => g.map((x) => x.replace(/^re:/, '')).join(' / ')).map((g) => <Tag key={g}>{g}</Tag>)
                  : <Tag color="orange">should refuse: the corpus doesn't say</Tag>}
                {q.gold_docs.map((d) => <Tag key={d} color="green">{d}</Tag>)}
                {q.note && <Typography.Text type="secondary"> · {q.note}</Typography.Text>}
              </div>
              <Row gutter={12}>
                <Col xs={24} lg={runB ? 12 : 24}><Side title={runA} r={a.get(q.id)} q={q} /></Col>
                {runB && <Col xs={24} lg={12}><Side title={runB} r={b.get(q.id)} q={q} /></Col>}
              </Row>
            </Space>
          ),
        }}
      />
    </Space>
  )
}

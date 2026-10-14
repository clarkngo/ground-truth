import { Alert, Button, Card, Input, Select, Space, Tag, Timeline, Typography } from 'antd'
import { useState } from 'react'
import { ask, isDemo, type AskResponse, type IndexEntry } from '../data'
import { secs } from '../format'
import { navigate } from '../route'

const EXAMPLES = [
  'A student withdraws from a 5-credit undergraduate course in week 3 of Fall 2025. How much tuition is refunded?',
  'Is generative AI allowed on coursework by default?',
  'How much is a student parking permit?',
]

export function Ask({ index }: { index: IndexEntry[] }) {
  const runs = index.filter((e) => !e.config.retrieval_only).map((e) => e.config.name)
  const [config, setConfig] = useState(runs.includes('baseline') ? 'baseline' : runs[0])
  const [question, setQuestion] = useState(EXAMPLES[0])
  const [result, setResult] = useState<AskResponse>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)

  async function submit() {
    setLoading(true)
    setError(undefined)
    try {
      setResult(await ask(question, config))
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {isDemo && (
        <Alert type="warning" showIcon title="Live questions need the local model server"
          description={<>This static demo has no backend. Clone the repo, start Ollama and run <span className="mono">uv run gt serve</span> to
            ask your own questions, or browse <a onClick={() => navigate('questions')}>every recorded answer</a>.</>} />
      )}
      <Card size="small" title="Ask the Larkspur corpus">
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Input.TextArea value={question} onChange={(e) => setQuestion(e.target.value)} autoSize={{ minRows: 2, maxRows: 5 }} maxLength={500} />
          <Space wrap>
            {EXAMPLES.map((q) => <Tag key={q} style={{ cursor: 'pointer' }} onClick={() => setQuestion(q)}>{q.length > 60 ? `${q.slice(0, 60)}…` : q}</Tag>)}
          </Space>
          <Space wrap>
            <Select value={config} onChange={setConfig} style={{ width: 200 }} options={runs.map((r) => ({ value: r, label: r }))} />
            <Button type="primary" loading={loading} disabled={isDemo || question.trim().length < 3} onClick={submit}>Ask</Button>
          </Space>
        </Space>
      </Card>
      {error && <Alert type="error" showIcon title="Request failed" description={error} />}
      {result && (
        <Card size="small" title="Answer" extra={<Typography.Text type="secondary">{secs(result.latency_ms)} · {result.tokens} tokens</Typography.Text>}>
          <div className="answer">{result.answer}</div>
          <div style={{ marginTop: 10 }}>
            <Typography.Text type="secondary">Sources: </Typography.Text>
            {result.retrieved_docs.map((d) => <Tag key={d} color={result.citations.includes(d) ? 'green' : undefined}>{d}</Tag>)}
          </div>
          {result.steps.length > 1 && (
            <Timeline style={{ marginTop: 16 }} items={result.steps.map((s) => ({
              children: <div style={{ fontSize: 12 }}><strong>{s.agent}</strong> · {s.detail} · {secs(s.latency_ms)}<div className="answer">{s.output}</div></div>,
            }))} />
          )}
        </Card>
      )}
    </Space>
  )
}

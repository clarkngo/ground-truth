import { Alert, Card, Col, Empty, Progress, Row, Space, Statistic, Table, Tag, Tooltip, Typography, theme } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { CATEGORIES, CATEGORY_LABEL, type IndexEntry } from '../data'
import { pct, rateColor, secs } from '../format'
import { navigate } from '../route'

const BASELINE = 'baseline'

function Rate({ v, invert }: { v: number | null | undefined; invert?: boolean }) {
  return <span style={{ color: rateColor(v, invert), fontWeight: 600 }}>{pct(v)}</span>
}

/** Plain-language findings computed from the results, so they stay true when experiments are re-run. */
function findings(endToEnd: IndexEntry[]): string[] {
  const by = new Map(endToEnd.map((e) => [e.config.name, e]))
  const base = by.get(BASELINE)
  const out: string[] = []
  if (!base) return out
  const best = [...endToEnd].sort((a, b) => (b.summary.accuracy ?? 0) - (a.summary.accuracy ?? 0))[0]
  if (best) out.push(`Most accurate: ${best.config.name} at ${pct(best.summary.accuracy)} overall (${best.config.description}).`)
  const agent = by.get('agent')
  if (agent) {
    const a = agent.by_category.multi_hop?.accuracy, b = base.by_category.multi_hop?.accuracy
    const slower = (agent.summary.latency_p50_ms ?? 0) / Math.max(1, base.summary.latency_p50_ms ?? 1)
    out.push(`Supervisor agent vs plain RAG on multi-hop questions: ${pct(b)} → ${pct(a)}, at ${slower.toFixed(1)}× the median latency and ${Math.round((agent.summary.tokens_per_question ?? 0) / Math.max(1, base.summary.tokens_per_question ?? 1) * 10) / 10}× the tokens.`)
  }
  const temporal = base.by_category.temporal?.accuracy
  if (temporal != null) out.push(`Baseline uses the current policy version on ${pct(temporal)} of "latest version" questions.`)
  const refusals = base.summary.correct_refusals
  if (refusals != null) out.push(`Baseline correctly refuses ${pct(refusals)} of unanswerable questions and wrongly refuses ${pct(base.summary.false_refusals)} of answerable ones.`)
  return out
}

export function Overview({ index }: { index: IndexEntry[] }) {
  const { token } = theme.useToken()
  if (index.length === 0) return <Empty description="No results yet. Run `uv run gt eval all` then `uv run gt export`." />

  const endToEnd = index.filter((e) => !e.config.retrieval_only)
    .sort((a, b) => (b.summary.accuracy ?? 0) - (a.summary.accuracy ?? 0))
  const retrieval = index.filter((e) => e.config.retrieval_only)
    .sort((a, b) => (b.summary.retrieval_mrr ?? 0) - (a.summary.retrieval_mrr ?? 0))
  const base = endToEnd.find((e) => e.config.name === BASELINE) ?? endToEnd[0]

  const columns: ColumnsType<IndexEntry> = [
    {
      title: 'Experiment', key: 'name', fixed: 'left', width: 220,
      render: (_, e) => (
        <div>
          <a onClick={() => navigate('questions', { run: e.config.name })} style={{ fontWeight: 600 }}>{e.config.name}</a>
          <div style={{ fontSize: 12, color: token.colorTextSecondary }}>{e.config.description}</div>
        </div>
      ),
    },
    { title: 'Model', key: 'model', width: 120, render: (_, e) => <span className="mono">{e.config.model}</span> },
    {
      title: 'Setup', key: 'setup', width: 170,
      render: (_, e) => (
        <Space size={4} wrap>
          <Tag color={e.config.pipeline === 'agent' ? 'purple' : 'blue'}>{e.config.pipeline}</Tag>
          <Tag>{e.config.retriever}</Tag>
          <Tag>{e.config.chunking}</Tag>
        </Space>
      ),
    },
    {
      title: 'Accuracy', key: 'acc', width: 150, sorter: (a, b) => (a.summary.accuracy ?? 0) - (b.summary.accuracy ?? 0),
      render: (_, e) => <Progress percent={Math.round((e.summary.accuracy ?? 0) * 100)} size="small" strokeColor={rateColor(e.summary.accuracy)} />,
    },
    { title: <Tooltip title="Unanswerable questions where the system said it didn't know">Correct refusals</Tooltip>, key: 'cr', width: 110, render: (_, e) => <Rate v={e.summary.correct_refusals} /> },
    { title: <Tooltip title="Answerable questions where the system wrongly said it didn't know">False refusals</Tooltip>, key: 'fr', width: 100, render: (_, e) => <Rate v={e.summary.false_refusals} invert /> },
    { title: <Tooltip title="Answers whose every citation was a retrieved source">Valid citations</Tooltip>, key: 'cv', width: 100, render: (_, e) => <Rate v={e.summary.citation_validity} /> },
    { title: <Tooltip title="Share of gold source documents retrieved">Retrieval recall</Tooltip>, key: 'rr', width: 100, render: (_, e) => <Rate v={e.summary.retrieval_recall} /> },
    { title: 'p50 latency', key: 'lat', width: 90, sorter: (a, b) => (a.summary.latency_p50_ms ?? 0) - (b.summary.latency_p50_ms ?? 0), render: (_, e) => secs(e.summary.latency_p50_ms) },
    { title: 'Tokens / q', key: 'tok', width: 90, render: (_, e) => e.summary.tokens_per_question ?? '—' },
  ]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      {base && (
        <Row gutter={[12, 12]}>
          {[
            { title: 'Accuracy', v: pct(base.summary.accuracy), c: rateColor(base.summary.accuracy), hint: `${base.summary.questions} ground-truth questions` },
            { title: 'Correct refusals', v: pct(base.summary.correct_refusals), c: rateColor(base.summary.correct_refusals), hint: 'says "I don\'t know" when it should' },
            { title: 'Valid citations', v: pct(base.summary.citation_validity), c: rateColor(base.summary.citation_validity), hint: 'cites only sources it retrieved' },
            { title: 'Median latency', v: secs(base.summary.latency_p50_ms), c: token.colorText, hint: `${base.config.model} on a laptop (M2, 16 GB)` },
          ].map((s) => (
            <Col key={s.title} xs={12} lg={6}>
              <Card size="small">
                <Statistic title={`Baseline · ${s.title}`} value={s.v} styles={{ content: { color: s.c } }} />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>{s.hint}</Typography.Text>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {findings(endToEnd).length > 0 && (
        <Alert type="info" showIcon title="What the experiments show"
          description={<ul style={{ margin: 0, paddingLeft: 18 }}>{findings(endToEnd).map((f) => <li key={f}>{f}</li>)}</ul>} />
      )}

      <Card size="small" title="Experiments" extra={<Typography.Text type="secondary" style={{ fontSize: 12 }}>Click an experiment to see every answer</Typography.Text>}>
        <Table<IndexEntry> rowKey={(e) => e.config.name} size="small" columns={columns} dataSource={endToEnd}
          pagination={false} scroll={{ x: 1250 }} />
      </Card>

      <Card size="small" title="Accuracy by question type">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'separate', borderSpacing: 3, fontSize: 13, minWidth: 640 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '4px 8px' }}>Experiment</th>
                {CATEGORIES.map((c) => <th key={c} style={{ padding: '4px 8px', fontWeight: 500 }}>{CATEGORY_LABEL[c]}</th>)}
              </tr>
            </thead>
            <tbody>
              {endToEnd.map((e) => (
                <tr key={e.config.name}>
                  <td style={{ padding: '4px 8px', whiteSpace: 'nowrap' }}>{e.config.name}</td>
                  {CATEGORIES.map((c) => {
                    const v = e.by_category[c]?.accuracy
                    return (
                      <td key={c} onClick={() => navigate('questions', { run: e.config.name, category: c })}
                        style={{ cursor: 'pointer', textAlign: 'center', padding: '6px 10px', borderRadius: 4, color: '#fff', fontWeight: 600,
                          background: v == null ? token.colorFillSecondary : rateColor(v), opacity: v == null ? 1 : 0.35 + 0.65 * v }}>
                        {pct(v)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card size="small" title="Retrieval experiments (no LLM)"
        extra={<Typography.Text type="secondary" style={{ fontSize: 12 }}>Did the right source documents come back?</Typography.Text>}>
        <Table<IndexEntry> rowKey={(e) => e.config.name} size="small" pagination={false} dataSource={retrieval} scroll={{ x: 600 }}
          columns={[
            { title: 'Experiment', key: 'n', render: (_, e) => <><strong>{e.config.name}</strong><div style={{ fontSize: 12, color: token.colorTextSecondary }}>{e.config.description}</div></> },
            { title: 'k', key: 'k', width: 50, render: (_, e) => e.config.k },
            { title: 'Recall', key: 'r', width: 90, render: (_, e) => <Rate v={e.summary.retrieval_recall} /> },
            { title: 'Hit rate', key: 'h', width: 90, render: (_, e) => <Rate v={e.summary.retrieval_hit} /> },
            { title: 'MRR', key: 'm', width: 90, render: (_, e) => (e.summary.retrieval_mrr ?? 0).toFixed(3) },
          ]} />
      </Card>
    </Space>
  )
}

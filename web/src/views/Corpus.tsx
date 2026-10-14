import { Card, Col, Menu, Row, Tag, Typography } from 'antd'
import { useState, type ReactNode } from 'react'
import type { Doc } from '../data'
import { navigate } from '../route'

/** Just enough markdown for the corpus: headings, bullet lists, tables and bold text. */
function Markdown({ text }: { text: string }) {
  const out: ReactNode[] = []
  const lines = text.split('\n')
  const inline = (s: string) => s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : p))
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('# ')) out.push(<Typography.Title key={i} level={4}>{line.slice(2)}</Typography.Title>)
    else if (line.startsWith('## ')) out.push(<Typography.Title key={i} level={5} style={{ marginTop: 16 }}>{line.slice(3)}</Typography.Title>)
    else if (line.startsWith('|')) {
      const rows: string[][] = []
      while (i < lines.length && lines[i].startsWith('|')) {
        if (!/^\|[-| ]+\|$/.test(lines[i])) rows.push(lines[i].split('|').slice(1, -1).map((c) => c.trim()))
        i++
      }
      i--
      out.push(
        <table key={i} style={{ borderCollapse: 'collapse', margin: '8px 0', fontSize: 13 }}>
          <tbody>{rows.map((r, ri) => <tr key={ri}>{r.map((c, ci) => (
            <td key={ci} style={{ border: '1px solid rgba(128,128,128,.3)', padding: '4px 10px', fontWeight: ri === 0 ? 600 : 400 }}>{c}</td>
          ))}</tr>)}</tbody>
        </table>,
      )
    } else if (/^(-|\d+\.) /.test(line)) out.push(<div key={i} style={{ paddingLeft: 16 }}>• {inline(line.replace(/^(-|\d+\.) /, ''))}</div>)
    else if (line.trim()) out.push(<p key={i} style={{ margin: '4px 0' }}>{inline(line)}</p>)
  }
  return <div>{out}</div>
}

export function Corpus({ corpus, params }: { corpus: Doc[]; params: URLSearchParams }) {
  const [selected, setSelected] = useState(params.get('doc') ?? corpus[0]?.id)
  const doc = corpus.find((d) => d.id === selected)
  const types = [...new Set(corpus.map((d) => d.type))]
  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} md={8} lg={6}>
        <Card size="small" styles={{ body: { padding: 0 } }}>
          <Menu mode="inline" selectedKeys={selected ? [selected] : []} onClick={({ key }) => { setSelected(key); navigate('corpus', { doc: key }) }}
            items={types.map((t) => ({
              key: t, type: 'group', label: t,
              children: corpus.filter((d) => d.type === t).map((d) => ({ key: d.id, label: d.title })),
            }))} />
        </Card>
      </Col>
      <Col xs={24} md={16} lg={18}>
        {doc && (
          <Card size="small" title={<span className="mono">{doc.id}</span>}
            extra={<>{doc.supersedes && <Tag color="orange">supersedes {doc.supersedes}</Tag>}<Tag>effective {doc.effective}</Tag></>}>
            <Markdown text={doc.body} />
          </Card>
        )}
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
          Larkspur Institute of Technology is fictional. Every policy, price and date was written for this project.
        </Typography.Paragraph>
      </Col>
    </Row>
  )
}

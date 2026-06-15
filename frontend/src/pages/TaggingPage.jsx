import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Typography, Button, Space, message, Table, Tag, Select,
  Drawer, Form, Progress, Statistic, Divider, InputNumber,
} from 'antd'
import {
  ThunderboltOutlined, RobotOutlined, RocketOutlined, EditOutlined,
  HistoryOutlined, ReloadOutlined, SafetyOutlined,
} from '@ant-design/icons'
import { getTaggingStats, getTaggingResults, triggerTagging, getTaggingTaskStatus,
         manualUpdateTagging, getTaggingHistory } from '../services/taggingService'
import { getFinanceCategories } from '../services/standardService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography

const METHOD_LABELS = { rule_engine: '规则引擎', ai: 'AI辅助', manual: '人工', hybrid: '混合', compliance_matrix: '合规矩阵' }
const DATA_LEVEL_CONFIG = {
  core: { color: 'red', label: '核心数据' },
  important: { color: 'orange', label: '重要数据' },
  sensitive: { color: 'gold', label: '敏感一般' },
  normal: { color: 'green', label: '常规一般' },
}

export default function TaggingPage() {
  const { hasRole } = useAuth()
  const canEdit = hasRole('data_admin', 'admin')

  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [filters, setFilters] = useState({ page: 1, page_size: 20 })
  const [taskId, setTaskId] = useState(null)
  const [taskRunning, setTaskRunning] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingField, setEditingField] = useState(null)
  const [history, setHistory] = useState([])
  const [categories, setCategories] = useState([])       // finance categories for edit
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [res, s] = await Promise.all([
        getTaggingResults(filters),
        getTaggingStats(),
      ])
      setData(res)
      setStats(s)
    } catch { message.error('加载数据失败') }
    finally { setLoading(false) }
  }, [filters])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    getFinanceCategories().then(setCategories).catch(() => {})
  }, [])

  // Pipeline trigger (old rule/AI engine)
  const runPipeline = async (mode) => {
    setTaskRunning(true)
    try {
      const { task_id } = await triggerTagging(mode)
      setTaskId(task_id)
      pollTask(task_id)
    } catch { message.error('启动失败'); setTaskRunning(false) }
  }

  // Compliance classify (new matrix engine)
  const runCompliance = async () => {
    setTaskRunning(true)
    try {
      const { runComplianceClassify } = await import('../services/standardService')
      const results = await runComplianceClassify(null)
      message.success(`金融合规分类完成: ${results.length} 个字段`)
      load()
    } catch (err) {
      message.error(err.response?.data?.detail || '合规分类失败')
    } finally { setTaskRunning(false) }
  }

  const pollTask = (tid) => {
    const interval = setInterval(async () => {
      try {
        const status = await getTaggingTaskStatus(tid)
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval)
          setTaskRunning(false)
          if (status.status === 'completed') {
            message.success(`打标完成: ${status.processed} 个字段, ${status.classified} 已分类, ${status.tiered} 已分级`)
          } else {
            message.error('打标失败: ' + JSON.stringify(status.errors))
          }
          load()
        }
      } catch { clearInterval(interval); setTaskRunning(false) }
    }, 1500)
  }

  // Manual edit
  const handleEdit = (record) => {
    setEditingField({ ...record })
    getTaggingHistory(record.id).then(setHistory).catch(() => setHistory([]))
    setDrawerOpen(true)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await manualUpdateTagging(editingField.id, {
        finance_category_id: editingField.finance_category_id,
        finance_data_level: editingField.finance_data_level,
        confidence: editingField.tagging_confidence || 1.0,
        comment: '人工修正',
      })
      message.success('已更新')
      setDrawerOpen(false)
      load()
    } catch (err) { message.error(err.response?.data?.detail || '操作失败') }
    finally { setSubmitting(false) }
  }

  const renderFinanceLevel = (v) => {
    const cfg = DATA_LEVEL_CONFIG[v]
    return cfg ? <Tag color={cfg.color}>{cfg.label}</Tag> : <Text type="secondary">-</Text>
  }

  const columns = [
    { title: '字段编码', dataIndex: 'field_code', key: 'field_code', width: 110 },
    { title: '字段名称', dataIndex: 'name', key: 'name', width: 120 },
    { title: '表名', dataIndex: 'table_name', key: 'table_name', width: 130, ellipsis: true },
    {
      title: '金融合规分类', dataIndex: 'finance_category_path', key: 'finance_category_path', width: 260, ellipsis: true,
      render: (v) => v ? <Text style={{ fontSize: 12 }}>{v}</Text> : <Text type="secondary">未分类</Text>,
    },
    {
      title: '合规级别', dataIndex: 'finance_data_level', key: 'finance_data_level', width: 100,
      render: renderFinanceLevel,
    },
    {
      title: '方法', dataIndex: 'tagging_method', key: 'tagging_method', width: 90,
      render: (v) => v ? <Tag>{METHOD_LABELS[v] || v}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '置信度', dataIndex: 'tagging_confidence', key: 'tagging_confidence', width: 90,
      render: (v) => v != null ? <Progress percent={Math.round(v * 100)} size="small" style={{ width: 60 }} /> : '-',
    },
    ...(canEdit ? [{
      title: '操作', key: 'actions', width: 80,
      render: (_, record) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>修正</Button>
      ),
    }] : []),
  ]

  return (
    <div>
      <Title level={3}>数据打标</Title>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}><Card><Statistic title="总字段" value={stats.total_fields} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="已分类" value={stats.classified_count} suffix={`/ ${stats.total_fields}`} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="覆盖率" value={stats.coverage_pct} suffix="%" /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="未分类" value={stats.unclassified_count} valueStyle={{ color: stats.unclassified_count > 0 ? '#cf1322' : undefined }} /></Card></Col>
        </Row>
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button type="primary" icon={<SafetyOutlined />} loading={taskRunning}
            onClick={runCompliance} disabled={taskRunning}>
            金融合规分类（矩阵判定）
          </Button>
          <Divider type="vertical" />
          <Button icon={<ThunderboltOutlined />} loading={taskRunning}
            onClick={() => runPipeline('compliance')} disabled={taskRunning}>
            合规矩阵
          </Button>
          <Button icon={<RobotOutlined />} loading={taskRunning}
            onClick={() => runPipeline('ai_only')} disabled={taskRunning}>
            AI辅助
          </Button>
          <Button icon={<RocketOutlined />} loading={taskRunning}
            onClick={() => runPipeline('full')} disabled={taskRunning}>
            全流水线（矩阵+AI）
          </Button>
          <Divider type="vertical" />
          <Select allowClear placeholder="合规级别" style={{ width: 120 }}
            value={filters.finance_data_level} onChange={(v) => setFilters(f => ({ ...f, finance_data_level: v, page: 1 }))}>
            {Object.entries(DATA_LEVEL_CONFIG).map(([k, cfg]) => <Select.Option key={k} value={k}>{cfg.label}</Select.Option>)}
          </Select>
          <Select allowClear placeholder="方法筛选" style={{ width: 120 }}
            value={filters.method} onChange={(v) => setFilters(f => ({ ...f, method: v, page: 1 }))}>
            {Object.entries(METHOD_LABELS).map(([k, v]) => <Select.Option key={k} value={k}>{v}</Select.Option>)}
          </Select>
          <Select allowClear placeholder="标状态" style={{ width: 120 }}
            value={filters.is_tagged} onChange={(v) => setFilters(f => ({ ...f, is_tagged: v, page: 1 }))}>
            <Select.Option value={true}>已打标</Select.Option>
            <Select.Option value={false}>未打标</Select.Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        pagination={{
          current: filters.page, pageSize: filters.page_size, total: data.total,
          onChange: (p, ps) => setFilters(f => ({ ...f, page: p, page_size: ps })),
          showTotal: (t) => `共 ${t} 条`,
        }}
      />

      <Drawer
        title={`修正打标: ${editingField?.field_code} ${editingField?.name}`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSubmit} loading={submitting}>保存</Button>
          </Space>
        }
      >
        {editingField && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text strong>金融合规分类:</Text>
              <Select
                style={{ width: '100%', marginTop: 4 }}
                value={editingField.finance_category_id}
                allowClear
                placeholder="选择67类金融标准分类"
                onChange={(v) => setEditingField(f => ({ ...f, finance_category_id: v }))}
              >
                {categories.filter(c => c.level === 3).map(c => (
                  <Select.Option key={c.id} value={c.id}>
                    <Tag color={DATA_LEVEL_CONFIG[c.ref_min_level]?.color} style={{ fontSize: 10 }}>
                      {DATA_LEVEL_CONFIG[c.ref_min_level]?.label}
                    </Tag>
                    {c.code.includes('BIZ_MKT') ? '  ' : ''}{c.name}
                  </Select.Option>
                ))}
              </Select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>合规数据级别:</Text>
              <Select
                style={{ width: '100%', marginTop: 4 }}
                value={editingField.finance_data_level}
                allowClear
                placeholder="选择合规四级"
                onChange={(v) => setEditingField(f => ({ ...f, finance_data_level: v }))}
              >
                {Object.entries(DATA_LEVEL_CONFIG).map(([k, cfg]) => (
                  <Select.Option key={k} value={k}><Tag color={cfg.color}>{cfg.label}</Tag></Select.Option>
                ))}
              </Select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>置信度:</Text>
              <InputNumber min={0} max={1} step={0.1} style={{ width: '100%', marginTop: 4 }}
                value={editingField.tagging_confidence}
                onChange={(v) => setEditingField(f => ({ ...f, tagging_confidence: v }))} />
            </div>

            <Divider />
            <Title level={5}><HistoryOutlined /> 打标历史</Title>
            {history.length === 0 ? (
              <Text type="secondary">暂无记录</Text>
            ) : (
              history.map(h => (
                <Card key={h.id} size="small" style={{ marginBottom: 8 }}>
                  <p><Tag>{h.action}</Tag> <Text type="secondary">{h.created_at}</Text></p>
                  {h.new_tier_level && <p>分级: {h.old_tier_level || '-'} → <Tag>{h.new_tier_level}</Tag></p>}
                  <p>方法: {METHOD_LABELS[h.tagging_method] || h.tagging_method} | 置信度: {h.new_confidence}</p>
                  {h.comment && <p><Text type="secondary">{h.comment}</Text></p>}
                </Card>
              ))
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}

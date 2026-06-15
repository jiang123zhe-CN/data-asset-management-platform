import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Typography, Button, Space, message, Popconfirm, Spin, Empty,
  Tabs, Table, Tag, Form, Input, Select, InputNumber, Descriptions, Alert, Statistic,
} from 'antd'
import {
  EditOutlined, SafetyOutlined, ApartmentOutlined, ThunderboltOutlined,
  WarningOutlined, CheckCircleOutlined,
} from '@ant-design/icons'
import {
  getFinanceCategories, getFinanceCategory, updateFinanceCategory,
  getGradingMatrix, getGradingRules,
  runComplianceClassify, getThresholdCheck,
} from '../services/standardService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography

// ── Grading level display config ──
const DATA_LEVEL_CONFIG = {
  core: { color: 'red', label: '核心数据', desc: '对国家安全造成特别严重/严重危害' },
  important: { color: 'orange', label: '重要数据', desc: '对经济运行/社会秩序/公共利益造成严重危害' },
  sensitive: { color: 'gold', label: '敏感一般数据', desc: '对组织/个人权益造成严重危害' },
  normal: { color: 'green', label: '常规一般数据', desc: '对组织/个人权益造成一般危害' },
}

const IMPACT_LABELS = {
  national_security: '国家安全', economy: '经济运行', social_order: '社会秩序',
  public_interest: '公共利益', org_rights: '组织权益', personal_rights: '个人权益',
}
const IMPACT_LEVEL_LABELS = {
  extremely_serious: '特别严重', serious: '严重', general: '一般',
}
const DATA_TYPE_LABELS = { business: '业务数据', user: '用户数据', enterprise: '企业数据' }

// ══════════════════════════════════════════════════════════════════
// Categories Tab — 67类金融标准分类
// ══════════════════════════════════════════════════════════════════

function CategoriesTab({ canEdit }) {
  const [flatList, setFlatList] = useState([])
  const [selectedL1, setSelectedL1] = useState(null)   // selected level-1 id
  const [selectedL2, setSelectedL2] = useState(null)   // selected level-2 id
  const [selectedId, setSelectedId] = useState(null)   // selected level-3 id (for detail)
  const [selectedCat, setSelectedCat] = useState(null)
  const [mode, setMode] = useState('view')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const loadTree = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getFinanceCategories()
      setFlatList(data)
    } catch {
      message.error('加载金融分类标准失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadTree() }, [loadTree])

  const loadDetail = async (id) => {
    try {
      const data = await getFinanceCategory(id)
      setSelectedCat(data)
      setMode('view')
    } catch {
      message.error('加载分类详情失败')
    }
  }

  // ── Data slices ──
  const l1List = flatList.filter(c => c.level === 1)
  const l2List = flatList.filter(c => c.level === 2 && c.parent_id === selectedL1)
  const l3List = flatList.filter(c => c.level === 3 && c.parent_id === selectedL2)

  // ── Selection handlers ──
  const handleL1Click = (id) => {
    setSelectedL1(id)
    setSelectedL2(null)
    setSelectedId(null)
    setSelectedCat(null)
  }

  const handleL2Click = (id) => {
    setSelectedL2(id)
    setSelectedId(null)
    setSelectedCat(null)
  }

  const handleL3Click = (id) => {
    setSelectedId(id)
    loadDetail(id)
  }

  // ── Build breadcrumb ──
  const l1Item = flatList.find(c => c.id === selectedL1)
  const l2Item = flatList.find(c => c.id === selectedL2)

  const handleEdit = () => {
    setMode('edit')
    form.setFieldsValue({
      name: selectedCat?.name,
      code: selectedCat?.code,
      data_type: selectedCat?.data_type,
      finance_product: selectedCat?.finance_product || undefined,
      ref_min_level: selectedCat?.ref_min_level,
      level_rationale: selectedCat?.level_rationale,
      appendix_desc: selectedCat?.appendix_desc,
      appendix_example: selectedCat?.appendix_example,
      sort_order: selectedCat?.sort_order,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSubmitting(true)
    try {
      await updateFinanceCategory(selectedId, values)
      message.success('分类已更新')
      loadDetail(selectedId)
      loadTree()
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => setMode('view')

  const renderLevelTag = (level) => {
    const cfg = DATA_LEVEL_CONFIG[level] || { color: 'default', label: level }
    return <Tag color={cfg.color}>{cfg.label}</Tag>
  }

  // ── Render a cascading picker column ──
  const renderColumn = (title, items, selectedId, onClick, placeholder, highlightColor = '#1677ff') => (
    <div style={{ flex: 1, minWidth: 150, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '8px 12px', fontWeight: 600, fontSize: 13, color: '#666', borderBottom: '1px solid #f0f0f0', background: '#fafafa', flexShrink: 0 }}>
        {title} <Text type="secondary" style={{ fontWeight: 400 }}>({items.length})</Text>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {items.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>{placeholder}</div>
        ) : (
          items.map(item => {
            const isSelected = item.id === selectedId
            const hasChildren = flatList.some(c => c.parent_id === item.id)
            return (
              <div
                key={item.id}
                onClick={() => onClick(item.id)}
                style={{
                  padding: '8px 12px', cursor: 'pointer',
                  background: isSelected ? '#e6f4ff' : 'transparent',
                  borderLeft: isSelected ? `3px solid ${highlightColor}` : '3px solid transparent',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  fontSize: 13,
                }}
              >
                <span>{item.name}</span>
                <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }} color={DATA_LEVEL_CONFIG[item.ref_min_level]?.color}>
                    {DATA_LEVEL_CONFIG[item.ref_min_level]?.label}
                  </Tag>
                  {hasChildren && <Text type="secondary" style={{ fontSize: 11 }}>{'>'}</Text>}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )

  return (
    <Row gutter={16}>
      <Col xs={24} md={14}>
        <Card
          title={<span><ApartmentOutlined /> 金融数据分类标准</span>}
          extra={
            <Text type="secondary" style={{ fontSize: 12 }}>
              {l1Item ? `${l1Item.name} ${l2Item ? `> ${l2Item.name}` : ''}` : '选择一级分类开始'}
            </Text>
          }
          bodyStyle={{ padding: 0 }}
          style={{ height: 'calc(100vh - 240px)' }}
        >
          {loading ? <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div> : flatList.length === 0 ? (
            <Empty description="暂无分类标准" style={{ marginTop: 60 }} />
          ) : (
            <div style={{ display: 'flex', height: '100%' }}>
              {renderColumn('一级分类', l1List, selectedL1, handleL1Click, '← 请选择', '#1677ff')}
              {renderColumn('二级分类', l2List, selectedL2, handleL2Click, selectedL1 ? '无二级分类' : '← 先选一级', '#722ed1')}
              {renderColumn('三级分类', l3List, selectedId, handleL3Click, selectedL2 ? '无三级分类' : '← 先选二级', '#fa8c16')}
            </div>
          )}
        </Card>
      </Col>
      <Col xs={24} md={10}>
        <Card
          title={mode === 'edit' ? '编辑分类' : '分类详情'}
          extra={
            mode === 'view' && selectedCat && canEdit && (
              <Button size="small" icon={<EditOutlined />} onClick={handleEdit}>编辑</Button>
            )
          }
          style={{ height: 'calc(100vh - 240px)', overflow: 'auto' }}
        >
          {mode === 'view' && selectedCat ? (
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="名称">{selectedCat.name}</Descriptions.Item>
              <Descriptions.Item label="编码"><Tag>{selectedCat.code}</Tag></Descriptions.Item>
              <Descriptions.Item label="层级">
                <Tag color={selectedCat.level === 1 ? 'blue' : selectedCat.level === 2 ? 'purple' : 'default'}>
                  {selectedCat.level === 1 ? '一级' : selectedCat.level === 2 ? '二级' : '三级'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数据类型">{DATA_TYPE_LABELS[selectedCat.data_type] || selectedCat.data_type}</Descriptions.Item>
              {selectedCat.finance_product && (
                <Descriptions.Item label="金融产品">{selectedCat.finance_product}</Descriptions.Item>
              )}
              <Descriptions.Item label="参考最低级别">{renderLevelTag(selectedCat.ref_min_level)}</Descriptions.Item>
              {l1Item && <Descriptions.Item label="所属一级">{l1Item.name}</Descriptions.Item>}
              {l2Item && <Descriptions.Item label="所属二级">{l2Item.name}</Descriptions.Item>}
              <Descriptions.Item label="标准依据">{selectedCat.standard_ref || '国信办通字〔2026〕2号'}</Descriptions.Item>
              {selectedCat.appendix_desc && (
                <Descriptions.Item label="附录描述">{selectedCat.appendix_desc}</Descriptions.Item>
              )}
              {selectedCat.appendix_example && (
                <Descriptions.Item label="数据示例">{selectedCat.appendix_example}</Descriptions.Item>
              )}
              {selectedCat.level_rationale && (
                <Descriptions.Item label="分级理由"><Text type="warning">{selectedCat.level_rationale}</Text></Descriptions.Item>
              )}
              <Descriptions.Item label="版本">{selectedCat.version}</Descriptions.Item>
            </Descriptions>
          ) : mode === 'view' && !selectedCat ? (
            <Empty description="点击三级分类查看详情" />
          ) : (
            <Form form={form} layout="vertical" onFinish={handleSubmit}>
              <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                <Input maxLength={200} />
              </Form.Item>
              <Form.Item name="code" label="编码">
                <Input disabled />
              </Form.Item>
              <Form.Item name="data_type" label="数据类型">
                <Select options={Object.entries(DATA_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
              </Form.Item>
              <Form.Item name="finance_product" label="金融产品">
                <Select allowClear>
                  <Select.Option value="stock">股票</Select.Option>
                  <Select.Option value="bond">债券</Select.Option>
                  <Select.Option value="fund">基金</Select.Option>
                  <Select.Option value="forex">外汇</Select.Option>
                  <Select.Option value="futures_option">期货期权</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name="ref_min_level" label="参考最低级别" rules={[{ required: true }]}>
                <Select options={Object.entries(DATA_LEVEL_CONFIG).map(([v, cfg]) => ({ value: v, label: cfg.label }))} />
              </Form.Item>
              <Form.Item name="level_rationale" label="分级理由">
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item name="appendix_desc" label="附录描述">
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item name="appendix_example" label="数据示例">
                <Input />
              </Form.Item>
              <Form.Item name="sort_order" label="排序" initialValue={0}>
                <InputNumber min={0} />
              </Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={submitting}>保存</Button>
                <Button onClick={handleCancel}>取消</Button>
              </Space>
            </Form>
          )}
        </Card>
      </Col>
    </Row>
  )
}

// ══════════════════════════════════════════════════════════════════
// Grading Tab — 分级矩阵 + 参考最低级别
// ══════════════════════════════════════════════════════════════════

function GradingTab() {
  const [matrix, setMatrix] = useState(null)
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [m, r] = await Promise.all([getGradingMatrix(), getGradingRules()])
      setMatrix(m)
      setRules(r)
    } catch {
      message.error('加载分级矩阵失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Build matrix table data
  const impactTargets = matrix?.impact_targets || []
  const impactLevels = matrix?.impact_levels || []
  const matrixData = matrix?.matrix || {}

  const matrixColumns = [
    { title: '影响对象 \\ 危害程度', dataIndex: 'target', key: 'target', width: 120, fixed: 'left',
      render: (v) => <Text strong>{IMPACT_LABELS[v] || v}</Text> },
    ...impactLevels.map(level => ({
      title: IMPACT_LEVEL_LABELS[level] || level,
      dataIndex: level,
      key: level,
      width: 140,
      render: (val) => {
        const cfg = DATA_LEVEL_CONFIG[val]
        return val ? <Tag color={cfg?.color} style={{ fontSize: 13, padding: '4px 12px' }}>{cfg?.label || val}</Tag> : <Tag>—</Tag>
      },
    })),
  ]

  const matrixRows = impactTargets.map(target => {
    const row = { key: target, target }
    impactLevels.forEach(level => {
      row[level] = matrixData[`${target}/${level}`] || null
    })
    return row
  })

  const rulesColumns = [
    { title: '影响对象', dataIndex: 'impact_target', key: 'impact_target', width: 120,
      render: (v) => IMPACT_LABELS[v] || v },
    { title: '危害程度', dataIndex: 'impact_level', key: 'impact_level', width: 100,
      render: (v) => IMPACT_LEVEL_LABELS[v] || v },
    { title: '判定级别', dataIndex: 'data_level', key: 'data_level', width: 130,
      render: (v) => {
        const cfg = DATA_LEVEL_CONFIG[v]
        return <Tag color={cfg?.color}>{cfg?.label || v}</Tag>
      }},
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
    { title: '说明', dataIndex: 'description', key: 'description', ellipsis: true },
  ]

  return (
    <div>
      <Alert
        message="分级判定方法"
        description="先确定数据涉及的影响对象（国家安全/经济运行/社会秩序/公共利益/组织权益/个人权益）和可能的危害程度（特别严重/严重/一般），然后在矩阵中查找对应的数据级别。实际级别 ≥ 参考最低级别（只能上调不能下调）。"
        type="info" showIcon style={{ marginBottom: 16 }}
      />

      <Title level={5}>分级判定矩阵（18格）</Title>
      <Table
        columns={matrixColumns}
        dataSource={matrixRows}
        pagination={false}
        loading={loading}
        bordered
        style={{ marginBottom: 24 }}
        scroll={{ x: 600 }}
      />

      <Title level={5}>矩阵规则明细（{rules.length} 条）</Title>
      <Table
        columns={rulesColumns}
        dataSource={rules}
        rowKey="id"
        pagination={false}
        loading={loading}
      />

      <Card title="关键原则" style={{ marginTop: 24 }}>
        <Descriptions column={1} size="small">
          <Descriptions.Item label="就高从严">
            一个数据集（表）的安全级别 = 该表所有字段中的最高级别。即使只有一个字段是核心/重要级别，整张表按最高级别保护。
          </Descriptions.Item>
          <Descriptions.Item label="级别不可降">
            实际分级必须 ≥ 附录A参考最低级别，只能上调不能下调。
          </Descriptions.Item>
          <Descriptions.Item label="30%变化阈值">
            核心数据和重要数据的条目数量或存储总量变化超过30%时，必须重新报送重要数据目录。
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// Classify Tab — 执行合规分类
// ══════════════════════════════════════════════════════════════════

function ClassifyTab() {
  const [results, setResults] = useState([])
  const [threshold, setThreshold] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadThreshold = useCallback(async () => {
    try {
      const t = await getThresholdCheck()
      setThreshold(t)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadThreshold() }, [loadThreshold])

  const handleClassify = async () => {
    setLoading(true)
    try {
      const data = await runComplianceClassify(null)
      setResults(data)
      message.success(`已完成 ${data.length} 个字段的合规分类分级`)
      loadThreshold()
    } catch (err) {
      message.error(err.response?.data?.detail || '分类执行失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '字段名', dataIndex: 'field_name', key: 'field_name', width: 120 },
    { title: '金融分类', dataIndex: 'finance_category_name', key: 'category', width: 160,
      render: (v, r) => v || <Tag>{r.finance_category_code}</Tag> },
    { title: '数据级别', dataIndex: 'finance_data_level', key: 'level', width: 130,
      render: (v) => {
        const cfg = DATA_LEVEL_CONFIG[v]
        return <Tag color={cfg?.color}>{cfg?.label || v}</Tag>
      }},
    { title: '参考最低级别', dataIndex: 'ref_min_level', key: 'ref', width: 130,
      render: (v) => {
        const cfg = DATA_LEVEL_CONFIG[v]
        return <Tag color={cfg?.color}>{cfg?.label || v}</Tag>
      }},
    { title: '升级', dataIndex: 'level_upgraded', key: 'upgraded', width: 80,
      render: (v, r) => v ? <Tag color="orange">已升级<Text type="secondary" style={{ fontSize: 11, display: 'block' }}>{r.upgrade_reason?.substring(0, 40)}</Text></Tag> : <Tag>—</Tag> },
    { title: '置信度', dataIndex: 'confidence', key: 'conf', width: 80,
      render: (v) => `${(v * 100).toFixed(0)}%` },
    { title: '方法', dataIndex: 'method', key: 'method', width: 120 },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="核心数据"
              value={threshold?.core_records || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="重要数据"
              value={threshold?.important_records || 0}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="关键数据合计"
              value={threshold?.total_critical || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="30%阈值"
              value={threshold?.threshold_30pct || 0}
              suffix="条"
              valueStyle={{ color: threshold?.total_critical > 0 && (threshold?.total_critical || 0) > (threshold?.threshold_30pct || 0) ? '#fa8c16' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={<span><ThunderboltOutlined /> 执行合规分类分级</span>}
        extra={
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleClassify} loading={loading}>
            执行分类分级
          </Button>
        }
      >
        <Alert
          message="按《金融信息服务数据分类分级指南》（国信办通字〔2026〕2号）对所有活跃字段执行四步判定"
          description="① 匹配67类三级标准分类 → ② 按影响对象×危害程度矩阵判定数据级别 → ③ 应用就高从严原则（表级继承）→ ④ 结果持久化到字段。"
          type="info" showIcon style={{ marginBottom: 16 }}
        />

        {results.length > 0 ? (
          <Table
            columns={columns}
            dataSource={results}
            rowKey="field_id"
            pagination={false}
            size="small"
            scroll={{ x: 900 }}
          />
        ) : (
          <Empty description="点击上方按钮，对所有活跃字段执行金融合规分类分级" />
        )}
      </Card>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// Main Page
// ══════════════════════════════════════════════════════════════════

export default function StandardPage() {
  const { hasRole } = useAuth()
  const canEdit = hasRole('system_admin', 'admin')

  const tabItems = [
    {
      key: 'categories',
      label: <span><ApartmentOutlined /> 分类标准</span>,
      children: <CategoriesTab canEdit={canEdit} />,
    },
    {
      key: 'grading',
      label: <span><SafetyOutlined /> 分级矩阵</span>,
      children: <GradingTab />,
    },
    {
      key: 'classify',
      label: <span><ThunderboltOutlined /> 执行分类</span>,
      children: <ClassifyTab />,
    },
  ]

  return (
    <div>
      <Title level={3}>标准管理</Title>
      <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
        《金融信息服务数据分类分级指南》国信办通字〔2026〕2号 — 67类三级标准分类 + 18格矩阵判定
      </Text>
      <Tabs defaultActiveKey="categories" items={tabItems} />
    </div>
  )
}

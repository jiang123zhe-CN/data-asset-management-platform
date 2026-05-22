import { useState, useEffect } from 'react'
import { Typography, Row, Col, Card, Statistic, Table, Spin } from 'antd'
import { FolderOutlined, TableOutlined, ApartmentOutlined, AuditOutlined } from '@ant-design/icons'
import { getReportSummary } from '../services/reportService'
import { getLogs } from '../services/logService'

const { Title } = Typography

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getReportSummary().then(setSummary).catch(() => {}),
      getLogs({ page: 1, page_size: 10 }).then((res) => setLogs(res.items)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin />

  const logColumns = [
    { title: '时间', dataIndex: 'created_at', width: 170, render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '用户', dataIndex: 'username', width: 100 },
    { title: '操作', dataIndex: 'action', width: 80 },
    { title: '模块', dataIndex: 'module', width: 80 },
  ]

  return (
    <div>
      <Title level={3}>仪表盘</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="资产目录数" value={summary?.total_directories || 0} prefix={<FolderOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="数据字段数" value={summary?.total_fields || 0} prefix={<TableOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="映射关系数" value={summary?.total_mappings || 0} prefix={<ApartmentOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="待复核/异常"
              value={summary?.pending_reviews || 0}
              suffix={`/ ${summary?.anomaly_count || 0}`}
              prefix={<AuditOutlined />}
              valueStyle={{ color: (summary?.pending_reviews || 0) > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近操作">
        <Table
          columns={logColumns}
          dataSource={logs}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}

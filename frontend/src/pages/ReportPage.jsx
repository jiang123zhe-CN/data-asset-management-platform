import { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Typography, Button, Space, Spin } from 'antd'
import { FolderOutlined, TableOutlined, ApartmentOutlined, AuditOutlined, ExportOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { getReportSummary, getReportByDirectory, getReportBySensitivity, exportFieldsReport, exportMappingsReport } from '../services/reportService'

const { Title } = Typography

export default function ReportPage() {
  const [summary, setSummary] = useState(null)
  const [dirStats, setDirStats] = useState([])
  const [sensitivityStats, setSensitivityStats] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getReportSummary().then(setSummary),
      getReportByDirectory().then(setDirStats),
      getReportBySensitivity().then(setSensitivityStats),
    ]).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin />

  const dirChartOption = {
    title: { text: '目录字段分布', left: 'center' },
    tooltip: {},
    xAxis: { type: 'category', data: dirStats.map((d) => d.name), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: '字段数' },
    series: [{ type: 'bar', data: dirStats.map((d) => d.field_count), itemStyle: { color: '#667eea' } }],
  }

  const pieChartOption = {
    title: { text: '敏感等级分布', left: 'center' },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: sensitivityStats.map((s) => ({ name: s.sensitivity_level, value: s.count })),
      label: { show: true, formatter: '{b}: {c}' },
    }],
  }

  return (
    <div>
      <Title level={3}>报表</Title>

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
          <Card><Statistic title="待复核数" value={summary?.pending_reviews || 0} prefix={<AuditOutlined />} valueStyle={{ color: summary?.pending_reviews > 0 ? '#cf1322' : undefined }} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={14}>
          <Card><ReactECharts option={dirChartOption} style={{ height: 350 }} /></Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card><ReactECharts option={pieChartOption} style={{ height: 350 }} /></Card>
        </Col>
      </Row>

      <Card title="数据导出">
        <Space>
          <Button type="primary" icon={<ExportOutlined />} onClick={exportFieldsReport}>
            导出字段报表
          </Button>
          <Button icon={<ExportOutlined />} onClick={exportMappingsReport}>
            导出映射报表
          </Button>
        </Space>
      </Card>
    </div>
  )
}

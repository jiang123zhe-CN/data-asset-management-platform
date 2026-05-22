import { useState, useEffect, useCallback } from 'react'
import { Tabs, Typography, Table, Button, Tag, Space, Drawer, Descriptions, message, Radio, Input, Popconfirm } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, EditOutlined, AlertOutlined } from '@ant-design/icons'
import { getReviews, submitReview, triggerAnomalyDetection } from '../services/reviewService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography

const STATUS_COLORS = {
  pending: 'orange',
  approved: 'green',
  corrected: 'blue',
  rejected: 'red',
}

export default function ReviewPage() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [currentReview, setCurrentReview] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [reviewAction, setReviewAction] = useState('approved')
  const [reviewComment, setReviewComment] = useState('')
  const [activeTab, setActiveTab] = useState('anomaly')
  const { hasRole } = useAuth()

  const loadData = useCallback(async (page = 1, pageSize = 20, type = activeTab) => {
    setLoading(true)
    try {
      const result = await getReviews({
        page,
        page_size: pageSize,
        review_type: type,
        status: 'pending',
      })
      setData(result)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => { loadData() }, [loadData])

  const handleView = async (record) => {
    setCurrentReview(record)
    setReviewAction('approved')
    setReviewComment('')
    setDrawerOpen(true)
  }

  const handleSubmit = async () => {
    if (!currentReview) return
    setSubmitting(true)
    try {
      await submitReview(currentReview.id, {
        status: reviewAction,
        comment: reviewComment,
      })
      message.success('复核已提交')
      setDrawerOpen(false)
      loadData(data.page, data.page_size)
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDetect = async () => {
    try {
      const result = await triggerAnomalyDetection()
      message.success(result.message)
      loadData(1)
    } catch { /* ignore */ }
  }

  const columns = [
    { title: '字段编码', dataIndex: 'field_code', width: 120 },
    { title: '字段名称', dataIndex: 'field_name', width: 150 },
    { title: '来源表', dataIndex: 'field_table', width: 120 },
    {
      title: '类型', dataIndex: 'anomaly_type', width: 120,
      render: (v) => {
        const labels = { unmapped: '未映射', missing_info: '信息缺失', auto_mapped: 'AI映射' }
        return <Tag>{labels[v] || v}</Tag>
      },
    },
    {
      title: '状态', dataIndex: 'review_status', width: 100,
      render: (v) => <Tag color={STATUS_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 160,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions', width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleView(record)}>复核</Button>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'anomaly',
      label: '异常复核',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<AlertOutlined />} onClick={handleDetect}>
              自动检测异常
            </Button>
          </div>
          <Table
            columns={columns}
            dataSource={data.items}
            rowKey="id"
            loading={loading}
            pagination={{
              current: data.page,
              pageSize: data.page_size,
              total: data.total,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => loadData(p, ps),
            }}
          />
        </div>
      ),
    },
    {
      key: 'ai_mapping',
      label: 'AI 映射复核',
      children: (
        <Table
          columns={columns}
          dataSource={data.items}
          rowKey="id"
          loading={loading}
          pagination={{
            current: data.page,
            pageSize: data.page_size,
            total: data.total,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => loadData(p, ps),
          }}
        />
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>人工复核</Title>
      <Tabs
        items={tabItems}
        activeKey={activeTab}
        onChange={(key) => { setActiveTab(key); loadData(1, 20, key) }}
      />

      <Drawer
        title="复核详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={500}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={submitting} onClick={handleSubmit}>提交复核</Button>
          </Space>
        }
      >
        {currentReview && (
          <div>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="字段编码">{currentReview.field_code}</Descriptions.Item>
              <Descriptions.Item label="字段名称">{currentReview.field_name}</Descriptions.Item>
              <Descriptions.Item label="异常类型">{currentReview.anomaly_type}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_COLORS[currentReview.review_status]}>{currentReview.review_status}</Tag>
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginBottom: 16 }}>
              <Text strong>复核操作：</Text>
              <Radio.Group
                value={reviewAction}
                onChange={(e) => setReviewAction(e.target.value)}
                style={{ marginTop: 8 }}
              >
                <Space direction="vertical">
                  <Radio value="approved">
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> 确认通过
                  </Radio>
                  <Radio value="corrected">
                    <EditOutlined style={{ color: '#1677ff' }} /> 修正
                  </Radio>
                  <Radio value="rejected">
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> 驳回
                  </Radio>
                </Space>
              </Radio.Group>
            </div>

            <div>
              <Text strong>备注：</Text>
              <Input.TextArea
                rows={3}
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                placeholder="输入复核备注..."
                style={{ marginTop: 8 }}
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

import { useState } from 'react'
import { Button, Alert, Progress, Space, Tag, message } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { triggerAutoMap, getAutoMapStatus } from '../../services/mappingService'
import { useAuth } from '../../hooks/useAuth'

export default function AutoMapPanel({ stats, onComplete }) {
  const [taskId, setTaskId] = useState(null)
  const [taskStatus, setTaskStatus] = useState(null)
  const [polling, setPolling] = useState(false)
  const { hasRole } = useAuth()

  const handleAutoMap = async () => {
    try {
      const result = await triggerAutoMap()
      setTaskId(result.task_id)
      setTaskStatus('running')
      setPolling(true)

      const interval = setInterval(async () => {
        try {
          const status = await getAutoMapStatus(result.task_id)
          setTaskStatus(status.status)
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(interval)
            setPolling(false)
            if (status.status === 'completed') {
              message.success(`AI 自动映射完成：成功映射 ${status.mapped_count} 个字段`)
            }
            onComplete()
          }
        } catch {
          clearInterval(interval)
          setPolling(false)
        }
      }, 2000)
    } catch (err) {
      message.error(err.response?.data?.detail || '启动AI映射失败')
    }
  }

  if (!hasRole('data_admin', 'admin')) return null

  return (
    <Alert
      type="info"
      message={
        <Space wrap>
          <span>
            统计：共 <Tag color="blue">{stats?.total_fields || 0}</Tag> 字段，
            <Tag color="green">{stats?.total_mappings || 0}</Tag> 已映射，
            <Tag color="orange">{stats?.unmapped_fields || 0}</Tag> 未映射，
            <Tag color="purple">{stats?.ai_suggested_mappings || 0}</Tag> AI建议
          </span>
          <Button
            type="primary"
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={handleAutoMap}
            loading={polling}
            disabled={stats?.unmapped_fields === 0}
          >
            {polling ? 'AI 映射中...' : 'AI 自动映射'}
          </Button>
          {taskStatus === 'running' && (
            <Progress percent={99} status="active" style={{ width: 100 }} strokeColor="#667eea" />
          )}
        </Space>
      }
      style={{ marginBottom: 8 }}
    />
  )
}

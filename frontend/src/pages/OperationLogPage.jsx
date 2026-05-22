import { useState, useEffect, useCallback } from 'react'
import { Table, Typography, Tag, Select, DatePicker } from 'antd'
import { getLogs } from '../services/logService'

const { Title } = Typography
const { RangePicker } = DatePicker

const ACTION_COLORS = {
  CREATE: 'green', UPDATE: 'blue', DELETE: 'red', IMPORT: 'purple',
  REVIEW: 'orange', LOGIN: 'cyan',
}

export default function OperationLogPage() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})

  const loadData = useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const result = await getLogs({ page, page_size: pageSize, ...filters })
      setData(result)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { loadData() }, [loadData])

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 170,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    { title: '用户', dataIndex: 'username', width: 100 },
    {
      title: '操作', dataIndex: 'action', width: 100,
      render: (v) => <Tag color={ACTION_COLORS[v]}>{v}</Tag>,
    },
    { title: '模块', dataIndex: 'module', width: 100 },
    { title: '目标类型', dataIndex: 'target_type', width: 100, render: (v) => v || '-' },
    {
      title: '详情', dataIndex: 'detail', width: 250,
      render: (v) => {
        if (!v) return '-'
        try {
          return JSON.stringify(JSON.parse(v), null, 1)
        } catch {
          return v.length > 100 ? v.slice(0, 100) + '...' : v
        }
      },
    },
  ]

  return (
    <div>
      <Title level={3}>操作日志</Title>
      <div style={{ marginBottom: 16 }}>
        <Select
          placeholder="模块"
          allowClear
          style={{ width: 120, marginRight: 8 }}
          onChange={(v) => setFilters((f) => ({ ...f, module: v }))}
          options={[
            { value: 'directory', label: '目录' },
            { value: 'field', label: '字段' },
            { value: 'mapping', label: '映射' },
            { value: 'review', label: '复核' },
            { value: 'user', label: '用户' },
            { value: 'auth', label: '认证' },
          ]}
        />
        <Select
          placeholder="操作"
          allowClear
          style={{ width: 120, marginRight: 8 }}
          onChange={(v) => setFilters((f) => ({ ...f, action: v }))}
          options={[
            { value: 'CREATE', label: '创建' },
            { value: 'UPDATE', label: '更新' },
            { value: 'DELETE', label: '删除' },
            { value: 'IMPORT', label: '导入' },
            { value: 'REVIEW', label: '复核' },
          ]}
        />
        <RangePicker
          onChange={(dates) => {
            if (dates) {
              setFilters((f) => ({
                ...f,
                date_from: dates[0].format('YYYY-MM-DD'),
                date_to: dates[1].format('YYYY-MM-DD'),
              }))
            } else {
              setFilters((f) => ({ ...f, date_from: undefined, date_to: undefined }))
            }
          }}
        />
      </div>
      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        scroll={{ x: 900 }}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => loadData(p, ps),
        }}
      />
    </div>
  )
}

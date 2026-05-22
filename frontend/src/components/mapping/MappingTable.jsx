import { Table, Button, Space, Tag, Popconfirm } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { useAuth } from '../../hooks/useAuth'

export default function MappingTable({ data, loading, onDelete, onPageChange, onBatchMap, selectedRowKeys, onSelectChange }) {
  const { hasRole } = useAuth()
  const canEdit = hasRole('data_admin', 'admin')

  const columns = [
    { title: '字段编码', dataIndex: 'field_code', key: 'field_code', width: 120 },
    { title: '字段名称', dataIndex: 'field_name', key: 'field_name', width: 150 },
    { title: '数据类型', dataIndex: 'field_data_type', key: 'field_data_type', width: 100 },
    { title: '来源表', dataIndex: 'field_table', key: 'field_table', width: 150 },
    {
      title: '目录路径', dataIndex: 'directory_path', key: 'directory_path', width: 250,
      render: (v) => v || '-',
    },
    {
      title: '映射来源', dataIndex: 'mapping_source', key: 'mapping_source', width: 120,
      render: (v) =>
        v === 'ai_suggested' ? (
          <Tag color="purple">AI建议</Tag>
        ) : (
          <Tag color="blue">人工</Tag>
        ),
    },
    {
      title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 80,
      render: (v) => (v != null ? `${(v * 100).toFixed(0)}%` : '-'),
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作', key: 'actions', width: 80, fixed: 'right',
      render: (_, record) =>
        canEdit && (
          <Popconfirm title="确定删除此映射？" onConfirm={() => onDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        ),
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={data.items}
      rowKey="id"
      loading={loading}
      scroll={{ x: 1200 }}
      rowSelection={canEdit ? { selectedRowKeys, onChange: onSelectChange } : undefined}
      pagination={{
        current: data.page,
        pageSize: data.page_size,
        total: data.total,
        showTotal: (t) => `共 ${t} 条`,
        showSizeChanger: true,
        onChange: onPageChange,
      }}
      title={() =>
        canEdit && (
          <Button type="primary" icon={<PlusOutlined />} onClick={onBatchMap}>
            批量映射
          </Button>
        )
      }
    />
  )
}

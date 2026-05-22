import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Space, Input, Select, Row, Col, Typography, Tag, message, Drawer, Modal, Upload } from 'antd'
import { PlusOutlined, UploadOutlined, DownloadOutlined, ExportOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import FieldForm from '../components/field/FieldForm'
import { getFields, createField, updateField, deleteField, importFields, downloadTemplate, exportFields, getImportHistory } from '../services/fieldService'
import { useAuth } from '../hooks/useAuth'

const { Title } = Typography

const SENSITIVITY_COLORS = { L1: 'green', L2: 'blue', L3: 'orange', L4: 'red' }

export default function FieldPage() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({})
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingField, setEditingField] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [searchText, setSearchText] = useState('')
  const { hasRole } = useAuth()
  const canEdit = hasRole('data_entry', 'data_admin', 'admin')

  const loadData = useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize, ...filters }
      if (searchText) params.search = searchText
      const result = await getFields(params)
      setData(result)
    } catch {
      message.error('加载字段列表失败')
    } finally {
      setLoading(false)
    }
  }, [filters, searchText])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSearch = () => {
    loadData(1)
  }

  const handleCreate = () => {
    setEditingField(null)
    setDrawerOpen(true)
  }

  const handleEdit = (record) => {
    setEditingField(record)
    setDrawerOpen(true)
  }

  const handleDelete = async (id) => {
    try {
      await deleteField(id)
      message.success('字段已停用')
      loadData(data.page, data.page_size)
    } catch {
      message.error('操作失败')
    }
  }

  const handleSubmit = async (values) => {
    setSubmitting(true)
    try {
      if (editingField) {
        await updateField(editingField.id, values)
        message.success('字段已更新')
      } else {
        await createField(values)
        message.success('字段已创建')
      }
      setDrawerOpen(false)
      loadData(data.page, data.page_size)
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleImport = async (file) => {
    setImporting(true)
    try {
      const result = await importFields(file)
      message.success(`导入完成: 成功 ${result.success_rows} 条, 失败 ${result.failed_rows} 条`)
      setImportModalOpen(false)
      loadData(1)
    } catch (err) {
      message.error(err.response?.data?.detail || '导入失败')
    } finally {
      setImporting(false)
    }
    return false // Prevent default upload behavior
  }

  const columns = [
    { title: '字段编码', dataIndex: 'field_code', key: 'field_code', width: 120 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '数据类型', dataIndex: 'data_type', key: 'data_type', width: 100 },
    { title: '表名', dataIndex: 'table_name', key: 'table_name', width: 150 },
    { title: '数据库', dataIndex: 'database_name', key: 'database_name', width: 120 },
    {
      title: '业务域', dataIndex: 'business_domain', key: 'business_domain', width: 100,
      render: (v) => v || '-',
    },
    {
      title: '敏感等级', dataIndex: 'sensitivity_level', key: 'sensitivity_level', width: 100,
      render: (v) => <Tag color={SENSITIVITY_COLORS[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '异常', dataIndex: 'is_anomaly', key: 'is_anomaly', width: 80,
      render: (v) => v ? <Tag color="red">异常</Tag> : <Tag color="green">正常</Tag>,
    },
    {
      title: '来源', dataIndex: 'source', key: 'source', width: 100,
      render: (v) => v === 'excel_import' ? <Tag>Excel导入</Tag> : <Tag color="blue">手动</Tag>,
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions', width: 150, fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
          {hasRole('data_admin', 'admin') && (
            <Button type="link" size="small" danger onClick={() => handleDelete(record.id)}>停用</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>字段管理</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Space wrap>
            <Input.Search
              placeholder="搜索字段编码、名称、表名..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              style={{ width: 300 }}
              allowClear
            />
            <Select
              placeholder="敏感等级"
              allowClear
              style={{ width: 120 }}
              onChange={(v) => setFilters((f) => ({ ...f, sensitivity_level: v }))}
              options={[
                { value: 'L1', label: 'L1-公开' },
                { value: 'L2', label: 'L2-内部' },
                { value: 'L3', label: 'L3-机密' },
                { value: 'L4', label: 'L4-绝密' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={() => loadData(1)}>刷新</Button>
          </Space>
        </Col>
        <Col>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={downloadTemplate}>下载模板</Button>
            <Button icon={<ExportOutlined />} onClick={exportFields}>导出</Button>
            {canEdit && (
              <>
                <Button type="primary" icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>
                  导入Excel
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新增字段
                </Button>
              </>
            )}
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1400 }}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showTotal: (t) => `共 ${t} 条`,
          showSizeChanger: true,
          onChange: (p, ps) => loadData(p, ps),
        }}
      />

      <Drawer
        title={editingField ? '编辑字段' : '新增字段'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={500}
      >
        <FieldForm
          initialData={editingField}
          onSubmit={handleSubmit}
          onCancel={() => setDrawerOpen(false)}
          loading={submitting}
        />
      </Drawer>

      <Modal
        title="导入Excel"
        open={importModalOpen}
        onCancel={() => setImportModalOpen(false)}
        footer={null}
      >
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          beforeUpload={handleImport}
          showUploadList={false}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: 48, color: '#667eea' }} />
          </p>
          <p>点击或拖拽 .xlsx/.xls 文件到此区域</p>
          <p style={{ color: '#999' }}>
            请确保文件列名与模板一致。{' '}
            <Button type="link" onClick={downloadTemplate} style={{ padding: 0 }}>
              下载模板
            </Button>
          </p>
        </Upload.Dragger>
      </Modal>
    </div>
  )
}

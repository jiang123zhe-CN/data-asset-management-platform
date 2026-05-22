import { useState, useEffect, useCallback } from 'react'
import { Row, Col, Card, Typography, Button, Space, message, Popconfirm, Spin, Empty } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderAddOutlined } from '@ant-design/icons'
import DirectoryTree from '../components/directory/DirectoryTree'
import DirectoryForm from '../components/directory/DirectoryForm'
import buildTree from '../utils/buildTree'
import {
  getDirectoryTree,
  getDirectory,
  createDirectory,
  updateDirectory,
  deleteDirectory,
} from '../services/directoryService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography

export default function DirectoryPage() {
  const [flatList, setFlatList] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selectedDir, setSelectedDir] = useState(null)
  const [mode, setMode] = useState('view') // 'view' | 'create' | 'edit'
  const [parentDir, setParentDir] = useState(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { hasRole } = useAuth()
  const canEdit = hasRole('system_admin', 'admin')

  const treeData = buildTree(flatList)

  const loadTree = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getDirectoryTree()
      setFlatList(data)
    } catch {
      message.error('加载目录树失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTree()
  }, [loadTree])

  const loadDetail = async (id) => {
    try {
      const data = await getDirectory(id)
      setSelectedDir(data)
      setMode('view')
      setParentDir(null)
    } catch {
      message.error('加载目录详情失败')
    }
  }

  const handleSelect = (id) => {
    setSelectedId(id)
    loadDetail(id)
  }

  const handleCreate = () => {
    setSelectedDir(null)
    setParentDir(null)
    setMode('create')
  }

  const handleAddChild = (parentData) => {
    setSelectedDir(null)
    setParentDir(parentData)
    setMode('create')
  }

  const handleEdit = () => {
    setMode('edit')
  }

  const handleDelete = async () => {
    try {
      await deleteDirectory(selectedId)
      message.success('目录已删除')
      setSelectedId(null)
      setSelectedDir(null)
      setMode('view')
      loadTree()
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async (values) => {
    setSubmitting(true)
    try {
      if (mode === 'edit') {
        await updateDirectory(selectedId, values)
        message.success('目录已更新')
        loadDetail(selectedId)
      } else {
        const data = parentDir
          ? { ...values, parent_id: parentDir.id }
          : values
        await createDirectory(data)
        message.success('目录已创建')
        setMode('view')
        setParentDir(null)
        loadTree()
      }
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => {
    if (selectedDir) {
      setMode('view')
      setParentDir(null)
    } else {
      setSelectedDir(null)
      setMode('view')
      setParentDir(null)
    }
  }

  const formInitialValues = mode === 'edit'
    ? { name: selectedDir?.name, code: selectedDir?.code, description: selectedDir?.description, tags: selectedDir?.tags, parent_id: selectedDir?.parent_id, sort_order: selectedDir?.sort_order }
    : parentDir
      ? { parent_id: parentDir.id, sort_order: 0 }
      : { sort_order: 0 }

  return (
    <div>
      <Title level={3}>资产目录管理</Title>
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Card
            title="目录结构"
            extra={
              canEdit && (
                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建根目录
                </Button>
              )
            }
            style={{ height: 'calc(100vh - 180px)', overflow: 'auto' }}
          >
            {loading ? (
              <Spin />
            ) : treeData.length === 0 ? (
              <Empty description="暂无目录，请创建" />
            ) : (
              <DirectoryTree
                treeData={treeData}
                selectedKeys={selectedId ? [selectedId] : []}
                onSelect={handleSelect}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card
            title={
              mode === 'create'
                ? parentDir ? `添加子目录: ${parentDir.name}` : '新建根目录'
                : mode === 'edit'
                  ? '编辑目录'
                  : '目录详情'
            }
            extra={
              mode === 'view' && selectedDir && canEdit && (
                <Space>
                  <Button icon={<FolderAddOutlined />} onClick={() => handleAddChild(selectedDir)}>
                    添加子目录
                  </Button>
                  <Button icon={<EditOutlined />} onClick={handleEdit}>编辑</Button>
                  <Popconfirm title="确定删除此目录？有子目录时不可删除" onConfirm={handleDelete}>
                    <Button danger icon={<DeleteOutlined />}>删除</Button>
                  </Popconfirm>
                </Space>
              )
            }
          >
            {mode === 'view' && selectedDir ? (
              <div>
                <p><Text strong>名称：</Text>{selectedDir.name}</p>
                <p><Text strong>编码：</Text>{selectedDir.code}</p>
                <p><Text strong>描述：</Text>{selectedDir.description || '-'}</p>
                <p><Text strong>标签：</Text>{selectedDir.tags || '-'}</p>
                <p><Text strong>层级：</Text>{selectedDir.level}</p>
                <p><Text strong>状态：</Text>{selectedDir.is_active ? '启用' : '禁用'}</p>
              </div>
            ) : mode === 'view' && !selectedDir ? (
              <Empty description="请从左侧选择一个目录" />
            ) : (
              <DirectoryForm
                initialData={formInitialValues}
                treeData={flatList}
                onSubmit={handleSubmit}
                onCancel={handleCancel}
                loading={submitting}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

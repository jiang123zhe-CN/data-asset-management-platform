import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Space, Typography, Tag, Modal, Form, Input, Select, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, KeyOutlined } from '@ant-design/icons'
import { getUsers, createUser, updateUser, deleteUser, resetPassword } from '../services/userService'

const { Title } = Typography

const ROLE_LABELS = {
  admin: '管理员',
  system_admin: '系统管理员',
  data_entry: '数据录入员',
  data_admin: '数据管理员',
  reviewer: '复核员',
}

const ROLE_COLORS = {
  admin: 'red',
  system_admin: 'volcano',
  data_entry: 'blue',
  data_admin: 'purple',
  reviewer: 'green',
}

export default function UserPage() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const loadData = useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const result = await getUsers({ page, page_size: pageSize })
      setData(result)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleCreate = () => {
    setEditingUser(null)
    form.resetFields()
    form.setFieldsValue({ role: 'data_entry' })
    setModalOpen(true)
  }

  const handleEdit = (record) => {
    setEditingUser(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const handleSubmit = async (values) => {
    setSubmitting(true)
    try {
      if (editingUser) {
        await updateUser(editingUser.id, values)
        message.success('用户已更新')
      } else {
        await createUser(values)
        message.success('用户已创建')
      }
      setModalOpen(false)
      loadData(data.page, data.page_size)
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteUser(id)
      message.success('用户已停用')
      loadData(data.page, data.page_size)
    } catch { /* ignore */ }
  }

  const handleResetPwd = async (id) => {
    try {
      await resetPassword(id)
      message.success('密码已重置为默认密码')
    } catch { /* ignore */ }
  }

  const columns = [
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '显示名', dataIndex: 'display_name', width: 120 },
    {
      title: '角色', dataIndex: 'role', width: 120,
      render: (v) => <Tag color={ROLE_COLORS[v]}>{ROLE_LABELS[v] || v}</Tag>,
    },
    { title: '邮箱', dataIndex: 'email', width: 180, render: (v) => v || '-' },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (v) => v ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>,
    },
    {
      title: '最后登录', dataIndex: 'last_login_at', width: 160,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 160,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions', width: 180, fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定重置密码？" onConfirm={() => handleResetPwd(record.id)}>
            <Button type="link" size="small" icon={<KeyOutlined />}>重置密码</Button>
          </Popconfirm>
          {record.is_active && (
            <Popconfirm title="确定停用此用户？" onConfirm={() => handleDelete(record.id)}>
              <Button type="link" size="small" danger>停用</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>用户管理</Title>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增用户</Button>
      </div>
      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1100 }}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => loadData(p, ps),
        }}
      />

      <Modal
        title={editingUser ? '编辑用户' : '新增用户'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3 }]}>
            <Input disabled={!!editingUser} />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="display_name" label="显示名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={Object.entries(ROLE_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

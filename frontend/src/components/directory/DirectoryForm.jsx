import { useEffect } from 'react'
import { Form, Input, Select, InputNumber, Button, Space } from 'antd'

export default function DirectoryForm({ initialData, treeData, onSubmit, onCancel, loading }) {
  const [form] = Form.useForm()

  useEffect(() => {
    form.resetFields()
    if (initialData) {
      form.setFieldsValue(initialData)
    }
  }, [initialData, form])

  const parentOptions = treeData
    .filter((d) => d.id !== initialData?.id)
    .map((d) => ({
      value: d.id,
      label: `${'  '.repeat(d.level)}${d.name}`,
    }))

  return (
    <Form form={form} layout="vertical" onFinish={onSubmit}>
      <Form.Item name="name" label="目录名称" rules={[{ required: true, message: '请输入目录名称' }]}>
        <Input />
      </Form.Item>
      <Form.Item name="code" label="目录编码" rules={[{ required: true, message: '请输入目录编码' }]}>
        <Input />
      </Form.Item>
      <Form.Item name="parent_id" label="父级目录">
        <Select allowClear placeholder="无（根目录）" options={parentOptions} />
      </Form.Item>
      <Form.Item name="description" label="描述">
        <Input.TextArea rows={3} />
      </Form.Item>
      <Form.Item name="tags" label="标签">
        <Input placeholder="多个标签用逗号分隔" />
      </Form.Item>
      <Form.Item name="sort_order" label="排序" initialValue={0}>
        <InputNumber min={0} />
      </Form.Item>
      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            {initialData ? '保存' : '创建'}
          </Button>
          <Button onClick={onCancel}>取消</Button>
        </Space>
      </Form.Item>
    </Form>
  )
}

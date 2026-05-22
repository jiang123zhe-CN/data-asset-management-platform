import { useEffect } from 'react'
import { Form, Input, Select, InputNumber, Button, Space } from 'antd'

const DATA_TYPES = ['VARCHAR', 'INT', 'BIGINT', 'DECIMAL', 'DATE', 'DATETIME', 'TIMESTAMP', 'TEXT', 'BOOLEAN', 'FLOAT']
const SENSITIVITY_LEVELS = ['L1', 'L2', 'L3', 'L4']

export default function FieldForm({ initialData, onSubmit, onCancel, loading }) {
  const [form] = Form.useForm()

  useEffect(() => {
    form.resetFields()
    if (initialData) {
      form.setFieldsValue(initialData)
    }
  }, [initialData, form])

  return (
    <Form form={form} layout="vertical" onFinish={onSubmit}>
      <Form.Item name="field_code" label="字段编码" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item name="name" label="字段名称" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item name="english_name" label="英文名称">
        <Input />
      </Form.Item>
      <Form.Item name="data_type" label="数据类型" rules={[{ required: true }]}>
        <Select options={DATA_TYPES.map((t) => ({ value: t, label: t }))} />
      </Form.Item>
      <Form.Item name="length" label="长度">
        <InputNumber min={0} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="precision" label="精度">
        <InputNumber min={0} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="table_name" label="所属表名" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item name="database_name" label="数据库名">
        <Input />
      </Form.Item>
      <Form.Item name="business_domain" label="业务域">
        <Input placeholder="如：客户域、财务域、人力域" />
      </Form.Item>
      <Form.Item name="sensitivity_level" label="敏感等级" initialValue="L1">
        <Select options={SENSITIVITY_LEVELS.map((l) => ({ value: l, label: l }))} />
      </Form.Item>
      <Form.Item name="description" label="描述">
        <Input.TextArea rows={3} />
      </Form.Item>
      <Form.Item name="business_rules" label="业务规则">
        <Input.TextArea rows={3} />
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

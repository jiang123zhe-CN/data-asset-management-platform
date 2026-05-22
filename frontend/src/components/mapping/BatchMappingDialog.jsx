import { useState, useEffect } from 'react'
import { Modal, Select, Tree, message, Transfer } from 'antd'
import { getDirectoryTree } from '../../services/directoryService'
import { getUnmappedFields, batchCreateMappings } from '../../services/mappingService'
import buildTree from '../../utils/buildTree'

export default function BatchMappingDialog({ open, onClose, onComplete }) {
  const [dirTree, setDirTree] = useState([])
  const [flatDirs, setFlatDirs] = useState([])
  const [unmappedFields, setUnmappedFields] = useState([])
  const [selectedDir, setSelectedDir] = useState(null)
  const [targetKeys, setTargetKeys] = useState([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      getDirectoryTree().then(setFlatDirs)
      getUnmappedFields().then(setUnmappedFields)
      setSelectedDir(null)
      setTargetKeys([])
    }
  }, [open])

  useEffect(() => {
    setDirTree(buildTree(flatDirs))
  }, [flatDirs])

  const handleSubmit = async () => {
    if (!selectedDir) {
      message.warning('请选择目标目录')
      return
    }
    if (targetKeys.length === 0) {
      message.warning('请选择至少一个字段')
      return
    }
    setSubmitting(true)
    try {
      await batchCreateMappings({ directory_id: selectedDir, field_ids: targetKeys })
      message.success(`成功映射 ${targetKeys.length} 个字段`)
      onComplete()
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const dirOptions = flatDirs.map((d) => ({
    value: d.id,
    label: `${'  '.repeat(d.level)}${d.name} (${d.code})`,
  }))

  return (
    <Modal
      title="批量映射"
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={submitting}
      width={700}
      okText="提交映射"
    >
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>选择目标目录：</label>
        <Select
          style={{ width: '100%' }}
          placeholder="搜索并选择目录..."
          options={dirOptions}
          value={selectedDir}
          onChange={setSelectedDir}
          showSearch
          filterOption={(input, option) => option.label.includes(input)}
        />
      </div>
      <div>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
          选择要映射的字段（仅显示未映射字段）：
        </label>
        <Transfer
          dataSource={unmappedFields.map((f) => ({
            key: f.id,
            title: `${f.name} (${f.field_code})`,
            description: f.table_name,
          }))}
          targetKeys={targetKeys}
          onChange={setTargetKeys}
          render={(item) => item.title}
          listStyle={{ width: 290, height: 300 }}
          showSearch
          filterOption={(inputValue, item) => item.title.includes(inputValue)}
          locale={{ searchPlaceholder: '搜索字段' }}
        />
      </div>
    </Modal>
  )
}

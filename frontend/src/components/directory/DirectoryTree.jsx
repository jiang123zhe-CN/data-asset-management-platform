import { Tree } from 'antd'
import { FolderOutlined } from '@ant-design/icons'

export default function DirectoryTree({ treeData, onSelect, selectedKeys }) {
  return (
    <Tree
      treeData={treeData}
      selectedKeys={selectedKeys}
      onSelect={(keys) => {
        if (keys.length > 0) onSelect(keys[0])
      }}
      defaultExpandAll
      blockNode
      showIcon
      icon={<FolderOutlined />}
    />
  )
}

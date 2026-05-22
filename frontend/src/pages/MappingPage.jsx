import { useState, useEffect, useCallback } from 'react'
import { Tabs, Typography, message, Spin } from 'antd'
import MappingTable from '../components/mapping/MappingTable'
import BatchMappingDialog from '../components/mapping/BatchMappingDialog'
import VisualizationGraph from '../components/mapping/VisualizationGraph'
import AutoMapPanel from '../components/mapping/AutoMapPanel'
import { getMappings, deleteMapping, getMappingStats } from '../services/mappingService'

const { Title } = Typography

export default function MappingPage() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [batchOpen, setBatchOpen] = useState(false)
  const [stats, setStats] = useState(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])

  const loadData = useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const result = await getMappings({ page, page_size: pageSize })
      setData(result)
    } catch {
      message.error('加载映射列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadStats = useCallback(async () => {
    try {
      const result = await getMappingStats()
      setStats(result)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadData()
    loadStats()
  }, [loadData, loadStats])

  const handleDelete = async (id) => {
    try {
      await deleteMapping(id)
      message.success('映射已删除')
      loadData(data.page, data.page_size)
      loadStats()
    } catch {
      message.error('删除失败')
    }
  }

  const tabItems = [
    {
      key: 'table',
      label: '映射列表',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <AutoMapPanel stats={stats} onComplete={() => { loadData(1); loadStats() }} />
          </div>
          <MappingTable
            data={data}
            loading={loading}
            onDelete={handleDelete}
            onPageChange={(p, ps) => loadData(p, ps)}
            onBatchMap={() => setBatchOpen(true)}
            selectedRowKeys={selectedRowKeys}
            onSelectChange={setSelectedRowKeys}
          />
        </div>
      ),
    },
    {
      key: 'visualization',
      label: '可视化关系图',
      children: <VisualizationGraph />,
    },
  ]

  return (
    <div>
      <Title level={3}>映射管理</Title>
      <Tabs items={tabItems} />

      <BatchMappingDialog
        open={batchOpen}
        onClose={() => setBatchOpen(false)}
        onComplete={() => { setBatchOpen(false); loadData(1); loadStats() }}
      />
    </div>
  )
}

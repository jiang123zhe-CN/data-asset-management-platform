import { useState, useEffect } from 'react'
import { Spin, message } from 'antd'
import ReactECharts from 'echarts-for-react'
import { getVisualizationData } from '../../services/mappingService'

export default function VisualizationGraph() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getVisualizationData()
      .then(setData)
      .catch(() => message.error('加载可视化数据失败'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin />

  if (!data || data.nodes.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无映射数据</div>
  }

  const dirNodes = data.nodes.filter((n) => n.node_type === 'directory')
  const fieldNodes = data.nodes.filter((n) => n.node_type === 'field')

  const option = {
    tooltip: { trigger: 'item', formatter: '{b}' },
    legend: {
      data: ['目录节点', '字段节点'],
      bottom: 0,
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        force: { repulsion: 200, edgeLength: [80, 250] },
        categories: [
          { name: '目录节点', itemStyle: { color: '#667eea' }, symbolSize: 40 },
          { name: '字段节点', itemStyle: { color: '#52c41a' }, symbolSize: 20 },
        ],
        data: [
          ...dirNodes.map((n) => ({
            id: n.id,
            name: n.label,
            category: 0,
            symbolSize: 30 + Math.min(n.group?.length || 0, 5) * 5,
          })),
          ...fieldNodes.map((n) => ({
            id: n.id,
            name: n.label,
            category: 1,
          })),
        ],
        links: data.edges.map((e) => ({
          source: e.source,
          target: e.target,
        })),
        label: { show: true, fontSize: 11 },
        emphasis: { focus: 'adjacency', label: { fontSize: 14 } },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 500 }} />
}

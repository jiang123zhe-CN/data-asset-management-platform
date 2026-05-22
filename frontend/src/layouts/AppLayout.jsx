import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, theme } from 'antd'
import {
  DashboardOutlined,
  FolderOutlined,
  TableOutlined,
  ApartmentOutlined,
  AuditOutlined,
  UserOutlined,
  FileTextOutlined,
  BarChartOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useAuth } from '../hooks/useAuth'
import './AppLayout.css'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/directories', icon: <FolderOutlined />, label: '资产目录', roles: null },
  { key: '/fields', icon: <TableOutlined />, label: '字段管理', roles: ['data_entry', 'data_admin', 'admin'] },
  { key: '/mappings', icon: <ApartmentOutlined />, label: '映射管理', roles: ['data_admin', 'admin'] },
  { key: '/review', icon: <AuditOutlined />, label: '人工复核', roles: ['reviewer', 'admin'] },
  { key: '/users', icon: <UserOutlined />, label: '用户管理', roles: ['admin'] },
  { key: '/logs', icon: <FileTextOutlined />, label: '操作日志', roles: ['reviewer', 'admin'] },
  { key: '/reports', icon: <BarChartOutlined />, label: '报表', roles: ['admin'] },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, hasRole } = useAuth()
  const { token: themeToken } = theme.useToken()

  const visibleMenuItems = menuItems.filter(
    (item) => !item.roles || hasRole(...item.roles),
  )

  const userMenuItems = [
    { key: 'role', label: `角色: ${user?.role}` },
    { key: 'logout', label: '退出登录', icon: <LogoutOutlined />, danger: true },
  ]

  const handleUserMenuClick = ({ key }) => {
    if (key === 'logout') logout()
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark" width={220}>
        <div className="logo">
          {collapsed ? 'D' : '数据资产平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={visibleMenuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: themeToken.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }}>
            <Button type="text" icon={<UserOutlined />}>
              {user?.display_name || user?.username}
            </Button>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

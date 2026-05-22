import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'

function Home() {
  const [backendStatus, setBackendStatus] = useState('checking...')

  useEffect(() => {
    getHealth()
      .then((data) => setBackendStatus(`v${data.version}`))
      .catch(() => setBackendStatus('offline'))
  }, [])

  return (
    <div className="home">
      <header className="home-header">
        <h1>数据资产管理平台</h1>
        <p className="subtitle">Data Asset Management Platform</p>
      </header>
      <main className="home-main">
        <div className="status-card">
          <span className="status-label">后端状态</span>
          <span className={`status-value ${backendStatus === 'offline' ? 'offline' : 'online'}`}>
            {backendStatus}
          </span>
        </div>
      </main>
    </div>
  )
}

export default Home

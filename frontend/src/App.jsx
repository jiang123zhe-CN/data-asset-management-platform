import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'
import AppLayout from './layouts/AppLayout'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import DirectoryPage from './pages/DirectoryPage'
import FieldPage from './pages/FieldPage'
import MappingPage from './pages/MappingPage'
import ReviewPage from './pages/ReviewPage'
import UserPage from './pages/UserPage'
import OperationLogPage from './pages/OperationLogPage'
import ReportPage from './pages/ReportPage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/directories" element={<DirectoryPage />} />
            <Route path="/fields" element={<FieldPage />} />
            <Route path="/mappings" element={<MappingPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/users" element={<UserPage />} />
            <Route path="/logs" element={<OperationLogPage />} />
            <Route path="/reports" element={<ReportPage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App

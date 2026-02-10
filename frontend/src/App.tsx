import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
import { useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardPage } from './pages/DashboardPage'
import { ExpiredItemsPage } from './pages/ExpiredItemsPage'
import { PredictivePage } from './pages/PredictivePage'
import { TestePage } from './pages/TestePage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading)
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading)
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <Layout><DashboardPage /></Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/expired-items"
        element={
          <PrivateRoute>
            <Layout><ExpiredItemsPage /></Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/predictive"
        element={
          <PrivateRoute>
            <Layout><PredictivePage /></Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/teste"
        element={
          <PrivateRoute>
            <Layout><TestePage /></Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/register"
        element={
          <AdminRoute>
            <Layout><RegisterPage /></Layout>
          </AdminRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

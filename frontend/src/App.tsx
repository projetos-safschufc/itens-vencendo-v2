import { Routes, Route, Navigate, useLocation, Link as RouterLink } from 'react-router-dom'
import { CircularProgress, Box, Typography, Link } from '@mui/material'
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

/** Rota pública: exibe o formulário de cadastro. Com login usa Layout; sem login, página standalone (como login). */
function RegisterRoute() {
  const { user, loading } = useAuth()
  if (loading)
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  if (user)
    return (
      <Layout>
        <RegisterPage />
      </Layout>
    )
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Box sx={{ maxWidth: 520, width: '100%' }}>
        <RegisterPage />
        <Typography variant="body2" align="center" sx={{ mt: 2 }}>
          <Link component={RouterLink} to="/login">
            Já tem conta? Entrar
          </Link>
        </Typography>
      </Box>
    </Box>
  )
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
      <Route path="/register" element={<RegisterRoute />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

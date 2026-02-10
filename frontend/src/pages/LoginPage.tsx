import { useState } from 'react'
import { useNavigate, Link as RouterLink, useLocation } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  Link,
} from '@mui/material'
import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../contexts/AuthContext'

export function LoginPage() {
  const [username, setUsername] = useState('') // e-mail
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from

  const getLoginErrorMessage = (err: unknown): string => {
    if (!err || typeof err !== 'object' || !('response' in err)) {
      return 'Não foi possível conectar ao servidor. Verifique sua conexão e se a API está em execução.'
    }
    const res = (err as { response?: { data?: unknown; status?: number } }).response
    const data = res?.data
    const status = res?.status
    if (data && typeof data === 'object' && 'detail' in data) {
      const d = (data as { detail: unknown }).detail
      if (typeof d === 'string') return d
      if (Array.isArray(d) && d.length > 0 && d[0] && typeof d[0] === 'object' && 'msg' in d[0]) {
        return String((d[0] as { msg: string }).msg)
      }
    }
    if (status === 401) return 'E-mail ou senha inválidos.'
    if (status === 503) return 'Serviço de autenticação indisponível. Tente novamente em instantes.'
    return 'Falha no login. Tente novamente.'
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(username, password)
      navigate(from === '/register' && user?.role === 'admin' ? '/register' : '/dashboard', { replace: true })
    } catch (err: unknown) {
      setError(getLoginErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

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
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom align="center">
            Analytics Inventário Hospitalar
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            Faça login para acessar o dashboard
          </Typography>
          {loading && (
            <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mb: 1 }}>
              O login pode levar alguns segundos. Aguarde...
            </Typography>
          )}
          <form onSubmit={handleSubmit}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            <TextField
              fullWidth
              label="E-mail"
              type="email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
            />
            <TextField
              fullWidth
              label="Senha"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="current-password"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword((v) => !v)} edge="end">
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 3 }}
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </Button>
          </form>
          <Typography variant="caption" display="block" sx={{ mt: 2 }} color="text.secondary">
            Use o e-mail e a senha cadastrados em ctrl.users (banco SAFS).
          </Typography>
          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            <Link component={RouterLink} to="/register" state={{ from: '/register' }}>
              Cadastrar novo usuário
            </Link>
            <Typography component="span" variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              (apenas administradores)
            </Typography>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}

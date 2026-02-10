import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Link,
} from '@mui/material'
import { authApi } from '../api/endpoints'

const PROFILES = [
  { value: 1, label: 'Administrador' },
  { value: 2, label: 'Analista' },
  { value: 3, label: 'Somente leitura' },
]

export function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [profileId, setProfileId] = useState(3)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      await authApi.register({ name, email, password, profile_id: profileId })
      setSuccess('Usuário cadastrado com sucesso.')
      setName('')
      setEmail('')
      setPassword('')
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null
      setError(detail || 'Falha ao cadastrar usuário.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Cadastrar novo usuário
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Apenas administradores. O usuário será criado em ctrl.users (banco SAFS).
      </Typography>
      <Card sx={{ maxWidth: 480 }}>
        <CardContent>
          <form onSubmit={handleSubmit}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
            <TextField
              fullWidth
              label="Nome"
              value={name}
              onChange={(e) => setName(e.target.value)}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="E-mail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Senha"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              helperText="Mínimo 6 caracteres"
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Perfil</InputLabel>
              <Select
                value={profileId}
                label="Perfil"
                onChange={(e) => setProfileId(Number(e.target.value))}
              >
                {PROFILES.map((p) => (
                  <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button type="submit" variant="contained" disabled={loading} sx={{ mt: 2 }}>
              {loading ? 'Cadastrando...' : 'CADASTRAR'}
            </Button>
            <Typography variant="body2" sx={{ mt: 2 }}>
              <Link component={RouterLink} to="/dashboard">
                Voltar ao dashboard
              </Link>
            </Typography>
          </form>
        </CardContent>
      </Card>
    </Box>
  )
}

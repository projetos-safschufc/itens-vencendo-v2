import { Link as RouterLink, useLocation } from 'react-router-dom'
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box,
  Link,
} from '@mui/material'
import LogoutIcon from '@mui/icons-material/Logout'
import { useAuth } from '../contexts/AuthContext'

const nav = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/expired-items', label: 'Itens vencidos' },
  { to: '/predictive', label: 'Análise preditiva' },
  { to: '/teste', label: 'Histórico 6 meses' },
  { to: '/register', label: 'Cadastrar usuário', adminOnly: true },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Analytics Inventário
          </Typography>
          {nav.map(({ to, label, adminOnly }) => {
            if (adminOnly && user?.role !== 'admin') return null
            return (
              <Link
                key={to}
                component={RouterLink}
                to={to}
                color="inherit"
                underline="none"
                sx={{ mx: 1 }}
              >
                <Button color="inherit" variant={location.pathname === to ? 'outlined' : 'text'}>
                  {label}
                </Button>
              </Link>
            )
          })}
          <Typography variant="body2" sx={{ mr: 2 }}>
            {new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })}
          </Typography>
          <Typography variant="body2" sx={{ mr: 1 }}>
            {user?.username} ({user?.role})
          </Typography>
          <IconButton color="inherit" onClick={logout} title="Sair">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ p: 3 }}>
        {children}
      </Box>
    </Box>
  )
}

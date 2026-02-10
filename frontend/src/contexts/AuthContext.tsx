import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/endpoints'

type User = { id: string; username: string; role: string; full_name: string | null } | null

type AuthContextValue = {
  user: User
  loading: boolean
  login: (username: string, password: string) => Promise<User | null>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const t = localStorage.getItem('access_token')
    if (!t) {
      setUser(null)
      setLoading(false)
      return null
    }
    try {
      const { data } = await authApi.me()
      setUser(data)
      return data
    } catch {
      setUser(null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback(async (username: string, password: string): Promise<User | null> => {
    const { data } = await authApi.login(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return refreshUser()
  }, [refreshUser])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

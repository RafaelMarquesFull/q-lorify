import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
    id: string
    email: string
    name: string | null
    role: string
}

interface AuthState {
    token: string | null
    user: User | null
    login: (token: string, user: User) => void
    logout: () => void
    setUser: (user: User) => void
    isAuthenticated: () => boolean
    isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            token: null,
            user: null,
            login: (token, user) => set({ token, user }),
            logout: () => set({ token: null, user: null }),
            setUser: (user) => set({ user }),
            isAuthenticated: () => !!get().token,
            isAdmin: () => get().user?.role === 'ADMIN',
        }),
        {
            name: 'auth-storage',
        }
    )
)

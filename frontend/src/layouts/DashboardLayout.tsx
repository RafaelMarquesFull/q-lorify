import { Link, useLocation } from "react-router-dom"
import { Bot, LayoutDashboard, Settings, Key, DollarSign, LogOut, Wallet, Cpu, LineChart, Scale } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import api from "@/lib/api"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"
import Logotipo from "@/assets/logotipo.png"

function SidebarBalance() {
    const [balance, setBalance] = useState<number | null>(null)

    useEffect(() => {
        const fetchBalance = () => {
            api.get("/billing/balance")
                .then(res => setBalance(res.data.balance))
                .catch(err => console.error("Failed to fetch balance", err))
        }

        fetchBalance()
        const interval = setInterval(fetchBalance, 30000)
        return () => clearInterval(interval)
    }, [])

    if (balance === null) return null

    return (
        <div className="px-4 mb-4 hidden lg:block">
            <Card className="glass-ultra border-primary/20 shadow-glow-primary relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                <CardContent className="p-4 flex items-center justify-between relative z-10">
                    <div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-1">Saldo Disponível</p>
                        <p className="text-lg font-bold bg-gradient-to-r from-foreground to-foreground/60 bg-clip-text text-transparent font-mono">
                            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(balance)}
                        </p>
                    </div>
                    <div className="p-2.5 rounded-xl bg-primary/10 ring-2 ring-primary/20 group-hover:ring-primary/40 group-hover:scale-110 transition-all duration-300">
                        <Wallet className="h-5 w-5 text-primary" />
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const location = useLocation()
    const logout = useAuthStore((state) => state.logout)
    const user = useAuthStore((state) => state.user)

    const links = [
        { href: "/dashboard", label: "Visão Geral", icon: LayoutDashboard },
        { href: "/dashboard/playground", label: "Playground", icon: Bot },
        { href: "/dashboard/analytics", label: "Analytics", icon: LineChart },
        { href: "/dashboard/models", label: "Modelos", icon: Cpu },
        { href: "/dashboard/functions", label: "Weights", icon: Scale },
        { href: "/dashboard/keys", label: "Chaves API", icon: Key },
        { href: "/dashboard/billing", label: "Faturamento", icon: DollarSign },
        { href: "/dashboard/settings", label: "Configurações", icon: Settings },
    ]

    return (
        <AnimatedGradientBg variant="subtle" className="h-screen overflow-hidden">
            <div className="h-screen flex">
                {/* Floating Sidebar with Advanced Glassmorphism */}
                <aside className="w-72 m-4 rounded-3xl glass-ultra border-white/20 flex flex-col shadow-xl-colored backdrop-blur-xl">
                    {/* Header */}
                    <div className="h-20 flex items-center justify-center px-6 border-b border-white/10 glass-ultra rounded-t-3xl">
                        <div className="p-2 ">
                            <img src={Logotipo} alt="Logo" className="h-14 md:min-w-36 " />
                        </div>

                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                        {links.map((link) => {
                            const Icon = link.icon
                            const active = location.pathname === link.href
                            return (
                                <Link key={link.href} to={link.href}>
                                    <div className={`
                                        group relative flex items-center gap-3 px-4 py-3 rounded-xl 
                                        transition-all duration-300 my-2
                                        ${active
                                            ? 'bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-lg scale-[1.02]'
                                            : 'text-muted-foreground hover:text-foreground hover:bg-white/5 hover:scale-[1.01]'
                                        }
                                    `}>
                                        {active && (
                                            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary to-accent opacity-20 blur-xl" />
                                        )}

                                        <Icon className={`h-5 w-5 relative z-10 transition-transform duration-300 ${active ? '' : 'group-hover:scale-110'}`} />
                                        <span className="font-semibold relative z-10">{link.label}</span>

                                        <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-white/10 to-transparent shimmer" />
                                        </div>
                                    </div>
                                </Link>
                            )
                        })}
                    </nav>

                    <SidebarBalance />

                    {/* User Section */}
                    <div className="p-4 border-t border-white/10">
                        <div className="flex items-center gap-3 mb-4 px-2">
                            <div className="relative">
                                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-primary to-accent opacity-50 blur-sm animate-pulse" />
                                <Avatar className="h-11 w-11 relative ring-2 ring-primary/30 ring-offset-2 ring-offset-background">
                                    <AvatarFallback className="bg-gradient-to-br from-primary/20 to-accent/20 text-primary font-bold text-lg">
                                        {user?.name?.[0] || 'U'}
                                    </AvatarFallback>
                                </Avatar>
                            </div>
                            <div className="flex-1 overflow-hidden">
                                <p className="text-sm font-semibold truncate">{user?.name}</p>
                                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            className="w-full glass-floating hover:glass-ultra hover:scale-[1.02] transition-all duration-300 group"
                            onClick={logout}
                        >
                            <LogOut className="mr-2 h-4 w-4 group-hover:rotate-12 transition-transform duration-300" />
                            Logout
                        </Button>
                    </div>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 overflow-auto rounded-l-3xl my-4 mr-4 bg-background/30 backdrop-blur-sm">
                    <div className="p-1">
                        {children}
                    </div>
                </main>
            </div>
        </AnimatedGradientBg>
    )
}

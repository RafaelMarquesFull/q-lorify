import { Link, useLocation } from "react-router-dom"
import { LayoutDashboard, Users, Server, Cpu, Settings, LogOut, Zap } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import { Button } from "@/components/ui/button"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const location = useLocation()
    const logout = useAuthStore((state) => state.logout)

    const links = [
        { href: "/admin", label: "Overview", icon: LayoutDashboard },
        { href: "/admin/providers", label: "AI Providers", icon: Server },
        { href: "/admin/models", label: "AI Models", icon: Cpu },
        { href: "/admin/users", label: "Users", icon: Users },
        { type: "divider", label: "Orchestrator" },
        { href: "/admin/orchestrator/functions", label: "Funções", icon: Zap },
        { href: "/admin/sentiment", label: "Tester", icon: Zap },
        { type: "divider", label: "" },
        { href: "/admin/settings", label: "Settings", icon: Settings },
    ]

    return (
        <div className="h-screen overflow-hidden bg-gradient-to-br from-background via-background to-destructive/5 text-foreground flex">
            {/* Sidebar - Distinct Red accent for Admin */}
            <aside className="w-64 border-r border-destructive/20 flex flex-col bg-card/30 backdrop-blur-xl h-full flex-shrink-0">
                <div className="h-16 flex items-center px-6 border-b border-destructive/20 flex-shrink-0">
                    <span className="font-bold tracking-tight bg-gradient-to-r from-destructive to-destructive/60 bg-clip-text text-transparent">Admin Panel</span>
                </div>

                <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
                    {links.map((link, index) => {
                        if (link.type === "divider") {
                            return link.label ? (
                                <div key={index} className="pt-4 pb-2">
                                    <span className="px-3 text-xs font-semibold text-destructive/80 uppercase tracking-wider">{link.label}</span>
                                </div>
                            ) : <div key={index} className="py-2" />
                        }
                        const Icon = link.icon!
                        const active = location.pathname === link.href
                        return (
                            <Link key={link.href} to={link.href!}>
                                <div className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 my-2 ${active
                                    ? 'bg-destructive text-destructive-foreground shadow-md scale-[1.02]'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50 hover:scale-[1.01]'
                                    }`}>
                                    <Icon className="h-5 w-5" />
                                    <span className="font-medium">{link.label}</span>
                                </div>
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-destructive/20 flex-shrink-0">
                    <Button variant="outline" className="w-full border-destructive/30 hover:bg-destructive/10 text-destructive hover:text-destructive hover:border-destructive" onClick={logout}>
                        <LogOut className="mr-2 h-4 w-4" /> Logout
                    </Button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 h-full overflow-y-auto bg-zinc-950 custom-scrollbar">
                {children}
            </main>
        </div>
    )
}

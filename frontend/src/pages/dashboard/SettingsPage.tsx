import { useState } from "react"
import { useAuthStore } from "@/store/auth"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { User, Lock, Save, Shield } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

export default function SettingsPage() {
    const user = useAuthStore((state) => state.user)
    const setUser = useAuthStore((state) => state.setUser)

    // Profile State
    const [name, setName] = useState(user?.name || "")
    const [savingProfile, setSavingProfile] = useState(false)

    // Password State
    const [newPassword, setNewPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")
    const [savingPassword, setSavingPassword] = useState(false)

    async function handleUpdateProfile(e: React.FormEvent) {
        e.preventDefault()
        if (!name.trim()) return

        setSavingProfile(true)
        try {
            await api.post("/users/update", { name })
            toast.success("Perfil atualizado com sucesso")
            // Update local store
            if (user) {
                setUser({ ...user, name })
            }
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Erro ao atualizar perfil")
        } finally {
            setSavingProfile(false)
        }
    }

    async function handleUpdatePassword(e: React.FormEvent) {
        e.preventDefault()
        if (!newPassword || !confirmPassword) return

        if (newPassword !== confirmPassword) {
            toast.error("As senhas não coincidem")
            return
        }

        if (newPassword.length < 6) {
            toast.error("A senha deve ter pelo menos 6 caracteres")
            return
        }

        setSavingPassword(true)
        try {
            await api.post("/users/update", { password: newPassword })
            toast.success("Senha atualizada com sucesso")
            setNewPassword("")
            setConfirmPassword("")
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Erro ao atualizar senha")
        } finally {
            setSavingPassword(false)
        }
    }

    return (
        <AnimatedGradientBg className="p-8 space-y-8 min-h-full rounded-3xl">
            <div className="mb-4">
                <h2 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">Configurações</h2>
                <p className="text-muted-foreground mt-1">Gerencie suas preferências e informações de conta</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Profile Section */}
                <Card className="glass-ultra border-white/10 shadow-xl">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <User className="h-5 w-5 text-primary" />
                            Perfil
                        </CardTitle>
                        <CardDescription>
                            Atualize suas informações pessoais
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleUpdateProfile} className="space-y-4">
                            <div className="space-y-2">
                                <Label>Email</Label>
                                <Input
                                    value={user?.email || ""}
                                    disabled
                                    className="bg-white/5 border-white/10 text-white/50"
                                />
                                <p className="text-xs text-muted-foreground">O email não pode ser alterado.</p>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="name">Nome</Label>
                                <Input
                                    id="name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="bg-white/5 border-white/10 focus:border-primary/50 text-white"
                                />
                            </div>

                            <Button
                                type="submit"
                                disabled={savingProfile || name === user?.name}
                                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                            >
                                {savingProfile ? "Salvando..." : (
                                    <>
                                        <Save className="mr-2 h-4 w-4" /> Salvar Alterações
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Security Section */}
                <Card className="glass-ultra border-white/10 shadow-xl">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Shield className="h-5 w-5 text-primary" />
                            Segurança
                        </CardTitle>
                        <CardDescription>
                            Gerencie sua senha e acesso
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleUpdatePassword} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="new-password">Nova Senha</Label>
                                <Input
                                    id="new-password"
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="bg-white/5 border-white/10 focus:border-primary/50 text-white"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirm-password">Confirmar Senha</Label>
                                <Input
                                    id="confirm-password"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="bg-white/5 border-white/10 focus:border-primary/50 text-white"
                                />
                            </div>

                            <Button
                                type="submit"
                                disabled={savingPassword || !newPassword}
                                variant="outline"
                                className="w-full border-white/10 hover:bg-white/5 hover:text-white"
                            >
                                {savingPassword ? "Atualizando..." : (
                                    <>
                                        <Lock className="mr-2 h-4 w-4" /> Atualizar Senha
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </AnimatedGradientBg>
    )
}

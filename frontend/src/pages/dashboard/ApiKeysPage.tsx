import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Trash2, Copy, Key, AlertCircle, AlertTriangle } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"

interface ApiKey {
    id: string
    key: string
    name: string
    createdAt: string
}

export default function ApiKeysPage() {
    const [keys, setKeys] = useState<ApiKey[]>([])
    const [loading, setLoading] = useState(false)
    const [createOpen, setCreateOpen] = useState(false)
    const [keyName, setKeyName] = useState("")
    const [newKeyData, setNewKeyData] = useState<{ key: string, name: string } | null>(null)
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
    const [keyToDelete, setKeyToDelete] = useState<string | null>(null)

    useEffect(() => {
        fetchKeys()
    }, [])

    async function fetchKeys() {
        try {
            const res = await api.get("/keys")
            setKeys(res.data)
        } catch (error) {
            toast.error("Falha ao buscar chaves de API")
        }
    }

    async function createKey() {
        if (!keyName.trim()) {
            toast.error("Por favor, insira um nome para a chave")
            return
        }
        setLoading(true)
        try {
            const res = await api.post("/keys", { name: keyName })
            setNewKeyData(res.data)
            setCreateOpen(false)
            setKeyName("")
            fetchKeys()
            toast.success("Chave de API criada com sucesso")
        } catch (error: any) {
            const msg = error.response?.data?.error || "Falha ao criar chave de API"
            toast.error(msg)
        } finally {
            setLoading(false)
        }
    }

    function openDeleteConfirm(id: string) {
        setKeyToDelete(id)
        setDeleteConfirmOpen(true)
    }

    async function confirmRevoke() {
        if (!keyToDelete) return

        try {
            await api.delete(`/keys/${keyToDelete}`)
            toast.success("Chave revogada")
            fetchKeys()
        } catch (error) {
            toast.error("Falha ao revogar chave")
        } finally {
            setDeleteConfirmOpen(false)
            setKeyToDelete(null)
        }
    }

    function copyToClipboard(text: string) {
        navigator.clipboard.writeText(text)
        toast.success("Copiado para a área de transferência")
    }

    return (
        <AnimatedGradientBg className="p-8 space-y-8 min-h-full">
            <div className="flex items-center justify-between max-w-6xl mx-auto w-full">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Chaves de API</h2>
                    <p className="text-white/60 mt-2">Gerencie suas chaves secretas para acesso programático.</p>
                </div>
                <Button onClick={() => setCreateOpen(true)} className="bg-white text-black hover:bg-white/90">
                    <Plus className="mr-2 h-4 w-4" /> Criar Nova Chave
                </Button>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
                {keys.map((key) => (
                    <Card key={key.id} className="glass-subtle hover:bg-white/5 transition-all text-foreground flex flex-col justify-between group">
                        <CardHeader className="pb-2">
                            <div className="flex items-start justify-between">
                                <div className="p-2.5 bg-emerald-500/10 rounded-xl ring-1 ring-emerald-500/20 group-hover:ring-emerald-500/40 transition-all">
                                    <Key className="h-5 w-5 text-emerald-400" />
                                </div>
                                <Button variant="ghost" size="icon" onClick={() => openDeleteConfirm(key.id)} className="h-8 w-8 text-muted-foreground hover:text-red-400 -mr-2 -mt-2 hover:bg-red-500/10">
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                            <CardTitle className="mt-4 text-base font-medium">{key.name || "Chave Secreta"}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between bg-black/40 p-2.5 rounded-lg border border-white/5 text-xs font-mono text-muted-foreground group-hover:border-white/10 transition-colors">
                                {key.key}
                            </div>
                            <p className="text-xs text-muted-foreground/60 mt-3">Criado em: {new Date(key.createdAt).toLocaleDateString('pt-BR')}</p>
                        </CardContent>
                    </Card>
                ))}

                {keys.length === 0 && (
                    <div className="col-span-full py-12 text-center border border-dashed border-white/10 rounded-lg">
                        <Key className="h-10 w-10 text-white/20 mx-auto mb-4" />
                        <h3 className="text-lg font-medium">Nenhuma Chave de API Encontrada</h3>
                        <p className="text-white/50 text-sm mt-1">Crie uma chave para começar a construir com o AgentForge.</p>
                    </div>
                )}
            </div>

            {/* Create Key Dialog */}
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                <DialogContent className="glass-ultra border-white/10 text-foreground sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Criar Nova Chave de API</DialogTitle>
                        <DialogDescription className="text-white/60">
                            Escolha um nome amigável para identificar esta chave depois.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Nome da Chave</Label>
                            <Input
                                id="name"
                                placeholder="ex: App de Produção, Script de Teste"
                                value={keyName}
                                onChange={(e) => setKeyName(e.target.value)}
                                className="bg-zinc-900 border-white/10 text-white"
                            />
                        </div>
                        <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-md flex items-start gap-3">
                            <AlertCircle className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
                            <p className="text-xs text-blue-200">
                                Nota: Você precisa ter saldo positivo para gerar novas chaves.
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setCreateOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                        <Button onClick={createKey} disabled={loading} className="bg-white text-black hover:bg-white/90">
                            {loading ? "Criando..." : "Criar Chave Secreta"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Success Dialog */}
            <Dialog open={!!newKeyData} onOpenChange={(open) => !open && setNewKeyData(null)}>
                <DialogContent className="glass-ultra border-white/10 text-foreground sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-emerald-400">
                            <Key className="h-5 w-5" /> Chave Criada com Sucesso
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Por favor, copie sua nova Chave de API. <strong>Você não poderá vê-la novamente!</strong>
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-1">
                            <Label className="text-xs uppercase tracking-wider text-white/40">{newKeyData?.name}</Label>
                            <div className="flex items-center space-x-2">
                                <Input value={newKeyData?.key || ""} readOnly className="font-mono bg-emerald-500/10 border-emerald-500/20 text-emerald-200" />
                                <Button size="icon" variant="secondary" onClick={() => newKeyData && copyToClipboard(newKeyData.key)} className="hover:bg-white/20">
                                    <Copy className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    </div>
                    <DialogFooter className="sm:justify-start">
                        <Button type="button" onClick={() => setNewKeyData(null)} className="w-full bg-white text-black hover:bg-white/90">
                            Eu salvei esta chave
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <DialogContent className="glass-ultra border-white/10 text-foreground sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-red-400">
                            <AlertTriangle className="h-5 w-5" /> Revogar Chave de API
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Tem certeza que deseja revogar esta chave? Esta ação <strong>não pode ser desfeita</strong> e quebrará imediatamente quaisquer aplicações usando esta chave.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)} className="border-white/10 text-white hover:bg-white/10">
                            Cancelar
                        </Button>
                        <Button onClick={confirmRevoke} className="bg-red-600 text-white hover:bg-red-700">
                            Sim, Revogar Chave
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AnimatedGradientBg>
    )
}

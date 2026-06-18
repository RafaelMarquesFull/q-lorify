import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"

import { Card, CardContent } from "@/components/ui/card"
import { Plus, Users, Edit, Trash2, AlertTriangle, Key, RefreshCw, Copy, Check } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

interface OrchClient {
    id: string
    name: string
    token: string
    enabled: boolean
    rateLimit: number
    allowedFunctions: string[] | null
    allowedModels: string[] | null
    requestCount: number
    lastRequestAt: string | null
    createdAt: string
}

export default function OrchestratorClientsPage() {
    const [clients, setClients] = useState<OrchClient[]>([])
    const [createOpen, setCreateOpen] = useState(false)
    const [editOpen, setEditOpen] = useState(false)
    const [deleteOpen, setDeleteOpen] = useState(false)
    const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const [editingClient, setEditingClient] = useState<OrchClient | null>(null)
    const [deleteId, setDeleteId] = useState<string | null>(null)
    const [newToken, setNewToken] = useState("")
    const [copiedToken, setCopiedToken] = useState(false)

    // Form state
    const [name, setName] = useState("")
    const [rateLimit, setRateLimit] = useState("100")
    const [enabled, setEnabled] = useState(true)

    useEffect(() => {
        fetchClients()
    }, [])

    async function fetchClients() {
        try {
            const res = await api.get("/admin/orchestrator/clients")
            setClients(res.data)
        } catch {
            toast.error("Falha ao carregar clientes")
        }
    }

    function resetForm() {
        setName("")
        setRateLimit("100")
        setEnabled(true)
        setEditingClient(null)
    }

    function openEdit(client: OrchClient) {
        setEditingClient(client)
        setName(client.name)
        setRateLimit(String(client.rateLimit))
        setEnabled(client.enabled)
        setEditOpen(true)
    }

    async function handleCreate() {
        if (!name) {
            toast.error("Nome é obrigatório")
            return
        }
        setLoading(true)
        try {
            const res = await api.post("/admin/orchestrator/clients", {
                name,
                rateLimit: parseInt(rateLimit),
                enabled
            })
            // Show the token
            setNewToken(res.data.token)
            setTokenDialogOpen(true)
            setCreateOpen(false)
            resetForm()
            fetchClients()
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao criar cliente")
        } finally {
            setLoading(false)
        }
    }

    async function handleUpdate() {
        if (!editingClient) return
        setLoading(true)
        try {
            await api.patch("/admin/orchestrator/clients", {
                id: editingClient.id,
                name,
                rateLimit: parseInt(rateLimit),
                enabled
            })
            toast.success("Cliente atualizado")
            setEditOpen(false)
            resetForm()
            fetchClients()
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao atualizar cliente")
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete() {
        if (!deleteId) return
        try {
            await api.delete("/admin/orchestrator/clients", { data: { id: deleteId } })
            toast.success("Cliente removido")
            setDeleteOpen(false)
            setDeleteId(null)
            fetchClients()
        } catch {
            toast.error("Erro ao remover cliente")
        }
    }

    async function regenerateToken(clientId: string) {
        try {
            const res = await api.post(`/admin/orchestrator/clients/${clientId}/regenerate-token`)
            setNewToken(res.data.token)
            setTokenDialogOpen(true)
            fetchClients()
        } catch {
            toast.error("Erro ao regenerar token")
        }
    }

    async function toggleEnabled(client: OrchClient) {
        try {
            await api.patch("/admin/orchestrator/clients", {
                id: client.id,
                enabled: !client.enabled
            })
            toast.success(`Cliente ${!client.enabled ? "ativado" : "desativado"}`)
            fetchClients()
        } catch {
            toast.error("Erro ao atualizar cliente")
        }
    }

    function copyToken() {
        navigator.clipboard.writeText(newToken)
        setCopiedToken(true)
        setTimeout(() => setCopiedToken(false), 2000)
        toast.success("Token copiado!")
    }

    return (
        <div className="p-8 space-y-8 text-white">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Clientes Orchestrator</h2>
                    <p className="text-white/60 mt-1">Gerencie tokens e permissões de acesso</p>
                </div>
                <Dialog open={createOpen} onOpenChange={(o) => { setCreateOpen(o); if (!o) resetForm() }}>
                    <DialogTrigger asChild>
                        <Button className="bg-white text-black hover:bg-white/90">
                            <Plus className="mr-2 h-4 w-4" /> Novo Cliente
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <Users className="h-5 w-5" /> Novo Cliente
                            </DialogTitle>
                            <DialogDescription className="text-white/60">
                                Um token será gerado automaticamente
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label className="text-right text-white">Nome</Label>
                                <Input
                                    placeholder="n8n-production"
                                    value={name}
                                    onChange={e => setName(e.target.value)}
                                    className="col-span-3 bg-white/5 border-white/10 text-white"
                                />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label className="text-right text-white">Rate Limit</Label>
                                <div className="col-span-3 flex items-center gap-2">
                                    <Input
                                        type="number"
                                        value={rateLimit}
                                        onChange={e => setRateLimit(e.target.value)}
                                        className="bg-white/5 border-white/10 text-white"
                                    />
                                    <span className="text-white/50 text-sm">/min</span>
                                </div>
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label className="text-right text-white">Ativo</Label>
                                <div className="col-span-3 flex items-center gap-2">
                                    <Switch checked={enabled} onCheckedChange={setEnabled} />
                                </div>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setCreateOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                            <Button onClick={handleCreate} disabled={loading} className="bg-white text-black hover:bg-white/90">
                                {loading ? "Criando..." : "Criar"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            <Card className="bg-zinc-950 border-white/10">
                <CardContent className="p-0">
                    <Table>
                        <TableHeader className="bg-white/5">
                            <TableRow className="border-white/10 hover:bg-transparent">
                                <TableHead className="text-white">Cliente</TableHead>
                                <TableHead className="text-white">Token</TableHead>
                                <TableHead className="text-white">Rate Limit</TableHead>
                                <TableHead className="text-white">Requisições</TableHead>
                                <TableHead className="text-white">Status</TableHead>
                                <TableHead className="text-right text-white">Ações</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {clients.map(client => (
                                <TableRow key={client.id} className="border-white/10 hover:bg-white/5">
                                    <TableCell>
                                        <div className="flex items-center gap-3">
                                            <Key className="h-4 w-4 text-white/50" />
                                            <span className="font-medium">{client.name}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <code className="text-xs bg-white/5 px-2 py-1 rounded text-white/60">
                                            {client.token}
                                        </code>
                                    </TableCell>
                                    <TableCell>
                                        <span className="text-white/60">{client.rateLimit}/min</span>
                                    </TableCell>
                                    <TableCell>
                                        <span className="text-white/60">{client.requestCount}</span>
                                    </TableCell>
                                    <TableCell>
                                        <Switch
                                            checked={client.enabled}
                                            onCheckedChange={() => toggleEnabled(client)}
                                        />
                                    </TableCell>
                                    <TableCell className="text-right space-x-1">
                                        <Button variant="ghost" size="icon" onClick={() => regenerateToken(client.id)} className="text-white/50 hover:text-amber-400" title="Regenerar Token">
                                            <RefreshCw className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" onClick={() => openEdit(client)} className="text-white/50 hover:text-white">
                                            <Edit className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" onClick={() => { setDeleteId(client.id); setDeleteOpen(true) }} className="text-white/50 hover:text-red-400">
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {clients.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-8 text-white/50">
                                        Nenhum cliente registrado
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={(o) => { setEditOpen(o); if (!o) resetForm() }}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Editar Cliente</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label className="text-right text-white">Nome</Label>
                            <Input
                                value={name}
                                onChange={e => setName(e.target.value)}
                                className="col-span-3 bg-white/5 border-white/10 text-white"
                            />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label className="text-right text-white">Rate Limit</Label>
                            <div className="col-span-3 flex items-center gap-2">
                                <Input
                                    type="number"
                                    value={rateLimit}
                                    onChange={e => setRateLimit(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white"
                                />
                                <span className="text-white/50 text-sm">/min</span>
                            </div>
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label className="text-right text-white">Ativo</Label>
                            <Switch checked={enabled} onCheckedChange={setEnabled} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                        <Button onClick={handleUpdate} disabled={loading} className="bg-white text-black hover:bg-white/90">
                            {loading ? "Salvando..." : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Token Dialog */}
            <Dialog open={tokenDialogOpen} onOpenChange={setTokenDialogOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-emerald-400">
                            <Key className="h-5 w-5" /> Token Gerado
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Copie e guarde este token. Ele não será exibido novamente.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                        <div className="flex items-center gap-2">
                            <code className="flex-1 bg-white/5 px-4 py-3 rounded text-sm font-mono text-emerald-400 break-all">
                                {newToken}
                            </code>
                            <Button variant="outline" size="icon" onClick={copyToken} className="border-white/10 text-white hover:bg-white/10">
                                {copiedToken ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                            </Button>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={() => setTokenDialogOpen(false)} className="bg-white text-black hover:bg-white/90">
                            Entendido
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Dialog */}
            <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-red-400">
                            <AlertTriangle className="h-5 w-5" /> Remover Cliente
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Tem certeza? O token será invalidado imediatamente.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                        <Button onClick={handleDelete} className="bg-red-600 text-white hover:bg-red-700">Remover</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

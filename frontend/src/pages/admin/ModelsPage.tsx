import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Plus, Cpu, Trash2, Edit, Shield, AlertTriangle, Zap, Clock, BrainCircuit, Eye } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

interface Model {
    id: string
    name: string
    providerModelId: string
    providerId: string
    provider: string
    costIn: number
    costOut: number
    isOrchestrator: boolean
    isSentiment: boolean
    description: string | null
    rpm: number
    isPublic: boolean
    fallback1Id: string | null
    fallback2Id: string | null
    fallback3Id: string | null
    fallback1Name: string | null
    fallback2Name: string | null
    fallback3Name: string | null
}

interface Provider {
    id: string
    name: string
}

export default function ModelsPage() {
    const [models, setModels] = useState<Model[]>([])
    const [providers, setProviders] = useState<Provider[]>([])
    const [loading, setLoading] = useState(false)
    const [createOpen, setCreateOpen] = useState(false)
    const [editOpen, setEditOpen] = useState(false)
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
    const [modelToDelete, setModelToDelete] = useState<string | null>(null)

    // Form State
    const [editingModel, setEditingModel] = useState<Model | null>(null)
    const [name, setName] = useState("")
    const [providerModelId, setProviderModelId] = useState("")
    const [providerId, setProviderId] = useState("")
    const [costIn, setCostIn] = useState("0")
    const [costOut, setCostOut] = useState("0")
    const [isOrchestrator, setIsOrchestrator] = useState(false)
    const [isSentiment, setIsSentiment] = useState(false)
    const [description, setDescription] = useState("")
    const [rpm, setRpm] = useState("60")
    const [isPublic, setIsPublic] = useState(true)
    const [fallback1Id, setFallback1Id] = useState("")
    const [fallback2Id, setFallback2Id] = useState("")
    const [fallback3Id, setFallback3Id] = useState("")

    useEffect(() => {
        fetchData()
    }, [])

    async function fetchData() {
        try {
            const [resModels, resProviders] = await Promise.all([
                api.get("/admin/models"),
                api.get("/admin/providers")
            ])
            setModels(resModels.data)
            setProviders(resProviders.data)
        } catch (error) {
            toast.error("Falha ao carregar dados")
        }
    }

    function resetForm() {
        setName("")
        setProviderModelId("")
        setProviderId("")
        setCostIn("0")
        setCostOut("0")
        setIsOrchestrator(false)
        setIsSentiment(false)
        setDescription("")
        setRpm("60")
        setIsPublic(true)
        setFallback1Id("")
        setFallback2Id("")
        setFallback3Id("")
        setEditingModel(null)
    }

    function openEditDialog(model: Model) {
        setEditingModel(model)
        setName(model.name)
        setProviderModelId(model.providerModelId || "")
        setProviderId(model.providerId)
        setCostIn(String(model.costIn || 0))
        setCostOut(String(model.costOut || 0))
        setIsOrchestrator(model.isOrchestrator || false)
        setIsSentiment(model.isSentiment || false)
        setDescription(model.description || "")
        setRpm(String(model.rpm || 60))
        setIsPublic(model.isPublic !== false)
        setFallback1Id(model.fallback1Id || "")
        setFallback2Id(model.fallback2Id || "")
        setFallback3Id(model.fallback3Id || "")
        setEditOpen(true)
    }

    async function handleCreate() {
        if (!name || !providerId) {
            toast.error("Nome e Provedor são obrigatórios")
            return
        }

        setLoading(true)
        try {
            await api.post("/admin/models", {
                name,
                providerModelId: providerModelId || name,
                providerId,
                costIn: parseFloat(costIn),
                costOut: parseFloat(costOut),
                isOrchestrator,
                isSentiment,
                description: description || null,
                rpm: parseInt(rpm),
                isPublic,
                fallback1Id: fallback1Id && fallback1Id !== "_none" ? fallback1Id : null,
                fallback2Id: fallback2Id && fallback2Id !== "_none" ? fallback2Id : null,
                fallback3Id: fallback3Id && fallback3Id !== "_none" ? fallback3Id : null
            })
            toast.success("Modelo criado com sucesso")
            setCreateOpen(false)
            resetForm()
            fetchData()
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao criar modelo")
        } finally {
            setLoading(false)
        }
    }

    async function handleUpdate() {
        if (!editingModel) return

        setLoading(true)
        try {
            await api.patch("/admin/models", {
                id: editingModel.id,
                name,
                providerModelId: providerModelId || name,
                providerId,
                costIn: parseFloat(costIn),
                costOut: parseFloat(costOut),
                isOrchestrator,
                isSentiment,
                description: description || null,
                rpm: parseInt(rpm),
                isPublic,
                fallback1Id: fallback1Id && fallback1Id !== "_none" ? fallback1Id : null,
                fallback2Id: fallback2Id && fallback2Id !== "_none" ? fallback2Id : null,
                fallback3Id: fallback3Id && fallback3Id !== "_none" ? fallback3Id : null
            })
            toast.success("Modelo atualizado")
            setEditOpen(false)
            resetForm()
            fetchData()
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao atualizar modelo")
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete() {
        if (!modelToDelete) return

        try {
            await api.delete("/admin/models", { data: { id: modelToDelete } })
            toast.success("Modelo removido")
            setDeleteConfirmOpen(false)
            setModelToDelete(null)
            fetchData()
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao remover modelo")
        }
    }

    function getFallbackCount(model: Model): number {
        let count = 0
        if (model.fallback1Id) count++
        if (model.fallback2Id) count++
        if (model.fallback3Id) count++
        return count
    }

    // Filter out current model and already selected fallbacks for dropdown options
    function getAvailableFallbacks(currentModelId: string | null, exclude: string[]) {
        return models.filter(m =>
            m.id !== currentModelId &&
            !exclude.includes(m.id)
        )
    }


    const modelFormFields = (
        <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Nome</Label>
                <Input
                    placeholder="GPT-4 Turbo"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">ID do Modelo</Label>
                <Input
                    placeholder="gpt-4-turbo-preview"
                    value={providerModelId}
                    onChange={e => setProviderModelId(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
                <span className="col-start-2 col-span-3 text-xs text-white/40">
                    ID enviado para a API do provedor
                </span>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Provedor</Label>
                <Select value={providerId} onValueChange={setProviderId}>
                    <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white">
                        <SelectValue placeholder="Selecione o Provedor" />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-950 border-white/10 text-white">
                        {providers.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Custo Input</Label>
                <Input
                    type="number"
                    step="0.000001"
                    value={costIn}
                    onChange={e => setCostIn(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Custo Output</Label>
                <Input
                    type="number"
                    step="0.000001"
                    value={costOut}
                    onChange={e => setCostOut(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>

            {/* Rate Limit Section */}
            <div className="border-t border-white/10 pt-4 mt-2">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right flex items-center gap-2">
                        <Clock className="h-4 w-4 text-amber-400" />
                        Rate Limit (RPM)
                    </Label>
                    <div className="col-span-3 flex items-center gap-3">
                        <Input
                            type="number"
                            min="0"
                            value={rpm}
                            onChange={e => setRpm(e.target.value)}
                            className="w-32 bg-white/5 border-white/10 text-white"
                        />
                        <span className="text-sm text-white/60">
                            requisições/minuto (0 = sem limite)
                        </span>
                    </div>
                </div>
            </div>

            {/* Orchestrator Model Section */}
            <div className="border-t border-white/10 pt-4 mt-2">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right flex items-center gap-2">
                        <Zap className="h-4 w-4 text-purple-400" />
                        Orquestrador
                    </Label>
                    <div className="col-span-3 flex items-center gap-3">
                        <Switch checked={isOrchestrator} onCheckedChange={setIsOrchestrator} />
                        <span className="text-sm text-white/60">
                            {isOrchestrator ? "Este modelo usa as funções do usuário" : "Modelo padrão"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Sentiment Model Section */}
            <div className="border-t border-white/10 pt-4 mt-2">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right flex items-center gap-2">
                        <BrainCircuit className="h-4 w-4 text-pink-400" />
                        Sentimento
                    </Label>
                    <div className="col-span-3 flex items-center gap-3">
                        <Switch checked={isSentiment} onCheckedChange={setIsSentiment} />
                        <span className="text-sm text-white/60">
                            {isSentiment ? "Habilitado para análise de sentimento" : "Não classificado como sentimento"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Public Model Section */}
            <div className="border-t border-white/10 pt-4 mt-2">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right flex items-center gap-2">
                        <Eye className="h-4 w-4 text-blue-400" />
                        Público
                    </Label>
                    <div className="col-span-3 flex items-center gap-3">
                        <Switch checked={isPublic} onCheckedChange={setIsPublic} />
                        <span className="text-sm text-white/60">
                            {isPublic ? "Visível para clientes (Landing & Dashboard)" : "Oculto (Apenas uso interno/Agentes)"}
                        </span>
                    </div>
                </div>
            </div>

            {/* Fallback Chain Section */}
            <div className="border-t border-white/10 pt-4 mt-2">
                <div className="flex items-center gap-2 mb-3">
                    <Shield className="h-4 w-4 text-amber-400" />
                    <span className="text-sm font-medium">Cadeia de Fallback</span>
                </div>
                <p className="text-xs text-white/50 mb-4">
                    Se este modelo falhar, o sistema tentará os modelos abaixo em ordem.
                </p>

                <div className="space-y-3">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right text-amber-400/80">Fallback 1</Label>
                        <Select value={fallback1Id} onValueChange={setFallback1Id}>
                            <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white">
                                <SelectValue placeholder="Nenhum" />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                <SelectItem value="_none">Nenhum</SelectItem>
                                {getAvailableFallbacks(editingModel?.id || null, []).map(m => (
                                    <SelectItem key={m.id} value={m.id}>{m.name} ({m.provider})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right text-amber-400/60">Fallback 2</Label>
                        <Select value={fallback2Id} onValueChange={setFallback2Id} disabled={!fallback1Id || fallback1Id === "_none"}>
                            <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white disabled:opacity-50">
                                <SelectValue placeholder="Nenhum" />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                <SelectItem value="_none">Nenhum</SelectItem>
                                {getAvailableFallbacks(editingModel?.id || null, [fallback1Id]).map(m => (
                                    <SelectItem key={m.id} value={m.id}>{m.name} ({m.provider})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label className="text-right text-amber-400/40">Fallback 3</Label>
                        <Select value={fallback3Id} onValueChange={setFallback3Id} disabled={!fallback2Id || fallback2Id === "_none"}>
                            <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white disabled:opacity-50">
                                <SelectValue placeholder="Nenhum" />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                <SelectItem value="_none">Nenhum</SelectItem>
                                {getAvailableFallbacks(editingModel?.id || null, [fallback1Id, fallback2Id]).map(m => (
                                    <SelectItem key={m.id} value={m.id}>{m.name} ({m.provider})</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </div>
        </div>
    )

    return (
        <div className="p-8 space-y-8 text-white">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold tracking-tight">Modelos de IA</h2>
                <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) resetForm(); }}>
                    <DialogTrigger asChild>
                        <Button className="bg-white text-black hover:bg-white/90">
                            <Plus className="mr-2 h-4 w-4" /> Adicionar Modelo
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-[550px]">
                        <DialogHeader>
                            <DialogTitle>Adicionar Modelo de IA</DialogTitle>
                        </DialogHeader>
                        {modelFormFields}
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setCreateOpen(false)} className="border-white/10">Cancelar</Button>
                            <Button onClick={handleCreate} disabled={loading} className="bg-white text-black hover:bg-white/90">
                                {loading ? "Criando..." : "Criar"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="rounded-md border border-white/10">
                <Table>
                    <TableHeader className="bg-white/5">
                        <TableRow className="border-white/10 hover:bg-transparent">
                            <TableHead className="text-white">Nome</TableHead>
                            <TableHead className="text-white">ID do Modelo</TableHead>
                            <TableHead className="text-white">Provedor</TableHead>
                            <TableHead className="text-white">Custo (In/Out)</TableHead>
                            <TableHead className="text-white">Fallbacks</TableHead>
                            <TableHead className="text-right text-white">Ações</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {models.map((model) => (
                            <TableRow key={model.id} className="border-white/10 hover:bg-white/5">
                                <TableCell className="font-medium">
                                    <div className="flex items-center gap-2">
                                        <Cpu className="h-4 w-4 text-white/50" />
                                        {model.name}
                                        {model.isOrchestrator && (
                                            <Badge className="bg-purple-500/20 text-purple-400 ml-2">
                                                <Zap className="h-3 w-3 mr-1" />
                                                Funções
                                            </Badge>
                                        )}
                                        {model.isSentiment && (
                                            <Badge className="bg-pink-500/20 text-pink-400 ml-2">
                                                <BrainCircuit className="h-3 w-3 mr-1" />
                                                Sentimento
                                            </Badge>
                                        )}
                                        {!model.isPublic && (
                                            <Badge className="bg-zinc-500/20 text-zinc-400 ml-2">
                                                <Eye className="h-3 w-3 mr-1" />
                                                Interno
                                            </Badge>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell className="font-mono text-xs text-white/60">
                                    {model.providerModelId}
                                </TableCell>
                                <TableCell>{model.provider}</TableCell>
                                <TableCell className="text-white/50 font-mono text-xs">
                                    ${model.costIn} / ${model.costOut}
                                </TableCell>
                                <TableCell>
                                    {getFallbackCount(model) > 0 ? (
                                        <Badge className="bg-amber-500/20 text-amber-400 hover:bg-amber-500/30">
                                            <Shield className="h-3 w-3 mr-1" />
                                            {getFallbackCount(model)} fallback{getFallbackCount(model) > 1 ? 's' : ''}
                                        </Badge>
                                    ) : (
                                        <span className="text-white/30 text-xs">Nenhum</span>
                                    )}
                                </TableCell>
                                <TableCell className="text-right space-x-1">
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="text-white/50 hover:text-white"
                                        onClick={() => openEditDialog(model)}
                                    >
                                        <Edit className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="text-white/50 hover:text-red-400"
                                        onClick={() => { setModelToDelete(model.id); setDeleteConfirmOpen(true); }}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                        {models.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} className="text-center py-8 text-white/50">
                                    Nenhum modelo encontrado
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={(open) => { setEditOpen(open); if (!open) resetForm(); }}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-[550px]">
                    <DialogHeader>
                        <DialogTitle>Editar Modelo</DialogTitle>
                    </DialogHeader>
                    {modelFormFields}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)} className="border-white/10">Cancelar</Button>
                        <Button onClick={handleUpdate} disabled={loading} className="bg-white text-black hover:bg-white/90">
                            {loading ? "Salvando..." : "Salvar Alterações"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-red-400">
                            <AlertTriangle className="h-5 w-5" /> Remover Modelo
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Tem certeza que deseja remover este modelo? Esta ação não pode ser desfeita.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)} className="border-white/10">Cancelar</Button>
                        <Button onClick={handleDelete} className="bg-red-600 text-white hover:bg-red-700">
                            Sim, Remover
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

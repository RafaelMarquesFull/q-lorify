import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Plus, Zap, Edit, Trash2, AlertTriangle, Code, Clock, Cpu, Bot, Brain, RefreshCw, CheckCircle, XCircle, Eye } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

interface OrchFunction {
    id: string
    name: string
    displayName: string
    description: string | null
    enabled: boolean
    pricePerUnit: number
    unitSize: number
    requiresAi: boolean
    timeout: number
    defaultModelId: string | null
    createdAt: string
}

interface AIModel {
    id: string
    name: string
    provider: string
}

interface Agent {
    id: string
    name: string
    systemPrompt: string
    systemPromptFull: string
    modelId: string
    modelName: string | null
    rulesModelId: string | null
    rulesVersion: number
    rulesCompiledAt: string | null
    hasRules: boolean
    promptHash: string | null
    createdAt: string
}

export default function OrchestratorFunctionsPage() {
    const [functions, setFunctions] = useState<OrchFunction[]>([])
    const [createOpen, setCreateOpen] = useState(false)
    const [editOpen, setEditOpen] = useState(false)
    const [deleteOpen, setDeleteOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const [editingFunc, setEditingFunc] = useState<OrchFunction | null>(null)
    const [deleteId, setDeleteId] = useState<string | null>(null)

    // Form state
    const [name, setName] = useState("")
    const [displayName, setDisplayName] = useState("")
    const [description, setDescription] = useState("")
    const [pricePerUnit, setPricePerUnit] = useState("0")
    const [unitSize, setUnitSize] = useState("1000")
    const [timeout, setTimeout] = useState("30000")
    const [requiresAi, setRequiresAi] = useState(false)
    const [enabled, setEnabled] = useState(true)
    const [defaultModelId, setDefaultModelId] = useState("")

    // AI Models
    const [models, setModels] = useState<AIModel[]>([])

    // ── Agents & Rules state ──
    const [agents, setAgents] = useState<Agent[]>([])
    const [compilingId, setCompilingId] = useState<string | null>(null)
    const [rulesPreview, setRulesPreview] = useState<any>(null)
    const [rulesPreviewOpen, setRulesPreviewOpen] = useState(false)
    const [promptPreview, setPromptPreview] = useState<string | null>(null)
    const [promptPreviewOpen, setPromptPreviewOpen] = useState(false)
    const [globalRulesModelId, setGlobalRulesModelId] = useState<string | null>(null)
    const [globalRulesModelName, setGlobalRulesModelName] = useState<string | null>(null)

    useEffect(() => {
        fetchFunctions()
        fetchModels()
        fetchAgents()
        fetchGlobalRulesModel()
    }, [])

    async function fetchModels() {
        try {
            const res = await api.get("/admin/models")
            setModels(res.data)
        } catch {
            console.error("Failed to load models")
        }
    }

    async function fetchFunctions() {
        try {
            const res = await api.get("/admin/orchestrator/functions")
            setFunctions(res.data)
        } catch {
            toast.error("Falha ao carregar funções")
        }
    }

    // ── Agents & Global Rules Model ──
    async function fetchAgents() {
        try {
            const res = await api.get("/admin/agents")
            setAgents(res.data)
        } catch {
            console.error("Failed to load agents")
        }
    }

    async function fetchGlobalRulesModel() {
        try {
            const res = await api.get("/admin/settings/rules-model")
            setGlobalRulesModelId(res.data.rulesModelId)
            setGlobalRulesModelName(res.data.modelName)
        } catch {
            console.error("Failed to load global rules model")
        }
    }

    async function handleSetGlobalRulesModel(modelId: string) {
        try {
            const res = await api.post("/admin/settings/rules-model", { rulesModelId: modelId })
            setGlobalRulesModelId(res.data.rulesModelId)
            setGlobalRulesModelName(res.data.modelName)
            toast.success(`Modelo de extração definido: ${res.data.modelName}`)
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao definir modelo")
        }
    }

    async function handleCompileRules(agentId: string) {
        setCompilingId(agentId)
        try {
            const res = await api.post(`/admin/agents/${agentId}/compile-rules`)
            toast.success(`Regras compiladas! ${res.data.rules_count} regras, v${res.data.version}`)
            fetchAgents()
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro na compilação")
        } finally {
            setCompilingId(null)
        }
    }

    async function handleViewRules(agentId: string) {
        try {
            const res = await api.get(`/admin/agents/${agentId}/rules`)
            setRulesPreview(res.data)
            setRulesPreviewOpen(true)
        } catch {
            toast.error("Erro ao carregar regras")
        }
    }

    function resetForm() {
        setName("")
        setDisplayName("")
        setDescription("")
        setPricePerUnit("0")
        setUnitSize("1000")
        setTimeout("30000")
        setRequiresAi(false)
        setEnabled(true)
        setDefaultModelId("")
        setEditingFunc(null)
    }

    function openEdit(func: OrchFunction) {
        setEditingFunc(func)
        setName(func.name)
        setDisplayName(func.displayName)
        setDescription(func.description || "")
        setPricePerUnit(String(func.pricePerUnit || 0))
        setUnitSize(String(func.unitSize || 1000))
        setTimeout(String(func.timeout))
        setRequiresAi(func.requiresAi)
        setEnabled(func.enabled)
        setDefaultModelId(func.defaultModelId || "")
        setEditOpen(true)
    }

    async function handleCreate() {
        if (!name) {
            toast.error("Nome é obrigatório")
            return
        }
        setLoading(true)
        try {
            await api.post("/admin/orchestrator/functions", {
                name,
                displayName: displayName || name,
                description: description || null,
                pricePerUnit: parseFloat(pricePerUnit) || 0,
                unitSize: parseInt(unitSize) || 1000,
                timeout: parseInt(timeout),
                requiresAi,
                enabled,
                defaultModelId: requiresAi && defaultModelId ? defaultModelId : null
            })
            toast.success("Função criada")
            setCreateOpen(false)
            resetForm()
            fetchFunctions()
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao criar função")
        } finally {
            setLoading(false)
        }
    }

    async function handleUpdate() {
        if (!editingFunc) return
        setLoading(true)
        try {
            await api.patch("/admin/orchestrator/functions", {
                id: editingFunc.id,
                name,
                displayName,
                description: description || null,
                pricePerUnit: parseFloat(pricePerUnit) || 0,
                unitSize: parseInt(unitSize) || 1000,
                timeout: parseInt(timeout),
                requiresAi,
                enabled,
                defaultModelId: requiresAi && defaultModelId ? defaultModelId : null
            })
            toast.success("Função atualizada")
            setEditOpen(false)
            resetForm()
            fetchFunctions()
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao atualizar função")
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete() {
        if (!deleteId) return
        try {
            await api.delete("/admin/orchestrator/functions", { data: { id: deleteId } })
            toast.success("Função removida")
            setDeleteOpen(false)
            setDeleteId(null)
            fetchFunctions()
        } catch {
            toast.error("Erro ao remover função")
        }
    }

    async function toggleEnabled(func: OrchFunction) {
        try {
            await api.patch("/admin/orchestrator/functions", {
                id: func.id,
                enabled: !func.enabled
            })
            toast.success(`Função ${!func.enabled ? "ativada" : "desativada"}`)
            fetchFunctions()
        } catch {
            toast.error("Erro ao atualizar função")
        }
    }

    // Format pricing display
    function formatPricing(price: number, unit: number): string {
        if (price === 0) return "Grátis"
        return `R$ ${price.toFixed(2)} / ${unit} req`
    }


    const formFields = (
        <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Nome (ID)</Label>
                <Input
                    placeholder="extract_cep"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white font-mono"
                    disabled={!!editingFunc}
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Nome Exibição</Label>
                <Input
                    placeholder="Extrator de CEP"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Descrição</Label>
                <Input
                    placeholder="Extrai CEPs do texto"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Preço (R$)</Label>
                <Input
                    type="number"
                    step="0.01"
                    placeholder="0.25"
                    value={pricePerUnit}
                    onChange={e => setPricePerUnit(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Por Qtd</Label>
                <div className="col-span-3 flex items-center gap-2">
                    <Input
                        type="number"
                        placeholder="1000"
                        value={unitSize}
                        onChange={e => setUnitSize(e.target.value)}
                        className="bg-white/5 border-white/10 text-white"
                    />
                    <span className="text-white/50 text-sm">requisições</span>
                </div>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Timeout (ms)</Label>
                <Input
                    type="number"
                    value={timeout}
                    onChange={e => setTimeout(e.target.value)}
                    className="col-span-3 bg-white/5 border-white/10 text-white"
                />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Requer IA</Label>
                <div className="col-span-3 flex items-center gap-2">
                    <Switch checked={requiresAi} onCheckedChange={setRequiresAi} />
                    <span className="text-sm text-white/60">{requiresAi ? "Sim" : "Não"}</span>
                </div>
            </div>
            {requiresAi && (
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right text-white">Modelo IA</Label>
                    <Select value={defaultModelId} onValueChange={setDefaultModelId}>
                        <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white">
                            <SelectValue placeholder="Selecione um modelo..." />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-950 border-white/10 text-white max-h-60">
                            {models.map(model => (
                                <SelectItem key={model.id} value={model.id}>
                                    {model.name} <span className="text-white/40">({model.provider})</span>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}
            <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-white">Ativa</Label>
                <div className="col-span-3 flex items-center gap-2">
                    <Switch checked={enabled} onCheckedChange={setEnabled} />
                    <span className="text-sm text-white/60">{enabled ? "Sim" : "Não"}</span>
                </div>
            </div>
        </div>
    )


    return (
        <div className="p-8 space-y-6 text-white">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Orchestrator</h2>
                <p className="text-white/60 mt-1">Gerencie funções e agentes do orchestrator</p>
            </div>

            <Tabs defaultValue="functions" className="space-y-6">
                <TabsList className="bg-white/5 border border-white/10">
                    <TabsTrigger value="functions" className="data-[state=active]:bg-white data-[state=active]:text-black">
                        <Zap className="h-4 w-4 mr-2" /> Funções
                    </TabsTrigger>
                    <TabsTrigger value="agents" className="data-[state=active]:bg-white data-[state=active]:text-black">
                        <Bot className="h-4 w-4 mr-2" /> Agentes & Rules
                    </TabsTrigger>
                </TabsList>

                {/* ═══════════════ TAB: FUNÇÕES ═══════════════ */}
                <TabsContent value="functions" className="space-y-6">
                    <div className="flex justify-end">
                        <Dialog open={createOpen} onOpenChange={(o) => { setCreateOpen(o); if (!o) resetForm() }}>
                            <DialogTrigger asChild>
                                <Button className="bg-white text-black hover:bg-white/90">
                                    <Plus className="mr-2 h-4 w-4" /> Nova Função
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-lg">
                                <DialogHeader>
                                    <DialogTitle className="flex items-center gap-2">
                                        <Zap className="h-5 w-5" /> Nova Função
                                    </DialogTitle>
                                    <DialogDescription className="text-white/60">
                                        Registre uma nova função determinística
                                    </DialogDescription>
                                </DialogHeader>
                                {formFields}
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
                                        <TableHead className="text-white">Função</TableHead>
                                        <TableHead className="text-white">Custo</TableHead>
                                        <TableHead className="text-white">Timeout</TableHead>
                                        <TableHead className="text-white">IA</TableHead>
                                        <TableHead className="text-white">Status</TableHead>
                                        <TableHead className="text-right text-white">Ações</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {functions.map(func => (
                                        <TableRow key={func.id} className="border-white/10 hover:bg-white/5">
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Code className="h-4 w-4 text-white/50" />
                                                    <div>
                                                        <p className="font-medium">{func.displayName}</p>
                                                        <p className="text-xs text-white/50 font-mono">{func.name}</p>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge className="bg-emerald-500/20 text-emerald-400">
                                                    {formatPricing(func.pricePerUnit, func.unitSize)}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <span className="flex items-center gap-1 text-white/60">
                                                    <Clock className="h-3 w-3" />
                                                    {func.timeout}ms
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                {func.requiresAi ? (
                                                    <Badge className="bg-purple-500/20 text-purple-400">
                                                        <Cpu className="h-3 w-3 mr-1" /> IA
                                                    </Badge>
                                                ) : (
                                                    <span className="text-white/40">-</span>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Switch
                                                    checked={func.enabled}
                                                    onCheckedChange={() => toggleEnabled(func)}
                                                />
                                            </TableCell>
                                            <TableCell className="text-right space-x-1">
                                                <Button variant="ghost" size="icon" onClick={() => openEdit(func)} className="text-white/50 hover:text-white">
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button variant="ghost" size="icon" onClick={() => { setDeleteId(func.id); setDeleteOpen(true) }} className="text-white/50 hover:text-red-400">
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {functions.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={6} className="text-center py-8 text-white/50">
                                                Nenhuma função registrada
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ═══════════════ TAB: AGENTES & RULES ═══════════════ */}
                <TabsContent value="agents" className="space-y-6">
                    {/* Global Rules Model Selector */}
                    <Card className="bg-zinc-950 border-white/10">
                        <CardContent className="p-4">
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                    <Brain className="h-5 w-5 text-purple-400" />
                                    <Label className="text-white font-medium whitespace-nowrap">Modelo para Extração de Regras</Label>
                                </div>
                                <Select
                                    value={globalRulesModelId || ""}
                                    onValueChange={handleSetGlobalRulesModel}
                                >
                                    <SelectTrigger className="bg-white/5 border-white/10 text-white w-[300px]">
                                        <SelectValue placeholder="Selecione o modelo..." />
                                    </SelectTrigger>
                                    <SelectContent className="bg-zinc-950 border-white/10 text-white max-h-60">
                                        {models.map(model => (
                                            <SelectItem key={model.id} value={model.id}>
                                                {model.name} <span className="text-white/40">({model.provider})</span>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {globalRulesModelName && (
                                    <Badge className="bg-purple-500/20 text-purple-400">
                                        <CheckCircle className="h-3 w-3 mr-1" /> {globalRulesModelName}
                                    </Badge>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Agents Table */}
                    <Card className="bg-zinc-950 border-white/10">
                        <CardContent className="p-0">
                            <Table>
                                <TableHeader className="bg-white/5">
                                    <TableRow className="border-white/10 hover:bg-transparent">
                                        <TableHead className="text-white">Agente</TableHead>
                                        <TableHead className="text-white">Compilação</TableHead>
                                        <TableHead className="text-right text-white">Ações</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {agents.map(agent => (
                                        <TableRow key={agent.id} className="border-white/10 hover:bg-white/5">
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Bot className="h-4 w-4 text-white/50" />
                                                    <div>
                                                        <p className="font-medium">{agent.name}</p>
                                                        <div className="flex items-center gap-2 mt-0.5">
                                                            <Badge className="bg-blue-500/20 text-blue-400 text-[10px]">
                                                                {agent.modelName || "sem modelo"}
                                                            </Badge>
                                                            <button
                                                                className="text-[10px] text-white/30 hover:text-white/60 underline cursor-pointer"
                                                                onClick={() => { setPromptPreview(agent.systemPromptFull); setPromptPreviewOpen(true) }}
                                                            >
                                                                ver prompt ({(agent.systemPromptFull || "").length} chars)
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {agent.hasRules ? (
                                                    <div className="flex items-center gap-2">
                                                        <Badge className="bg-emerald-500/20 text-emerald-400">
                                                            <CheckCircle className="h-3 w-3 mr-1" />
                                                            v{agent.rulesVersion}
                                                        </Badge>
                                                        {agent.rulesCompiledAt && (
                                                            <span className="text-xs text-white/30">
                                                                {new Date(agent.rulesCompiledAt).toLocaleDateString('pt-BR')}
                                                            </span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <Badge className="bg-orange-500/20 text-orange-400">
                                                        <XCircle className="h-3 w-3 mr-1" /> Não compilado
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right space-x-1">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => handleCompileRules(agent.id)}
                                                    disabled={!globalRulesModelId || compilingId === agent.id}
                                                    className="text-white/50 hover:text-emerald-400"
                                                    title="Compilar regras"
                                                >
                                                    <RefreshCw className={`h-4 w-4 ${compilingId === agent.id ? "animate-spin" : ""}`} />
                                                </Button>
                                                {agent.hasRules && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => handleViewRules(agent.id)}
                                                        className="text-white/50 hover:text-blue-400"
                                                        title="Ver regras compiladas"
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                    {agents.length === 0 && (
                                        <TableRow>
                                            <TableCell colSpan={3} className="text-center py-12 text-white/50">
                                                <Bot className="h-8 w-8 mx-auto mb-2 opacity-30" />
                                                <p>Nenhum agente registrado</p>
                                                <p className="text-xs text-white/30 mt-1">Os agentes são criados pelos usuários via API</p>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* ═══════════════ DIALOGS ═══════════════ */}

            {/* Functions: Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={(o) => { setEditOpen(o); if (!o) resetForm() }}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Editar Função</DialogTitle>
                    </DialogHeader>
                    {formFields}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                        <Button onClick={handleUpdate} disabled={loading} className="bg-white text-black hover:bg-white/90">
                            {loading ? "Salvando..." : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Functions: Delete Dialog */}
            <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-red-400">
                            <AlertTriangle className="h-5 w-5" /> Remover Função
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Tem certeza? Esta ação não pode ser desfeita.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteOpen(false)} className="border-white/10 text-white hover:bg-white/10">Cancelar</Button>
                        <Button onClick={handleDelete} className="bg-red-600 text-white hover:bg-red-700">Remover</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* System Prompt Preview Dialog */}
            <Dialog open={promptPreviewOpen} onOpenChange={setPromptPreviewOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Code className="h-5 w-5 text-blue-400" /> System Prompt
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Definido pelo usuário — somente leitura
                        </DialogDescription>
                    </DialogHeader>
                    <pre className="bg-black/50 border border-white/10 rounded-lg p-4 text-xs font-mono text-white/80 overflow-auto max-h-[60vh] whitespace-pre-wrap">
                        {promptPreview || "Sem system prompt"}
                    </pre>
                </DialogContent>
            </Dialog>

            {/* Rules Preview Dialog */}
            <Dialog open={rulesPreviewOpen} onOpenChange={setRulesPreviewOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Brain className="h-5 w-5 text-purple-400" /> Regras Compiladas
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            {rulesPreview?.agent_name} — v{rulesPreview?.rules_version}
                            {rulesPreview?.rules_compiled_at && ` — ${new Date(rulesPreview.rules_compiled_at).toLocaleString('pt-BR')}`}
                        </DialogDescription>
                    </DialogHeader>
                    {rulesPreview?.compiled_rules ? (
                        <div className="space-y-4">
                            <div className="flex gap-2 flex-wrap">
                                {rulesPreview.compiled_rules.rules?.map((r: any) => (
                                    <Badge key={r.id} className="bg-white/10 text-white/70">
                                        {r.type}: {r.id}
                                    </Badge>
                                ))}
                            </div>
                            <pre className="bg-black/50 border border-white/10 rounded-lg p-4 text-xs font-mono text-white/80 overflow-auto max-h-[50vh]">
                                {JSON.stringify(rulesPreview.compiled_rules, null, 2)}
                            </pre>
                        </div>
                    ) : (
                        <p className="text-white/50 py-8 text-center">Nenhuma regra compilada ainda.</p>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    )
}

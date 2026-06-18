import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Plus, Server, Trash2, Key, ChevronDown, ChevronUp, RefreshCw, ToggleLeft, Download, Check, Loader2 } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"

interface ProviderKey {
    id: string
    label: string
    apiKey: string
    isActive: boolean
    usageCount: number
    lastUsedAt: string | null
    createdAt: string
}

interface Provider {
    id: string
    name: string
    type: string
    baseUrl: string
    hasApiKey: boolean
    rotationEnabled: boolean
    keys: ProviderKey[]
    models: { id: string, name: string }[]
}

export default function ProvidersPage() {
    const [providers, setProviders] = useState<Provider[]>([])
    const [loading, setLoading] = useState(false)
    const [open, setOpen] = useState(false)
    const [expandedProvider, setExpandedProvider] = useState<string | null>(null)

    // Form State - New Provider
    const [name, setName] = useState("")
    const [type, setType] = useState("openai")
    const [baseUrl, setBaseUrl] = useState("")
    const [apiKey, setApiKey] = useState("")

    // Add Key Dialog
    const [addKeyOpen, setAddKeyOpen] = useState(false)
    const [addKeyProviderId, setAddKeyProviderId] = useState<string | null>(null)
    const [newKeyValue, setNewKeyValue] = useState("")
    const [newKeyLabel, setNewKeyLabel] = useState("")

    // Sync Models Dialog
    const [syncOpen, setSyncOpen] = useState(false)
    const [syncProviderId, setSyncProviderId] = useState<string | null>(null)
    const [syncProviderName, setSyncProviderName] = useState("")
    const [syncLoading, setSyncLoading] = useState(false)
    const [availableModels, setAvailableModels] = useState<{
        id: string
        name: string
        already_imported: boolean
    }[]>([])
    const [selectedModels, setSelectedModels] = useState<string[]>([])
    const [importing, setImporting] = useState(false)

    useEffect(() => {
        fetchProviders()
    }, [])

    async function fetchProviders() {
        try {
            const res = await api.get("/admin/providers")
            setProviders(res.data)
        } catch (error) {
            toast.error("Falha ao buscar provedores")
        }
    }

    async function handleSubmit() {
        if (!name || !type) return

        setLoading(true)
        try {
            await api.post("/admin/providers", {
                name,
                type,
                baseUrl,
                apiKey
            })
            toast.success("Provedor criado")
            setOpen(false)
            fetchProviders()
            setName("")
            setBaseUrl("")
            setApiKey("")
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao criar provedor")
        } finally {
            setLoading(false)
        }
    }

    async function toggleRotation(providerId: string, currentValue: boolean) {
        try {
            await api.patch("/admin/providers", {
                id: providerId,
                rotationEnabled: !currentValue
            })
            toast.success(`Rotação ${!currentValue ? "ativada" : "desativada"}`)
            fetchProviders()
        } catch (error) {
            toast.error("Falha ao atualizar configuração")
        }
    }

    async function addKey() {
        if (!addKeyProviderId || !newKeyValue) return

        try {
            await api.post(`/admin/providers/${addKeyProviderId}/keys`, {
                apiKey: newKeyValue,
                label: newKeyLabel || "Chave API"
            })
            toast.success("Chave adicionada")
            setAddKeyOpen(false)
            setNewKeyValue("")
            setNewKeyLabel("")
            setAddKeyProviderId(null)
            fetchProviders()
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao adicionar chave")
        }
    }

    async function toggleKeyActive(providerId: string, keyId: string, currentValue: boolean) {
        try {
            await api.patch(`/admin/providers/${providerId}/keys`, {
                keyId,
                isActive: !currentValue
            })
            toast.success(`Chave ${!currentValue ? "ativada" : "desativada"}`)
            fetchProviders()
        } catch (error) {
            toast.error("Falha ao atualizar chave")
        }
    }

    async function deleteKey(providerId: string, keyId: string) {
        try {
            await api.delete(`/admin/providers/${providerId}/keys`, {
                data: { keyId }
            })
            toast.success("Chave removida")
            fetchProviders()
        } catch (error) {
            toast.error("Falha ao remover chave")
        }
    }

    function openAddKeyDialog(providerId: string) {
        setAddKeyProviderId(providerId)
        setAddKeyOpen(true)
    }

    async function openSyncDialog(provider: Provider) {
        setSyncProviderId(provider.id)
        setSyncProviderName(provider.name)
        setSyncOpen(true)
        setSyncLoading(true)
        setAvailableModels([])
        setSelectedModels([])

        try {
            const res = await api.get(`/admin/providers/${provider.id}/sync`)
            setAvailableModels(res.data.models || [])
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao buscar modelos")
            setSyncOpen(false)
        } finally {
            setSyncLoading(false)
        }
    }

    function toggleModelSelection(modelId: string) {
        setSelectedModels(prev =>
            prev.includes(modelId)
                ? prev.filter(id => id !== modelId)
                : [...prev, modelId]
        )
    }

    function selectAllNewModels() {
        const newModels = availableModels.filter(m => !m.already_imported).map(m => m.id)
        setSelectedModels(newModels)
    }

    async function importSelectedModels() {
        if (!syncProviderId || selectedModels.length === 0) return

        setImporting(true)
        let successCount = 0
        let errorCount = 0

        for (const modelId of selectedModels) {
            try {
                await api.post("/admin/models", {
                    name: modelId,
                    providerModelId: modelId,
                    providerId: syncProviderId,
                    costIn: 0,
                    costOut: 0
                })
                successCount++
            } catch {
                errorCount++
            }
        }

        setImporting(false)
        setSyncOpen(false)

        if (successCount > 0) {
            toast.success(`${successCount} modelo(s) importado(s) com sucesso!`)
        }
        if (errorCount > 0) {
            toast.error(`${errorCount} modelo(s) falharam ao importar`)
        }

        fetchProviders()
    }

    return (
        <div className="p-8 space-y-8 text-white">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold tracking-tight">Provedores de IA</h2>
                <Dialog open={open} onOpenChange={setOpen}>
                    <DialogTrigger asChild>
                        <Button className="bg-white text-black hover:bg-white/90">
                            <Plus className="mr-2 h-4 w-4" /> Adicionar Provedor
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-[425px]">
                        <DialogHeader>
                            <DialogTitle>Adicionar Provedor de IA</DialogTitle>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="name" className="text-right">Nome</Label>
                                <Input id="name" value={name} onChange={e => setName(e.target.value)} className="col-span-3 bg-white/5 border-white/10 text-white" />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="type" className="text-right">Tipo</Label>
                                <Select value={type} onValueChange={setType}>
                                    <SelectTrigger className="col-span-3 bg-white/5 border-white/10 text-white">
                                        <SelectValue placeholder="Tipo" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                        <SelectItem value="openai">OpenAI Compatível</SelectItem>
                                        <SelectItem value="anthropic">Anthropic</SelectItem>
                                        <SelectItem value="gemini">Google Gemini</SelectItem>
                                        <SelectItem value="groq">Groq</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="baseurl" className="text-right">Base URL</Label>
                                <Input id="baseurl" placeholder="Opcional" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} className="col-span-3 bg-white/5 border-white/10 text-white" />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="apikey" className="text-right">API Key</Label>
                                <Input id="apikey" type="password" placeholder="Chave única (fallback)" value={apiKey} onChange={e => setApiKey(e.target.value)} className="col-span-3 bg-white/5 border-white/10 text-white" />
                            </div>
                        </div>
                        <div className="flex justify-end">
                            <Button onClick={handleSubmit} disabled={loading} className="bg-white text-black hover:bg-white/90">Criar</Button>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="space-y-4">
                {providers.map((provider) => (
                    <Card key={provider.id} className="bg-zinc-950 border-white/10 text-white">
                        <CardHeader className="pb-2">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Server className="h-5 w-5 text-white/50" />
                                    <CardTitle className="text-lg">{provider.name}</CardTitle>
                                    <Badge variant="outline" className="border-white/20 text-white/60">{provider.type}</Badge>
                                    <span className="text-xs text-white/40">{provider.models.length} modelos</span>
                                </div>
                                <div className="flex items-center gap-4">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => openSyncDialog(provider)}
                                        className="border-white/10 text-white/70 hover:text-white"
                                    >
                                        <Download className="h-4 w-4 mr-1" /> Sincronizar Modelos
                                    </Button>
                                    <div className="flex items-center gap-2">
                                        <RefreshCw className={`h-4 w-4 ${provider.rotationEnabled ? "text-emerald-400" : "text-white/30"}`} />
                                        <span className="text-sm text-white/60">Rotação</span>
                                        <Switch
                                            checked={provider.rotationEnabled}
                                            onCheckedChange={() => toggleRotation(provider.id, provider.rotationEnabled)}
                                        />
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setExpandedProvider(expandedProvider === provider.id ? null : provider.id)}
                                        className="text-white/60"
                                    >
                                        <Key className="h-4 w-4 mr-1" />
                                        {provider.keys?.length || 0} chaves
                                        {expandedProvider === provider.id ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>

                        {expandedProvider === provider.id && (
                            <CardContent className="pt-4 border-t border-white/5">
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <h4 className="text-sm font-medium text-white/70">Chaves de API para Rotação</h4>
                                        <Button size="sm" variant="outline" className="border-white/10" onClick={() => openAddKeyDialog(provider.id)}>
                                            <Plus className="h-3 w-3 mr-1" /> Adicionar Chave
                                        </Button>
                                    </div>

                                    {provider.keys && provider.keys.length > 0 ? (
                                        <Table>
                                            <TableHeader>
                                                <TableRow className="border-white/5 hover:bg-transparent">
                                                    <TableHead className="text-white/50 text-xs">Label</TableHead>
                                                    <TableHead className="text-white/50 text-xs">API Key</TableHead>
                                                    <TableHead className="text-white/50 text-xs">Uso</TableHead>
                                                    <TableHead className="text-white/50 text-xs">Status</TableHead>
                                                    <TableHead className="text-right text-white/50 text-xs">Ações</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {provider.keys.map((key) => (
                                                    <TableRow key={key.id} className="border-white/5 hover:bg-white/5">
                                                        <TableCell className="text-sm">{key.label || "Sem label"}</TableCell>
                                                        <TableCell className="font-mono text-xs text-white/50">{key.apiKey}</TableCell>
                                                        <TableCell className="text-sm">{key.usageCount} usos</TableCell>
                                                        <TableCell>
                                                            <Badge className={key.isActive ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}>
                                                                {key.isActive ? "Ativa" : "Inativa"}
                                                            </Badge>
                                                        </TableCell>
                                                        <TableCell className="text-right">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-7 w-7 text-white/50 hover:text-white"
                                                                onClick={() => toggleKeyActive(provider.id, key.id, key.isActive)}
                                                            >
                                                                <ToggleLeft className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-7 w-7 text-white/50 hover:text-red-400"
                                                                onClick={() => deleteKey(provider.id, key.id)}
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    ) : (
                                        <div className="py-6 text-center text-white/40 text-sm border border-dashed border-white/10 rounded-md">
                                            <Key className="h-8 w-8 mx-auto mb-2 opacity-30" />
                                            Nenhuma chave configurada. {provider.hasApiKey ? "Usando chave única (fallback)." : "Adicione chaves para habilitar rotação."}
                                        </div>
                                    )}

                                    {!provider.rotationEnabled && provider.keys && provider.keys.length > 0 && (
                                        <p className="text-xs text-amber-400/80 flex items-center gap-1">
                                            ⚠️ Rotação desativada. Ative o switch acima para usar múltiplas chaves.
                                        </p>
                                    )}
                                </div>
                            </CardContent>
                        )}
                    </Card>
                ))}

                {providers.length === 0 && (
                    <div className="text-center py-12 text-white/50 border border-dashed border-white/10 rounded-lg">
                        <Server className="h-10 w-10 mx-auto mb-4 opacity-30" />
                        Nenhum provedor encontrado
                    </div>
                )}
            </div>

            {/* Add Key Dialog */}
            <Dialog open={addKeyOpen} onOpenChange={setAddKeyOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Adicionar Chave de API</DialogTitle>
                        <DialogDescription className="text-white/60">
                            Adicione uma nova chave para o pool de rotação deste provedor.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Label (opcional)</Label>
                            <Input
                                placeholder="Ex: Produção, Backup, Key 1"
                                value={newKeyLabel}
                                onChange={(e) => setNewKeyLabel(e.target.value)}
                                className="bg-zinc-900 border-white/10"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>API Key</Label>
                            <Input
                                type="password"
                                placeholder="sk-..."
                                value={newKeyValue}
                                onChange={(e) => setNewKeyValue(e.target.value)}
                                className="bg-zinc-900 border-white/10"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddKeyOpen(false)} className="border-white/10">Cancelar</Button>
                        <Button onClick={addKey} className="bg-white text-black hover:bg-white/90">Adicionar</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Sync Models Dialog */}
            <Dialog open={syncOpen} onOpenChange={setSyncOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white sm:max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Download className="h-5 w-5" />
                            Sincronizar Modelos - {syncProviderName}
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Selecione os modelos que deseja importar do provedor.
                        </DialogDescription>
                    </DialogHeader>

                    {syncLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-white/50" />
                            <span className="ml-3 text-white/60">Buscando modelos...</span>
                        </div>
                    ) : (
                        <>
                            <div className="flex items-center justify-between py-2 border-b border-white/10">
                                <span className="text-sm text-white/60">
                                    {availableModels.filter(m => !m.already_imported).length} novos modelos disponíveis
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={selectAllNewModels}
                                    className="text-white/70"
                                >
                                    <Check className="h-4 w-4 mr-1" /> Selecionar Todos Novos
                                </Button>
                            </div>

                            <div className="flex-1 overflow-auto max-h-96 space-y-1 py-2">
                                {availableModels.map((model) => (
                                    <div
                                        key={model.id}
                                        className={`flex items-center justify-between p-3 rounded-md cursor-pointer transition-colors ${model.already_imported
                                                ? 'bg-white/5 opacity-50 cursor-not-allowed'
                                                : selectedModels.includes(model.id)
                                                    ? 'bg-emerald-500/20 border border-emerald-500/40'
                                                    : 'bg-white/5 hover:bg-white/10'
                                            }`}
                                        onClick={() => !model.already_imported && toggleModelSelection(model.id)}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`w-5 h-5 rounded border flex items-center justify-center ${model.already_imported
                                                    ? 'border-white/20 bg-white/10'
                                                    : selectedModels.includes(model.id)
                                                        ? 'border-emerald-500 bg-emerald-500'
                                                        : 'border-white/30'
                                                }`}>
                                                {(model.already_imported || selectedModels.includes(model.id)) && (
                                                    <Check className="h-3 w-3 text-white" />
                                                )}
                                            </div>
                                            <span className="font-mono text-sm">{model.id}</span>
                                        </div>
                                        {model.already_imported && (
                                            <Badge className="bg-white/10 text-white/50">Já importado</Badge>
                                        )}
                                    </div>
                                ))}
                                {availableModels.length === 0 && (
                                    <div className="text-center py-8 text-white/50">
                                        Nenhum modelo encontrado
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    <DialogFooter className="border-t border-white/10 pt-4">
                        <Button variant="outline" onClick={() => setSyncOpen(false)} className="border-white/10">
                            Cancelar
                        </Button>
                        <Button
                            onClick={importSelectedModels}
                            disabled={selectedModels.length === 0 || importing}
                            className="bg-emerald-600 text-white hover:bg-emerald-700"
                        >
                            {importing ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Importando...
                                </>
                            ) : (
                                <>
                                    <Download className="h-4 w-4 mr-2" />
                                    Importar {selectedModels.length > 0 ? `(${selectedModels.length})` : ''}
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

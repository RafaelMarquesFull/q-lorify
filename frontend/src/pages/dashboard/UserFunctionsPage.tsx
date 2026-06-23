import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Zap, Code, Settings, Check, Info, Key, Plus, Trash2, MapPin, Building2, Ruler, Weight } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"

interface UserFunctionDetails {
    name: string
    displayName: string
    description: string | null
    cost: string
    requiresAi: boolean
    enrichPricePerUnit: number
    unitSize: number
    userEnabled: boolean
    userConfig: {
        id?: string
        outputTemplate?: string
        config?: Record<string, any>
    } | null
}

interface UserFunctionKey {
    id: string
    key: string
    description: string
}

export default function UserFunctionsPage() {
    const [functions, setFunctions] = useState<UserFunctionDetails[]>([])
    const [loading, setLoading] = useState(true)
    const [configOpen, setConfigOpen] = useState(false)
    const [selectedFunc, setSelectedFunc] = useState<UserFunctionDetails | null>(null)
    const [outputTemplate, setOutputTemplate] = useState("")
    const [saving, setSaving] = useState(false)

    // Keys state
    const [keys, setKeys] = useState<UserFunctionKey[]>([])
    const [newKeyName, setNewKeyName] = useState("")
    const [newKeyDesc, setNewKeyDesc] = useState("")
    const [addingKey, setAddingKey] = useState(false)
    const [orchestratorModel, setOrchestratorModel] = useState<string>("(carregando...)")
    const [enrichEnabled, setEnrichEnabled] = useState(false)
    const [targetUnit, setTargetUnit] = useState("m")
    const [targetMassUnit, setTargetMassUnit] = useState("kg")

    useEffect(() => {
        fetchFunctions()
        fetchOrchestratorModel()
    }, [])

    async function fetchOrchestratorModel() {
        try {
            const res = await api.get("/public/models")
            const models = res.data || []
            const orch = models.find((m: any) => m.isOrchestrator)
            if (orch) {
                setOrchestratorModel(orch.name)
            } else {
                setOrchestratorModel("fined-turbo")
            }
        } catch {
            setOrchestratorModel("fined-turbo")
        }
    }

    async function fetchFunctions() {
        try {
            const res = await api.get("/user/functions")
            setFunctions(res.data.functions || [])
        } catch {
            toast.error("Falha ao carregar funções")
        } finally {
            setLoading(false)
        }
    }

    async function toggleFunction(func: UserFunctionDetails) {
        try {
            if (func.userEnabled) {
                // Disable
                await api.delete("/user/functions", { data: { functionName: func.name } })
                toast.success(`${func.displayName} desativado`)
            } else {
                // Enable
                await api.post("/user/functions", { functionName: func.name })
                toast.success(`${func.displayName} ativado`)
            }
            fetchFunctions()
        } catch {
            toast.error("Erro ao atualizar função")
        }
    }

    async function openConfig(func: UserFunctionDetails) {
        setSelectedFunc(func)
        setOutputTemplate(func.userConfig?.outputTemplate || "")
        // Load config
        const config = func.userConfig?.config || {}
        setEnrichEnabled(!!config.enrich)
        setTargetUnit(config.target_unit || "m")
        setTargetMassUnit(config.target_unit || "kg")
        setConfigOpen(true)
        // Fetch keys for this function
        try {
            const res = await api.get(`/user/functions/${func.name}/keys`)
            setKeys(res.data.keys || [])
        } catch {
            setKeys([])
        }
    }

    async function addKey() {
        if (!selectedFunc || !newKeyName || !newKeyDesc) return
        setAddingKey(true)
        try {
            await api.post(`/user/functions/${selectedFunc.name}/keys`, {
                key: newKeyName,
                description: newKeyDesc
            })
            toast.success("Key adicionada")
            setNewKeyName("")
            setNewKeyDesc("")
            // Refresh keys
            const res = await api.get(`/user/functions/${selectedFunc.name}/keys`)
            setKeys(res.data.keys || [])
        } catch (e: any) {
            toast.error(e.response?.data?.error || "Erro ao adicionar key")
        } finally {
            setAddingKey(false)
        }
    }

    async function deleteKey(keyId: string) {
        if (!selectedFunc) return
        try {
            await api.delete(`/user/functions/${selectedFunc.name}/keys`, { data: { keyId } })
            toast.success("Key removida")
            setKeys(keys.filter(k => k.id !== keyId))
        } catch {
            toast.error("Erro ao remover key")
        }
    }

    async function saveConfig() {
        if (!selectedFunc) return
        setSaving(true)
        try {
            const config: Record<string, any> = {
                ...(selectedFunc.userConfig?.config || {}),
                enrich: enrichEnabled,
                target_unit: selectedFunc.name === 'convert_mass' ? targetMassUnit : targetUnit
            }
            await api.patch("/user/functions", {
                functionName: selectedFunc.name,
                outputTemplate: outputTemplate || null,
                config
            })
            toast.success("Configuração salva")
            setConfigOpen(false)
            fetchFunctions()
        } catch {
            toast.error("Erro ao salvar")
        } finally {
            setSaving(false)
        }
    }

    const costColors: Record<string, string> = {
        low: "bg-emerald-500/20 text-emerald-400",
        medium: "bg-amber-500/20 text-amber-400",
        high: "bg-red-500/20 text-red-400"
    }

    const templateExamples: Record<string, string> = {
        extract_cep: `{
  "cep_1": "{{result_1}}",
  "cep_2": "{{result_2}}"
}`,
        extract_cpfcnpj: `{
  "doc_1": "{{result_1}}",
  "doc_2": "{{result_2}}"
}`,
        extract_phones: `{
  "telefone_1": "{{result_1}}",
  "telefone_2": "{{result_2}}"
}`,
        extract_emails: `{
  "email_1": "{{result_1}}"
}`,
        extract_endereco: `{
  "endereco_1": "{{result_1}}",
  "endereco_2": "{{result_2}}"
}`,
        convert_units: `{
  "medidas_produto": "{{result_1}}"
}`,
        convert_mass: `{
  "peso_carga": "{{result_1}}"
}`
    }

    // Pattern examples - realistic freight quote templates
    const patternExamples: Record<string, string> = {
        extract_cep: `Remetente: EMPRESA X
CNPJ: 94.516.671/0001-53
CEP: 96800-001 (Santa Cruz/RS)
Destinatário: EMPRESA Y
CEP: 88100-001 (São José/SC)`,
        extract_cpfcnpj: `Remetente (CNPJ): 09.278.286/0001-46
Destinatário (CNPJ): 09.263.687/0001-22
Pagador: Remetente`,
        extract_phones: `Contato: João Silva
Telefone: (11) 98765-4321
Whatsapp: (11) 99876-5432`,
        extract_emails: `Responsável: Maria Santos
E-mail: maria@empresa.com
Comercial: vendas@empresa.com`,
        extract_endereco: `Coleta: Rua das Flores, 123, Centro
São Paulo/SP - CEP 01310-100
Entrega: Av. Brasil, 456, Industrial
Rio de Janeiro/RJ - CEP 20040-020`,
        extract_valores: `Valor da Mercadoria: R$ 5.908,96
Valor do Frete: R$ 350,00
Valor NF: R$ 1.145,35`,
        extract_dimensoes: `Volumes: 4 caixas
Cubagem Total: 0,3573 m³
Medidas: 120cm x 80cm x 95cm (LxAxC)`,
        extract_quantidades: `Quantidade de Volumes: 26
Peso bruto: 165 Kg
Peso total: 360kg
6 containers de 1.000 L`,
        convert_units: `Dimensões: 36 x 30 x 55 CM
Largura: 80cm
Comprimento: 3 polegadas
Altura: 1,5 metros`,
        convert_mass: `Peso bruto: 2,5 toneladas
Peso líquido: 500 kg
Embalagem: 250 gramas
Carga: 1t 300kg`
    }

    // Output examples - structured JSON with normalized values
    const outputExamples: Record<string, string> = {
        extract_cep: `{
  "CEP_origem": "96800001",
  "CEP_destino": "88100001"
}`,
        extract_cpfcnpj: `{
  "CNPJ_remetente": "09278286000146",
  "CNPJ_destinatario": "09263687000122"
}`,
        extract_phones: `{
  "telefone_principal": {
    "ddd": "11",
    "numero": "987654321",
    "codigo_pais": null
  },
  "whatsapp": {
    "ddd": "11",
    "numero": "998765432",
    "codigo_pais": null
  }
}`,
        extract_emails: `{
  "email_responsavel": "maria@empresa.com",
  "email_comercial": "vendas@empresa.com"
}`,
        extract_endereco: `{
  "endereco_coleta": {
    "logradouro": "Rua das Flores",
    "numero": "123",
    "complemento": null,
    "bairro": "Centro",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01310100"
  },
  "endereco_entrega": {
    "logradouro": "Av. Brasil",
    "numero": "456",
    "complemento": "Galpão 2",
    "bairro": "Industrial",
    "cidade": "Rio de Janeiro",
    "uf": "RJ",
    "cep": "20040020"
  }
}`,
        extract_valores: `{
  "valor_mercadoria": {
    "valor": 5908.96,
    "moeda": "BRL"
  },
  "valor_frete": {
    "valor": 350.00,
    "moeda": "BRL"
  }
}`,
        extract_dimensoes: `{
  "medidas": {
    "largura": 1.20,
    "altura": 0.80,
    "comprimento": 0.95,
    "cubagem_total": 0.912,
    "unidade": "m"
  }
}`,
        extract_quantidades: `{
  "carga": {
    "quantidade": 26,
    "peso": 165,
    "tipo_volume": "caixa"
  }
}`,
        convert_units: `{
  "medidas_produto": {
    "found": true,
    "count": 4,
    "target_unit": "m",
    "measurements": [
      { "original": "36 x 30 x 55 CM", "type": "dimensions", "converted_text": "0.36 x 0.3 x 0.55 m" },
      { "original": "80cm", "converted_value": 0.8, "converted_text": "0.8 m" },
      { "original": "3 polegadas", "converted_value": 0.0762, "converted_text": "0.0762 m" },
      { "original": "1,5 metros", "converted_value": 1.5, "converted_text": "1.5 m" }
    ]
  }
}`,
        convert_mass: `{
  "peso_carga": {
    "found": true,
    "count": 3,
    "target_unit": "kg",
    "measurements": [
      { "original": "2,5 toneladas", "converted_value": 2500.0, "extenso": "dois mil e quinhentos quilos" },
      { "original": "500 kg", "converted_value": 500.0, "extenso": "quinhentos quilos" },
      { "original": "250 gramas", "converted_value": 0.25, "extenso": "zero vírgula dois cinco quilos" }
    ]
  }
}`
    }

    if (loading) {
        return (
            <div className="p-8 text-white">
                <div className="animate-pulse">Carregando funções...</div>
            </div>
        )
    }

    return (
        <AnimatedGradientBg className="p-8 space-y-8 min-h-full rounded-3xl">
            <div className="mb-4">
                <h2 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">Minhas Funções</h2>
                <p className="text-muted-foreground mt-1">Configure as funções de extração que deseja usar</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                {functions.map(func => (
                    <Card
                        key={func.name}
                        className={`transition-all duration-300 ${func.userEnabled
                            ? 'glass-card border-primary/30 bg-primary/5 hover:bg-primary/10 shadow-glow-primary'
                            : 'glass-subtle hover:bg-white/5'
                            }`}
                    >
                        <CardHeader className="pb-3">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                    <div className={`p-2 rounded-lg ${func.userEnabled ? 'bg-primary/10 text-primary ring-1 ring-primary/20' : 'bg-white/5 text-muted-foreground ring-1 ring-white/10'}`}>
                                        <Code className="h-5 w-5" />
                                    </div>
                                    <CardTitle className="text-lg">{func.displayName}</CardTitle>
                                </div>
                                <Switch
                                    checked={func.userEnabled}
                                    onCheckedChange={() => toggleFunction(func)}
                                />
                            </div>
                            <CardDescription className="text-white/50">
                                {func.description}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Badge className={costColors[func.cost]}>
                                        {func.cost}
                                    </Badge>
                                    {func.requiresAi && (
                                        <Badge className="bg-purple-500/20 text-purple-400">
                                            <Zap className="h-3 w-3 mr-1" /> IA
                                        </Badge>
                                    )}
                                </div>
                                {func.userEnabled && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => openConfig(func)}
                                        className="text-white/60 hover:text-white"
                                    >
                                        <Settings className="h-4 w-4 mr-1" /> Configurar
                                    </Button>
                                )}
                            </div>
                            {func.userConfig?.outputTemplate && (
                                <div className="mt-3 pt-3 border-t border-white/10">
                                    <div className="flex items-center gap-1 text-xs text-emerald-400">
                                        <Check className="h-3 w-3" /> Template configurado
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>

            {functions.length === 0 && (
                <div className="text-center py-12 text-white/50">
                    Nenhuma função disponível. Contate o administrador.
                </div>
            )}

            {/* Como Usar Section - At Bottom */}
            <Card className="glass-card border-blue-500/20 bg-gradient-to-br from-blue-900/10 to-transparent">
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2 text-primary">
                        <Code className="h-5 w-5" />
                        Como Usar
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                        Use o modelo <code className="bg-primary/10 px-1.5 py-0.5 rounded text-primary border border-primary/20">{orchestratorModel}</code> para executar suas funções
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                        <p className="text-sm text-purple-300 font-medium mb-3">📌 Formato de Padrões por Função</p>
                        <div className="space-y-3">
                            {functions.filter(f => f.userEnabled).map(func => (
                                patternExamples[func.name] && (
                                    <div key={func.name} className="bg-black/20 rounded p-2">
                                        <p className="text-xs text-white/50 mb-1">{func.displayName}:</p>
                                        <pre className="text-xs text-purple-200">{patternExamples[func.name]}</pre>
                                    </div>
                                )
                            ))}
                            {functions.filter(f => f.userEnabled).length === 0 && (
                                <p className="text-sm text-white/40">Habilite funções acima para ver exemplos de padrões.</p>
                            )}
                        </div>
                    </div>

                    <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                        <pre className="relative bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-4 text-sm overflow-x-auto text-blue-200 shadow-inner">
                            {`curl -X POST ${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/chat/completions \\
  -H "Authorization: Bearer sk-agent-SUA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${orchestratorModel}",
    "messages": [{
      "role": "user",
      "content": "${functions.filter(f => f.userEnabled && patternExamples[f.name]).map(f => patternExamples[f.name]?.split('\n')[0]).slice(0, 2).join(', ') || 'Sua mensagem aqui'}"
    }]
  }'`}
                        </pre>
                    </div>
                    <p className="text-xs text-white/40">
                        💡 Use o formato <code className="bg-white/10 px-1 rounded">chave: valor</code> para direcionar dados às chaves que você configurou. Caso não use o formato, a IA classificará automaticamente.
                    </p>
                </CardContent>
            </Card>

            {/* Config Dialog */}
            <Dialog open={configOpen} onOpenChange={setConfigOpen}>
                <DialogContent className="glass-ultra border-white/10 text-foreground sm:max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Settings className="h-5 w-5" />
                            Configurar {selectedFunc?.displayName}
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Configure as chaves de extração e templates para esta função.
                        </DialogDescription>
                    </DialogHeader>

                    <Tabs defaultValue="keys" className="w-full">
                        <TabsList className="grid w-full grid-cols-3 bg-white/5">
                            <TabsTrigger value="keys" className="data-[state=active]:bg-white/10">
                                <Key className="h-4 w-4 mr-2" /> Chaves
                            </TabsTrigger>
                            <TabsTrigger value="options" className="data-[state=active]:bg-white/10">
                                <Settings className="h-4 w-4 mr-2" /> Opções
                            </TabsTrigger>
                            <TabsTrigger value="template" className="data-[state=active]:bg-white/10">
                                <Code className="h-4 w-4 mr-2" /> Template
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="options" className="space-y-4 py-4">
                            {selectedFunc?.name === 'extract_cep' && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20 mt-0.5">
                                                <MapPin className="h-5 w-5" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-white">Enriquecimento de CEP</p>
                                                <p className="text-sm text-white/50 mt-1">
                                                    Obtém endereço completo a partir do CEP (logradouro, bairro, cidade, estado).
                                                </p>
                                                <div className="flex items-center gap-2 mt-2">
                                                    <Badge className="bg-amber-500/20 text-amber-400 text-xs">
                                                        +R$ {selectedFunc?.enrichPricePerUnit?.toFixed(2).replace('.', ',')} a cada {selectedFunc?.unitSize?.toLocaleString('pt-BR')} requisições
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={enrichEnabled}
                                            onCheckedChange={setEnrichEnabled}
                                        />
                                    </div>
                                </div>
                            )}
                            {selectedFunc?.name === 'extract_cpfcnpj' && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20 mt-0.5">
                                                <Building2 className="h-5 w-5" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-white">Enriquecimento de CNPJ</p>
                                                <p className="text-sm text-white/50 mt-1">
                                                    Consulta dados completos da empresa (razão social, endereço, situação cadastral). Apenas CNPJs são enriquecidos, nunca CPFs.
                                                </p>
                                                <div className="flex items-center gap-2 mt-2">
                                                    <Badge className="bg-amber-500/20 text-amber-400 text-xs">
                                                        +R$ {selectedFunc?.enrichPricePerUnit?.toFixed(2).replace('.', ',')} a cada {selectedFunc?.unitSize?.toLocaleString('pt-BR')} requisições
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={enrichEnabled}
                                            onCheckedChange={setEnrichEnabled}
                                        />
                                    </div>
                                </div>
                            )}
                            {selectedFunc?.name === 'convert_units' && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 ring-1 ring-teal-500/20 mt-0.5">
                                                <Ruler className="h-5 w-5" />
                                            </div>
                                            <div className="flex-1">
                                                <p className="font-medium text-white">Unidade de Destino</p>
                                                <p className="text-sm text-white/50 mt-1">
                                                    Selecione para qual unidade as medidas detectadas serão convertidas.
                                                </p>
                                                <div className="mt-3">
                                                    <Select value={targetUnit} onValueChange={setTargetUnit}>
                                                        <SelectTrigger className="w-[220px] bg-white/5 border-white/10 text-foreground">
                                                            <SelectValue placeholder="Selecione a unidade" />
                                                        </SelectTrigger>
                                                        <SelectContent className="glass-ultra border-white/10 text-foreground">
                                                            <SelectItem value="mm">Milímetros (mm)</SelectItem>
                                                            <SelectItem value="cm">Centímetros (cm)</SelectItem>
                                                            <SelectItem value="m">Metros (m)</SelectItem>
                                                            <SelectItem value="km">Quilômetros (km)</SelectItem>
                                                            <SelectItem value="pol">Polegadas (pol)</SelectItem>
                                                            <SelectItem value="ft">Pés (ft)</SelectItem>
                                                            <SelectItem value="yd">Jardas (yd)</SelectItem>
                                                            <SelectItem value="mi">Milhas (mi)</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {selectedFunc?.name === 'convert_mass' && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400 ring-1 ring-orange-500/20 mt-0.5">
                                                <Weight className="h-5 w-5" />
                                            </div>
                                            <div className="flex-1">
                                                <p className="font-medium text-white">Unidade de Massa de Destino</p>
                                                <p className="text-sm text-white/50 mt-1">
                                                    Selecione para qual unidade de massa os valores detectados serão convertidos. O resultado incluirá o valor por extenso.
                                                </p>
                                                <div className="mt-3">
                                                    <Select value={targetMassUnit} onValueChange={setTargetMassUnit}>
                                                        <SelectTrigger className="w-[220px] bg-white/5 border-white/10 text-foreground">
                                                            <SelectValue placeholder="Selecione a unidade" />
                                                        </SelectTrigger>
                                                        <SelectContent className="glass-ultra border-white/10 text-foreground">
                                                            <SelectItem value="t">Toneladas (t)</SelectItem>
                                                            <SelectItem value="kg">Quilos (kg)</SelectItem>
                                                            <SelectItem value="g">Gramas (g)</SelectItem>
                                                            <SelectItem value="mg">Miligramas (mg)</SelectItem>
                                                            <SelectItem value="lb">Libras (lb)</SelectItem>
                                                            <SelectItem value="oz">Onças (oz)</SelectItem>
                                                            <SelectItem value="@">Arrobas (@)</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {selectedFunc?.name !== 'extract_cep' && selectedFunc?.name !== 'extract_cpfcnpj' && selectedFunc?.name !== 'convert_units' && selectedFunc?.name !== 'convert_mass' && (
                                <div className="text-center py-8 text-white/40">
                                    Nenhuma opção adicional disponível para esta função.
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="keys" className="space-y-4 py-4">
                            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 w-full">
                                <div className="grid grid-cols-[auto_1fr] gap-3">
                                    <Info className="h-5 w-5 text-purple-400 mt-0.5" />
                                    <div className="text-sm text-white/70 min-w-0">
                                        <p>Defina as <strong>chaves</strong> que a IA usará para classificar os dados extraídos.</p>
                                        {selectedFunc && patternExamples[selectedFunc.name] && (
                                            <div className="mt-2 w-full">
                                                <p className="text-xs text-white/50 mb-1">Exemplo de entrada:</p>
                                                <pre className="bg-black/30 rounded p-1.5 text-xs text-purple-200 overflow-x-auto max-w-full whitespace-pre">{patternExamples[selectedFunc.name].split('\n')[0]}</pre>
                                            </div>
                                        )}
                                        {selectedFunc && outputExamples[selectedFunc.name] && (
                                            <div className="mt-2 w-full">
                                                <p className="text-xs text-white/50 mb-1">Exemplo de saída:</p>
                                                <pre className="bg-black/30 rounded p-1.5 text-xs text-emerald-200 overflow-x-auto max-h-40 max-w-full whitespace-pre">{outputExamples[selectedFunc.name]}</pre>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Add new key form */}
                            <div className="grid grid-cols-[1fr_2fr_auto] gap-2">
                                <Input
                                    placeholder="Nome da chave"
                                    value={newKeyName}
                                    onChange={e => setNewKeyName(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white font-mono"
                                />
                                <Input
                                    placeholder="Descrição para a IA identificar..."
                                    value={newKeyDesc}
                                    onChange={e => setNewKeyDesc(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white"
                                />
                                <Button
                                    onClick={addKey}
                                    disabled={addingKey || !newKeyName || !newKeyDesc}
                                    className="bg-purple-600 hover:bg-purple-700"
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                            </div>

                            {/* Keys list */}
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                                {keys.length === 0 ? (
                                    <div className="text-center py-6 text-white/40">
                                        Nenhuma chave configurada. Adicione acima.
                                    </div>
                                ) : (
                                    keys.map(k => (
                                        <div key={k.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                            <div>
                                                <span className="font-mono text-purple-400">{k.key}</span>
                                                <span className="text-white/50 mx-2">→</span>
                                                <span className="text-white/70">{k.description}</span>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => deleteKey(k.id)}
                                                className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </TabsContent>

                        <TabsContent value="template" className="space-y-4 py-4">
                            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                                <div className="flex items-start gap-2">
                                    <Info className="h-5 w-5 text-blue-400 mt-0.5" />
                                    <div className="text-sm text-white/70">
                                        <p>Use placeholders como <code className="bg-white/10 px-1 rounded">{`{{result_1}}`}</code> para mapear resultados.</p>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label className="text-white">Template de Saída (JSON)</Label>
                                <Textarea
                                    placeholder={templateExamples[selectedFunc?.name || ""] || "{}"}
                                    value={outputTemplate}
                                    onChange={e => setOutputTemplate(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white font-mono min-h-[200px]"
                                />
                            </div>

                            {selectedFunc && templateExamples[selectedFunc.name] && (
                                <div className="space-y-2">
                                    <Label className="text-white/50">Exemplo:</Label>
                                    <pre className="bg-white/5 p-3 rounded text-xs text-white/60 overflow-auto">
                                        {templateExamples[selectedFunc.name]}
                                    </pre>
                                </div>
                            )}
                        </TabsContent>
                    </Tabs>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setConfigOpen(false)} className="border-white/10 text-white hover:bg-white/10">
                            Fechar
                        </Button>
                        <Button onClick={saveConfig} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700">
                            {saving ? "Salvando..." : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AnimatedGradientBg>
    )
}

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { BrainCircuit, Play, MessageSquare, AlertTriangle, Layers, ArrowRight, BarChart3, FlaskConical } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { DomainStats } from "@/components/dashboard/DomainStats"

interface Model {
    id: string
    name: string
    provider: string
}

export default function AnalyticsPage() {
    const [loading, setLoading] = useState(false)
    const [models, setModels] = useState<Model[]>([])
    const [mode, setMode] = useState<"test" | "stats">("test")

    // Inputs
    const [intent, setIntent] = useState("")
    const [context, setContext] = useState("")
    const [statusJson, setStatusJson] = useState('{"valor1": false, "valor2": true}')
    const [categories, setCategories] = useState("carro, moto, barco, bicicleta")
    const [exceptions, setExceptions] = useState('[{"pattern": "urgente", "action": "reclassify"}]')
    const [selectedModel, setSelectedModel] = useState<string>("")
    const [multiIntentMode, setMultiIntentMode] = useState(false)

    // Result
    const [result, setResult] = useState<any>(null)

    useEffect(() => {
        fetchModels()
    }, [])

    async function fetchModels() {
        try {
            const res = await api.get("/public/models")
            setModels(res.data)
        } catch (error) {
            console.error(error)
        }
    }

    async function handleAnalyze() {
        setLoading(true)
        setResult(null)
        try {
            // Parse JSON inputs
            let parsedStatus = {}
            try {
                parsedStatus = JSON.parse(statusJson)
            } catch (e) {
                toast.error("Erro no JSON de Status")
                setLoading(false)
                return
            }

            let parsedExceptions = []
            try {
                parsedExceptions = JSON.parse(exceptions)
            } catch (e) {
                toast.error("Erro no JSON de Exceções")
                setLoading(false)
                return
            }

            const payload = {
                intent,
                context,
                status: parsedStatus,
                categories: categories.split(",").map(c => c.trim()),
                exceptions: parsedExceptions,
                model_id: selectedModel || undefined,
                multi_intent: multiIntentMode
            }

            const res = await api.post("/ai/sentiment/analyze", payload)
            setResult(res.data)
            toast.success("Análise concluída!")
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha na análise")
        } finally {
            setLoading(false)
        }
    }

    function loadScenario(type: string) {
        if (type === "sticky") {
            setIntent("qual o valor?")
            setContext("certo, vamos continuar")
            setStatusJson('{"cotacao": "cotar"}')
            toast.info("Cenário: Sticky Session carregado")
        } else if (type === "exception") {
            setIntent("quero falar com atendente urgente")
            setContext("")
            setStatusJson('{"cotacao": "cotar"}')
            toast.info("Cenário: Exceção carregado")
        } else if (type === "menu") {
            setIntent("2")
            setContext("Escolha uma opção:\n1. Cotação\n2. Rastreio")
            setStatusJson('{}')
            toast.info("Cenário: Menu numérico carregado")
        }
    }

    return (
        <div className="p-8 space-y-8 text-white max-w-6xl mx-auto">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">Analise de sentimentos</h2>
                    <p className="text-muted-foreground mt-2">Valide a lógica do orquestrador de análise de sentimentos.</p>
                </div>

                {mode === "test" && (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => loadScenario("sticky")} className="border-white/10 text-foreground bg-white/5 hover:bg-white/10">
                            <Layers className="mr-2 h-4 w-4" /> Sticky Teste
                        </Button>
                        <Button variant="outline" onClick={() => loadScenario("exception")} className="border-white/10 text-foreground bg-white/5 hover:bg-white/10">
                            <AlertTriangle className="mr-2 h-4 w-4" /> Exception Teste
                        </Button>
                        <Button variant="outline" onClick={() => loadScenario("menu")} className="border-white/10 text-foreground bg-white/5 hover:bg-white/10">
                            <ArrowRight className="mr-2 h-4 w-4" /> Menu Teste
                        </Button>
                    </div>
                )}
            </div>

            {/* Tab Navigation */}
            <div className="flex space-x-1 rounded-xl bg-white/5 p-1 w-fit border border-white/10">
                <button
                    onClick={() => setMode("test")}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${mode === "test"
                            ? "bg-primary text-primary-foreground shadow-sm"
                            : "text-muted-foreground hover:bg-white/5 hover:text-white"
                        }`}
                >
                    <FlaskConical className="h-4 w-4" />
                    Live Testing
                </button>
                <button
                    onClick={() => setMode("stats")}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${mode === "stats"
                            ? "bg-primary text-primary-foreground shadow-sm"
                            : "text-muted-foreground hover:bg-white/5 hover:text-white"
                        }`}
                >
                    <BarChart3 className="h-4 w-4" />
                    Domain Analytics
                </button>
            </div>

            {mode === "stats" ? (
                <DomainStats />
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* Inputs Column */}
                    <div className="space-y-6">
                        <Card className="glass-ultra border-white/10">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <MessageSquare className="h-5 w-5 text-blue-400" /> Input Data
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>1. Intenção (User Message)</Label>
                                    <Input
                                        value={intent}
                                        onChange={e => setIntent(e.target.value)}
                                        placeholder="Ex: Qual o valor?"
                                        className="bg-white/5 border-white/10 text-foreground"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label>2. Contexto (Previous Message)</Label>
                                    <Textarea
                                        value={context}
                                        onChange={e => setContext(e.target.value)}
                                        placeholder="Ex: Olá, bem-vindo!"
                                        className="bg-white/5 border-white/10 text-foreground min-h-[80px]"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label className="flex justify-between">
                                        <span>3. Status (JSON)</span>
                                        <span className="text-xs text-muted-foreground">Sticky Session</span>
                                    </Label>
                                    <div className="font-mono text-sm">
                                        <Textarea
                                            value={statusJson}
                                            onChange={e => setStatusJson(e.target.value)}
                                            className="bg-white/5 border-white/10 text-amber-400/90 font-mono min-h-[80px]"
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="glass-ultra border-white/10">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <BrainCircuit className="h-5 w-5 text-purple-400" /> Configuração
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>4. Categorias (Target)</Label>
                                    <Input
                                        value={categories}
                                        onChange={e => setCategories(e.target.value)}
                                        className="bg-white/5 border-white/10 text-foreground"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label>5. Exceções (JSON)</Label>
                                    <Textarea
                                        value={exceptions}
                                        onChange={e => setExceptions(e.target.value)}
                                        className="bg-white/5 border-white/10 text-foreground font-mono min-h-[80px]"
                                    />
                                </div>

                                <div className="flex items-center space-x-2 p-3 rounded bg-white/5 border border-white/10">
                                    <Checkbox
                                        id="multi-intent"
                                        checked={multiIntentMode}
                                        onCheckedChange={(checked) => setMultiIntentMode(checked as boolean)}
                                    />
                                    <Label htmlFor="multi-intent" className="cursor-pointer">
                                        Multi-Intent Mode (detectar múltiplas intenções)
                                    </Label>
                                </div>

                                <div className="space-y-2">
                                    <Label>AI Model (Fallback)</Label>
                                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                                        <SelectTrigger className="bg-white/5 border-white/10 text-foreground">
                                            <SelectValue placeholder="Select a model for AI Analysis" />
                                        </SelectTrigger>
                                        <SelectContent className="glass-ultra border-white/10 text-foreground">
                                            {models.map(m => (
                                                <SelectItem key={m.id} value={m.id}>{m.name} ({m.provider})</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <Button onClick={handleAnalyze} disabled={loading} className="w-full bg-primary hover:bg-primary/90 text-primary-foreground mt-4 transition-all duration-300">
                                    {loading ? "Analisando..." : <><Play className="mr-2 h-4 w-4" /> Executar Análise</>}
                                </Button>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Results Column */}
                    <div className="space-y-6">
                        <Card className="glass-ultra border-white/10 h-full">
                            <CardHeader>
                                <CardTitle>Resultado</CardTitle>
                                <CardDescription>Decisão tomada pelo orquestrador</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {result ? (
                                    <div className="space-y-8 animate-in fade-in duration-500">
                                        <div className="text-center py-8 bg-black/20 rounded-lg border border-white/5">
                                            <p className="text-sm text-muted-foreground mb-2">CLASSIFICAÇÃO FINAL</p>
                                            <Badge className={`text-2xl px-4 py-2 border-none shadow-lg ${result.classification === 'incompreendido'
                                                ? 'bg-orange-500 hover:bg-orange-600 shadow-orange-500/20'
                                                : 'bg-blue-500 hover:bg-blue-600 shadow-blue-500/20'
                                                }`}>
                                                {result.classification?.toUpperCase()}
                                            </Badge>
                                        </div>

                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                                <span className="text-muted-foreground">Fonte da Decisão</span>
                                                <Badge variant="outline" className={`
                                                    ${result.source === 'fallback' ? 'text-orange-400 border-orange-400/30' : ''}
                                                    ${result.source === 'sticky_session' ? 'text-amber-400 border-amber-400/30' : ''}
                                                    ${result.source === 'ai_classifier' ? 'text-purple-400 border-purple-400/30' : ''}
                                                    ${result.source === 'rule_match' || result.source === 'rule_match_ai_validated' ? 'text-green-400 border-green-400/30' : ''}
                                                    ${result.source === 'exception_ai_validated' || result.source === 'exception_pattern_match' ? 'text-red-400 border-red-400/30' : ''}
                                                    ${result.source === 'exception_ai_rejected' ? 'text-yellow-400 border-yellow-400/30' : ''}
                                                `}>
                                                    {result.source?.replace(/_/g, ' ').toUpperCase()}
                                                </Badge>
                                            </div>

                                            <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                                <span className="text-muted-foreground">Validado por IA?</span>
                                                <span className={result.ai_validated ? "text-purple-400 font-bold" : "text-white/40"}>
                                                    {result.ai_validated ? "SIM ✓" : "NÃO"}
                                                </span>
                                            </div>

                                            {result.multi_intent && result.classifications && (
                                                <div className="p-4 rounded bg-purple-500/10 border border-purple-500/30">
                                                    <p className="text-sm text-purple-400 mb-3 font-semibold">🎯 MÚLTIPLAS INTENÇÕES DETECTADAS</p>
                                                    <div className="flex flex-wrap gap-2">
                                                        {result.classifications.map((cls: string, idx: number) => (
                                                            <Badge key={idx} className="bg-purple-500/20 text-purple-300 border-purple-500/50">
                                                                {idx + 1}. {cls.toUpperCase()}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                                <span className="text-muted-foreground">Exceção Detectada?</span>
                                                <span className={result.is_exception ? "text-red-400 font-bold" : "text-green-400"}>
                                                    {result.is_exception ? "SIM" : "NÃO"}
                                                </span>
                                            </div>

                                            <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                                <span className="text-muted-foreground">Status Ativo Anterior</span>
                                                <span className="font-mono text-amber-400">
                                                    {result.active_status || "null"}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="mt-6">
                                            <Label className="mb-2 block">Raw Response</Label>
                                            <pre className="bg-black/50 p-4 rounded text-xs font-mono overflow-auto border border-white/5 text-muted-foreground custom-scrollbar max-h-[300px]">
                                                {JSON.stringify(result, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="h-64 flex flex-col items-center justify-center text-muted-foreground/30">
                                        <BrainCircuit className="h-16 w-16 mb-4 opacity-50" />
                                        <p>Aguardando análise...</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            )}
        </div>
    )
}

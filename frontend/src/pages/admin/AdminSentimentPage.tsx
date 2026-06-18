import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    BrainCircuit, Play, MessageSquare, AlertTriangle, Layers, ArrowRight,
    BookOpen, GraduationCap, BarChart3, CheckCircle, Trash2, Plus,
    RefreshCw, Eye, Clock, Zap, TrendingUp
} from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { PerformanceStats } from "@/components/admin/PerformanceStats"
import { FinancialSavingsCard } from "@/components/dashboard/FinancialSavingsCard"

interface Model {
    id: string
    name: string
    provider: string
}

interface SentimentLog {
    id: string
    intent: string
    context: string
    categories: string[]
    classification: string
    classifications: string[] | null
    confidence: number
    source: string
    tokenUsage: number
    reviewed: boolean
    correction: string | null
    notes: string | null
    createdAt: string
}

interface Synonym {
    id: string
    word: string
    category: string
    source: string
    useCount: number
    lastUsedAt: string | null
    createdAt: string
}

interface Pattern {
    id: string
    word: string
    category: string
    occurrenceCount: number
    avgConfidence: number
    autoApproved: boolean
    lastSeen: string
}

interface Stats {
    totalLogs: number
    pendingReviews: number
    totalSynonyms: number
    cacheHits: number
    aiClassifications: number
    fallbacks: number
    avgConfidence: number
}

export default function AdminSentimentPage() {
    const [loading, setLoading] = useState(false)
    const [models, setModels] = useState<Model[]>([])
    const [activeTab, setActiveTab] = useState("tester")

    // Tester Inputs
    const [intent, setIntent] = useState("")
    const [context, setContext] = useState("")
    const [statusJson, setStatusJson] = useState('{"cotacao": false, "rastreio": false}')
    const [categories, setCategories] = useState("cotacao, rastreio, boleto, cte, coleta, conversacao, atendente")
    const [exceptions, setExceptions] = useState('[{"pattern": "urgente", "action": "reclassify"}]')
    const [selectedModel, setSelectedModel] = useState<string>("")
    const [result, setResult] = useState<any>(null)

    // Logs State
    const [logs, setLogs] = useState<SentimentLog[]>([])
    const [logsLoading, setLogsLoading] = useState(false)
    const [showPendingOnly, setShowPendingOnly] = useState(true)
    const [selectedLog, setSelectedLog] = useState<SentimentLog | null>(null)
    const [reviewDialogOpen, setReviewDialogOpen] = useState(false)
    const [correction, setCorrection] = useState("")
    const [reviewNotes, setReviewNotes] = useState("")
    const [addSynonymWord, setAddSynonymWord] = useState("")
    const [addSynonymCategory, setAddSynonymCategory] = useState("")

    // Synonyms State
    const [synonyms, setSynonyms] = useState<Synonym[]>([])
    const [synonymsLoading, setSynonymsLoading] = useState(false)
    const [newSynonymWord, setNewSynonymWord] = useState("")
    const [newSynonymCategory, setNewSynonymCategory] = useState("")

    // Patterns/Stats State
    const [patterns, setPatterns] = useState<Pattern[]>([])
    const [stats, setStats] = useState<Stats | null>(null)
    const [selectedReviewModel, setSelectedReviewModel] = useState<string>("")

    useEffect(() => {
        fetchModels()
    }, [])

    useEffect(() => {
        if (activeTab === "logs") fetchLogs()
        if (activeTab === "synonyms") fetchSynonyms()
        if (activeTab === "stats") {
            fetchPatterns()
            fetchStats()
        }
    }, [activeTab, showPendingOnly])

    async function fetchModels() {
        try {
            const res = await api.get("/admin/models")
            setModels(res.data)
        } catch (error) {
            console.error(error)
        }
    }

    const fetchLogs = useCallback(async () => {
        setLogsLoading(true)
        try {
            const params = showPendingOnly ? { pending: "true" } : { limit: 100 }
            const res = await api.get("/ai/sentiment/logs", { params })
            setLogs(res.data.logs || [])
        } catch (error: any) {
            toast.error("Falha ao carregar logs")
        } finally {
            setLogsLoading(false)
        }
    }, [showPendingOnly])

    async function fetchSynonyms() {
        setSynonymsLoading(true)
        try {
            const res = await api.get("/ai/sentiment/synonyms")
            setSynonyms(res.data.synonyms || [])
        } catch (error: any) {
            toast.error("Falha ao carregar sinônimos")
        } finally {
            setSynonymsLoading(false)
        }
    }

    async function fetchPatterns() {
        try {
            const res = await api.get("/ai/sentiment/patterns")
            setPatterns(res.data.patterns || [])
        } catch (error: any) {
            console.error("Patterns error:", error)
        }
    }

    async function fetchStats() {
        try {
            const res = await api.get("/ai/sentiment/stats")
            setStats(res.data)
        } catch (error: any) {
            console.error("Stats error:", error)
        }
    }

    async function handleAnalyze() {
        setLoading(true)
        setResult(null)
        try {
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
                model_id: selectedModel || undefined
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

    function openReviewDialog(log: SentimentLog) {
        setSelectedLog(log)
        setCorrection(log.correction || "")
        setReviewNotes(log.notes || "")
        setAddSynonymWord("")
        setAddSynonymCategory(log.classification || "")
        setReviewDialogOpen(true)
    }

    async function handleReviewSubmit() {
        if (!selectedLog) return
        try {
            const payload: any = {
                correction: correction || undefined,
                notes: reviewNotes || undefined
            }
            if (addSynonymWord && addSynonymCategory) {
                payload.add_synonym = {
                    word: addSynonymWord,
                    category: addSynonymCategory
                }
            }
            await api.post(`/ai/sentiment/logs/${selectedLog.id}/review`, payload)
            toast.success("Log revisado com sucesso!")
            setReviewDialogOpen(false)
            fetchLogs()
        } catch (error: any) {
            toast.error("Falha ao revisar log")
        }
    }

    async function handleEvaluateWithAI() {
        if (!selectedLog) return
        try {
            toast.loading("IA avaliando...")
            const payload = selectedReviewModel && selectedReviewModel !== "auto" ? { modelId: selectedReviewModel } : {}
            const res = await api.post(`/ai/sentiment/logs/${selectedLog.id}/evaluate`, payload)
            toast.dismiss()

            if (res.data.category) {
                setCorrection(res.data.category)
                setReviewNotes(res.data.reasoning || "Sugerido por IA")
                toast.success(`IA Sugere: ${res.data.category}`)
            } else {
                toast.warning("IA não conseguiu determinar a categoria")
            }
        } catch (error: any) {
            toast.dismiss()
            toast.error("Falha na avaliação da IA")
        }
    }

    async function handleAddSynonym() {
        if (!newSynonymWord || !newSynonymCategory) {
            toast.error("Preencha palavra e categoria")
            return
        }
        try {
            await api.post("/ai/sentiment/synonyms", {
                word: newSynonymWord,
                category: newSynonymCategory
            })
            toast.success("Sinônimo adicionado!")
            setNewSynonymWord("")
            setNewSynonymCategory("")
            fetchSynonyms()
        } catch (error: any) {
            toast.error("Falha ao adicionar sinônimo")
        }
    }

    async function handleDeleteSynonym(id: string) {
        try {
            await api.delete(`/ai/sentiment/synonyms/${id}`)
            toast.success("Sinônimo removido!")
            fetchSynonyms()
        } catch (error: any) {
            toast.error("Falha ao remover sinônimo")
        }
    }

    async function handlePromotePattern(pattern: Pattern) {
        try {
            await api.post("/ai/sentiment/synonyms", {
                word: pattern.word,
                category: pattern.category
            })
            toast.success(`Padrão "${pattern.word}" promovido a sinônimo!`)
            fetchPatterns()
            fetchSynonyms()
        } catch (error: any) {
            toast.error("Falha ao promover padrão")
        }
    }

    const getSourceColor = (source: string) => {
        const colors: Record<string, string> = {
            'cache': 'text-green-400 border-green-400/30 bg-green-400/10',
            'learned_cache': 'text-green-400 border-green-400/30 bg-green-400/10',
            'ai_classifier': 'text-purple-400 border-purple-400/30 bg-purple-400/10',
            'fallback': 'text-orange-400 border-orange-400/30 bg-orange-400/10',
            'sticky_session': 'text-amber-400 border-amber-400/30 bg-amber-400/10',
            'rule_match': 'text-blue-400 border-blue-400/30 bg-blue-400/10',
            'exception_pattern_match': 'text-red-400 border-red-400/30 bg-red-400/10'
        }
        return colors[source] || 'text-white/60 border-white/30'
    }

    return (
        <div className="p-8 space-y-6 text-white max-w-7xl mx-auto">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <BrainCircuit className="h-8 w-8 text-purple-400" />
                        Sentiment Analysis Hub
                    </h2>
                    <p className="text-white/60 mt-2">Teste, revise e gerencie o sistema de aprendizado de sentimentos.</p>
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="grid w-full grid-cols-4 bg-zinc-900 border border-white/10">
                    <TabsTrigger value="tester" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">
                        <Play className="h-4 w-4 mr-2" /> Tester
                    </TabsTrigger>
                    <TabsTrigger value="logs" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">
                        <BookOpen className="h-4 w-4 mr-2" /> Logs
                        {stats?.pendingReviews ? (
                            <Badge className="ml-2 bg-orange-500 text-white text-xs">{stats.pendingReviews}</Badge>
                        ) : null}
                    </TabsTrigger>
                    <TabsTrigger value="synonyms" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">
                        <GraduationCap className="h-4 w-4 mr-2" /> Sinônimos
                    </TabsTrigger>
                    <TabsTrigger value="stats" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">
                        <BarChart3 className="h-4 w-4 mr-2" /> Estatísticas
                    </TabsTrigger>
                </TabsList>

                {/* TESTER TAB */}
                <TabsContent value="tester" className="space-y-6">
                    <div className="flex gap-2 justify-end">
                        <Button variant="outline" onClick={() => loadScenario("sticky")} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                            <Layers className="mr-2 h-4 w-4" /> Sticky Test
                        </Button>
                        <Button variant="outline" onClick={() => loadScenario("exception")} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                            <AlertTriangle className="mr-2 h-4 w-4" /> Exception Test
                        </Button>
                        <Button variant="outline" onClick={() => loadScenario("menu")} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                            <ArrowRight className="mr-2 h-4 w-4" /> Menu Test
                        </Button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* Inputs Column */}
                        <div className="space-y-6">
                            <Card className="bg-zinc-950 border-white/10 text-white">
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
                                            placeholder="Ex: Quero cotar um frete"
                                            className="bg-white/5 border-white/10 text-white"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>2. Contexto (Previous Message)</Label>
                                        <Textarea
                                            value={context}
                                            onChange={e => setContext(e.target.value)}
                                            placeholder="Ex: Olá, bem-vindo!"
                                            className="bg-white/5 border-white/10 text-white min-h-[80px]"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label className="flex justify-between">
                                            <span>3. Status (JSON)</span>
                                            <span className="text-xs text-white/40">Sticky Session</span>
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

                            <Card className="bg-zinc-950 border-white/10 text-white">
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
                                            className="bg-white/5 border-white/10 text-white"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>5. Exceções (JSON)</Label>
                                        <Textarea
                                            value={exceptions}
                                            onChange={e => setExceptions(e.target.value)}
                                            className="bg-white/5 border-white/10 text-white font-mono min-h-[80px]"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>AI Model (Fallback)</Label>
                                        <Select value={selectedModel} onValueChange={setSelectedModel}>
                                            <SelectTrigger className="bg-white/5 border-white/10 text-white">
                                                <SelectValue placeholder="Select a model for AI Analysis" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                                {models.map(m => (
                                                    <SelectItem key={m.id} value={m.id}>{m.name} ({m.provider})</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <Button onClick={handleAnalyze} disabled={loading} className="w-full bg-white text-black hover:bg-zinc-200 mt-4">
                                        {loading ? "Analisando..." : <><Play className="mr-2 h-4 w-4" /> Executar Análise</>}
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Results Column */}
                        <div className="space-y-6">
                            <Card className="bg-zinc-900 border-white/10 text-white h-full">
                                <CardHeader>
                                    <CardTitle>Resultado</CardTitle>
                                    <CardDescription className="text-white/60">Decisão tomada pelo orquestrador</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {result ? (
                                        <div className="space-y-8 animate-in fade-in duration-500">
                                            <div className="text-center py-8 bg-black/20 rounded-lg border border-white/5">
                                                <p className="text-sm text-white/40 mb-2">CLASSIFICAÇÃO FINAL</p>
                                                <Badge className={`text-2xl px-4 py-2 border-none shadow-lg ${result.classification === 'incompreendido'
                                                    ? 'bg-orange-500 hover:bg-orange-600'
                                                    : 'bg-blue-500 hover:bg-blue-600'
                                                    }`}>
                                                    {result.classification?.toUpperCase()}
                                                </Badge>
                                            </div>

                                            <div className="space-y-4">
                                                <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5">
                                                    <span className="text-white/60">Fonte da Decisão</span>
                                                    <Badge variant="outline" className={getSourceColor(result.source)}>
                                                        {result.source?.replace(/_/g, ' ').toUpperCase()}
                                                    </Badge>
                                                </div>

                                                <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5">
                                                    <span className="text-white/60">Validado por IA?</span>
                                                    <span className={result.ai_validated ? "text-purple-400 font-bold" : "text-white/40"}>
                                                        {result.ai_validated ? "SIM ✓" : "NÃO"}
                                                    </span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5">
                                                    <span className="text-white/60">Exceção Detectada?</span>
                                                    <span className={result.is_exception ? "text-red-400 font-bold" : "text-green-400"}>
                                                        {result.is_exception ? "SIM" : "NÃO"}
                                                    </span>
                                                </div>

                                                <div className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5">
                                                    <span className="text-white/60">Status Ativo Anterior</span>
                                                    <span className="font-mono text-amber-400">
                                                        {result.active_status || "null"}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="mt-6">
                                                <Label className="mb-2 block">Raw Response</Label>
                                                <pre className="bg-black/50 p-4 rounded text-xs font-mono overflow-auto border border-white/5 text-white/70 max-h-64">
                                                    {JSON.stringify(result, null, 2)}
                                                </pre>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="h-64 flex flex-col items-center justify-center text-white/20">
                                            <BrainCircuit className="h-16 w-16 mb-4 opacity-50" />
                                            <p>Aguardando análise...</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>

                {/* LOGS TAB */}
                <TabsContent value="logs" className="space-y-6">
                    <Card className="bg-zinc-950 border-white/10 text-white">
                        <CardHeader>
                            <div className="flex justify-between items-center">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <BookOpen className="h-5 w-5 text-blue-400" /> Logs de Classificação
                                    </CardTitle>
                                    <CardDescription className="text-white/60">
                                        Revise e corrija classificações para melhorar o sistema.
                                    </CardDescription>
                                </div>
                                <div className="flex gap-2">
                                    <Button
                                        variant={showPendingOnly ? "default" : "outline"}
                                        onClick={() => setShowPendingOnly(!showPendingOnly)}
                                        className={showPendingOnly ? "bg-orange-500 hover:bg-orange-600" : "border-white/10 text-white bg-white/5"}
                                    >
                                        <Clock className="h-4 w-4 mr-2" />
                                        {showPendingOnly ? "Pendentes" : "Todos"}
                                    </Button>
                                    <Button variant="outline" onClick={fetchLogs} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                                        <RefreshCw className={`h-4 w-4 ${logsLoading ? 'animate-spin' : ''}`} />
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[500px]">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-white/10 hover:bg-transparent">
                                            <TableHead className="text-white/60">Intent</TableHead>
                                            <TableHead className="text-white/60">Classificação</TableHead>
                                            <TableHead className="text-white/60">Fonte</TableHead>
                                            <TableHead className="text-white/60">Confiança</TableHead>
                                            <TableHead className="text-white/60">Tokens</TableHead>
                                            <TableHead className="text-white/60">Status</TableHead>
                                            <TableHead className="text-white/60 text-right">Ações</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {logs.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={7} className="text-center text-white/40 py-12">
                                                    {logsLoading ? "Carregando..." : "Nenhum log encontrado"}
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            logs.map(log => (
                                                <TableRow key={log.id} className="border-white/10 hover:bg-white/5">
                                                    <TableCell className="max-w-[200px] truncate font-mono text-sm">
                                                        {log.intent}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge className={log.classification === 'incompreendido'
                                                            ? 'bg-orange-500/20 text-orange-400 border-orange-400/30'
                                                            : 'bg-blue-500/20 text-blue-400 border-blue-400/30'
                                                        }>
                                                            {log.classification}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge variant="outline" className={getSourceColor(log.source)}>
                                                            {log.source}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell>
                                                        <span className={`font-mono ${log.confidence >= 0.8 ? 'text-green-400' : log.confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                            {(log.confidence * 100).toFixed(0)}%
                                                        </span>
                                                    </TableCell>
                                                    <TableCell className="font-mono text-white/60">
                                                        {log.tokenUsage}
                                                    </TableCell>
                                                    <TableCell>
                                                        {log.reviewed ? (
                                                            <CheckCircle className="h-4 w-4 text-green-400" />
                                                        ) : (
                                                            <Clock className="h-4 w-4 text-orange-400" />
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => openReviewDialog(log)}
                                                            className="hover:bg-white/10"
                                                        >
                                                            <Eye className="h-4 w-4" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* SYNONYMS TAB */}
                <TabsContent value="synonyms" className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <Card className="bg-zinc-950 border-white/10 text-white">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Plus className="h-5 w-5 text-green-400" /> Adicionar Sinônimo
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Palavra/Frase</Label>
                                    <Input
                                        value={newSynonymWord}
                                        onChange={e => setNewSynonymWord(e.target.value)}
                                        placeholder="Ex: cotasao"
                                        className="bg-white/5 border-white/10 text-white"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Categoria</Label>
                                    <Input
                                        value={newSynonymCategory}
                                        onChange={e => setNewSynonymCategory(e.target.value)}
                                        placeholder="Ex: cotacao"
                                        className="bg-white/5 border-white/10 text-white"
                                    />
                                </div>
                                <Button onClick={handleAddSynonym} className="w-full bg-green-500 hover:bg-green-600 text-white">
                                    <Plus className="h-4 w-4 mr-2" /> Adicionar
                                </Button>
                            </CardContent>
                        </Card>

                        <Card className="bg-zinc-950 border-white/10 text-white lg:col-span-2">
                            <CardHeader>
                                <div className="flex justify-between items-center">
                                    <div>
                                        <CardTitle className="flex items-center gap-2">
                                            <GraduationCap className="h-5 w-5 text-purple-400" /> Sinônimos Aprendidos
                                        </CardTitle>
                                        <CardDescription className="text-white/60">
                                            {synonyms.length} sinônimos no cache
                                        </CardDescription>
                                    </div>
                                    <Button variant="outline" onClick={fetchSynonyms} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                                        <RefreshCw className={`h-4 w-4 ${synonymsLoading ? 'animate-spin' : ''}`} />
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <ScrollArea className="h-[350px]">
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="border-white/10 hover:bg-transparent">
                                                <TableHead className="text-white/60">Palavra</TableHead>
                                                <TableHead className="text-white/60">Categoria</TableHead>
                                                <TableHead className="text-white/60">Fonte</TableHead>
                                                <TableHead className="text-white/60">Uso</TableHead>
                                                <TableHead className="text-white/60 text-right">Ações</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {synonyms.length === 0 ? (
                                                <TableRow>
                                                    <TableCell colSpan={5} className="text-center text-white/40 py-12">
                                                        {synonymsLoading ? "Carregando..." : "Nenhum sinônimo cadastrado"}
                                                    </TableCell>
                                                </TableRow>
                                            ) : (
                                                synonyms.map(syn => (
                                                    <TableRow key={syn.id} className="border-white/10 hover:bg-white/5">
                                                        <TableCell className="font-mono">{syn.word}</TableCell>
                                                        <TableCell>
                                                            <Badge className="bg-blue-500/20 text-blue-400 border-blue-400/30">
                                                                {syn.category}
                                                            </Badge>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Badge variant="outline" className={
                                                                syn.source === 'admin' ? 'text-purple-400 border-purple-400/30' : 'text-green-400 border-green-400/30'
                                                            }>
                                                                {syn.source}
                                                            </Badge>
                                                        </TableCell>
                                                        <TableCell className="font-mono text-white/60">
                                                            {syn.useCount}x
                                                        </TableCell>
                                                        <TableCell className="text-right">
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDeleteSynonym(syn.id)}
                                                                className="hover:bg-red-500/20 text-red-400"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                ))
                                            )}
                                        </TableBody>
                                    </Table>
                                </ScrollArea>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* STATS TAB */}
                <TabsContent value="stats" className="space-y-6">
                    {/* New Components */}
                    <div className="flex flex-col gap-6">
                        <FinancialSavingsCard />
                        <PerformanceStats />
                    </div>

                    {/* Keep Overview Cards for Summary */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                        <Card className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30 text-white">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-white/60">Total Logs</p>
                                        <p className="text-3xl font-bold">{stats?.totalLogs || 0}</p>
                                    </div>
                                    <BookOpen className="h-8 w-8 text-blue-400/50" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-500/30 text-white">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-white/60">Cache Hits Global</p>
                                        <p className="text-3xl font-bold">{stats?.cacheHits || 0}</p>
                                    </div>
                                    <Zap className="h-8 w-8 text-green-400/50" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30 text-white">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-white/60">Sinônimos</p>
                                        <p className="text-3xl font-bold">{stats?.totalSynonyms || 0}</p>
                                    </div>
                                    <GraduationCap className="h-8 w-8 text-purple-400/50" />
                                </div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gradient-to-br from-orange-500/20 to-orange-600/10 border-orange-500/30 text-white">
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-white/60">Pendentes</p>
                                        <p className="text-3xl font-bold">{stats?.pendingReviews || 0}</p>
                                    </div>
                                    <Clock className="h-8 w-8 text-orange-400/50" />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Patterns for Auto-Learning */}
                    <Card className="bg-zinc-950 border-white/10 text-white">
                        <CardHeader>
                            <div className="flex justify-between items-center">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <TrendingUp className="h-5 w-5 text-amber-400" /> Padrões Candidatos
                                    </CardTitle>
                                    <CardDescription className="text-white/60">
                                        Palavras frequentes que podem virar sinônimos.
                                    </CardDescription>
                                </div>
                                <Button variant="outline" onClick={fetchPatterns} className="border-white/10 text-white bg-white/5 hover:bg-white/10">
                                    <RefreshCw className="h-4 w-4" />
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[350px]">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-white/10 hover:bg-transparent">
                                            <TableHead className="text-white/60">Palavra</TableHead>
                                            <TableHead className="text-white/60">Categoria</TableHead>
                                            <TableHead className="text-white/60">Ocorrências</TableHead>
                                            <TableHead className="text-white/60">Confiança Média</TableHead>
                                            <TableHead className="text-white/60 text-right">Ações</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {patterns.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center text-white/40 py-12">
                                                    Nenhum padrão candidato encontrado
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            patterns.map(pattern => (
                                                <TableRow key={pattern.id} className="border-white/10 hover:bg-white/5">
                                                    <TableCell className="font-mono">{pattern.word}</TableCell>
                                                    <TableCell>
                                                        <Badge className="bg-amber-500/20 text-amber-400 border-amber-400/30">
                                                            {pattern.category}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="font-mono">{pattern.occurrenceCount}x</TableCell>
                                                    <TableCell>
                                                        <span className={`font-mono ${pattern.avgConfidence >= 0.8 ? 'text-green-400' : 'text-yellow-400'}`}>
                                                            {(pattern.avgConfidence * 100).toFixed(0)}%
                                                        </span>
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => handlePromotePattern(pattern)}
                                                            className="border-green-400/30 text-green-400 hover:bg-green-400/20"
                                                        >
                                                            <CheckCircle className="h-4 w-4 mr-1" /> Promover
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Review Dialog */}
            <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
                <DialogContent className="bg-zinc-950 border-white/10 text-white max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Eye className="h-5 w-5 text-blue-400" /> Revisar Classificação
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            Corrija a classificação e opcionalmente adicione um sinônimo.
                        </DialogDescription>
                    </DialogHeader>

                    {selectedLog && (
                        <div className="space-y-6 py-4">
                            <div className="bg-white/5 p-4 rounded-lg space-y-3">
                                <div>
                                    <Label className="text-white/60">Intent</Label>
                                    <p className="font-mono text-lg">{selectedLog.intent}</p>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <Label className="text-white/60">Classificação Atual</Label>
                                        <Badge className="mt-1 bg-blue-500/20 text-blue-400 border-blue-400/30">
                                            {selectedLog.classification}
                                        </Badge>
                                    </div>
                                    <div>
                                        <Label className="text-white/60">Fonte</Label>
                                        <Badge variant="outline" className={`mt-1 ${getSourceColor(selectedLog.source)}`}>
                                            {selectedLog.source}
                                        </Badge>
                                    </div>
                                </div>
                                <div>
                                    <Label className="text-white/60">Categorias Disponíveis</Label>
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {selectedLog.categories.map(cat => (
                                            <Badge key={cat} variant="outline" className="text-white/60 border-white/20">
                                                {cat}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            </div>



                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <Label>Correção (classificação correta)</Label>
                                    <div className="flex items-center gap-2">
                                        <Select value={selectedReviewModel} onValueChange={setSelectedReviewModel}>
                                            <SelectTrigger className="h-6 w-[140px] text-xs bg-white/5 border-white/10 text-white">
                                                <SelectValue placeholder="Modelo (Auto)" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-zinc-950 border-white/10 text-white">
                                                <SelectItem value="auto">Automático</SelectItem>
                                                {models.map(m => (
                                                    <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            onClick={handleEvaluateWithAI}
                                            className="h-6 text-xs bg-purple-500/10 text-purple-400 border-purple-500/20 hover:bg-purple-500/20"
                                        >
                                            <Zap className="h-3 w-3 mr-1" /> Avaliar com IA
                                        </Button>
                                    </div>
                                    <Input
                                        value={correction}
                                        onChange={e => setCorrection(e.target.value)}
                                        placeholder="Ex: cotacao"
                                        className="bg-white/5 border-white/10 text-white"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label>Notas</Label>
                                    <Textarea
                                        value={reviewNotes}
                                        onChange={e => setReviewNotes(e.target.value)}
                                        placeholder="Observações sobre esta revisão..."
                                        className="bg-white/5 border-white/10 text-white min-h-[80px]"
                                    />
                                </div>

                                <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 space-y-3">
                                    <Label className="text-green-400">Adicionar Sinônimo (opcional)</Label>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Input
                                                value={addSynonymWord}
                                                onChange={e => setAddSynonymWord(e.target.value)}
                                                placeholder="Palavra"
                                                className="bg-white/5 border-white/10 text-white"
                                            />
                                        </div>
                                        <div>
                                            <Input
                                                value={addSynonymCategory}
                                                onChange={e => setAddSynonymCategory(e.target.value)}
                                                placeholder="Categoria"
                                                className="bg-white/5 border-white/10 text-white"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setReviewDialogOpen(false)} className="border-white/10 text-white bg-white/5">
                            Cancelar
                        </Button>
                        <Button onClick={handleReviewSubmit} className="bg-blue-500 hover:bg-blue-600 text-white">
                            <CheckCircle className="h-4 w-4 mr-2" /> Salvar Revisão
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div >
    )
}

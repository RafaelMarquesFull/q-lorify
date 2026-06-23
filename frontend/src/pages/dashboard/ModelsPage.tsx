import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Cpu, Zap, Clock, Copy, Check } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"

interface Model {
    id: string
    name: string
    costIn: number
    costOut: number
    description: string | null
    rpm: number
    integrationGuide: string | null
    isOrchestrator: boolean
}

export default function ModelsPage() {
    const [models, setModels] = useState<Model[]>([])
    const [loading, setLoading] = useState(true)
    const [selectedModel, setSelectedModel] = useState<Model | null>(null)
    const [copied, setCopied] = useState(false)

    useEffect(() => {
        fetchModels()
    }, [])

    async function fetchModels() {
        try {
            const res = await api.get("/public/models")
            setModels(res.data || [])
        } catch {
            toast.error("Falha ao carregar modelos")
        } finally {
            setLoading(false)
        }
    }

    function copyToClipboard(text: string) {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    if (loading) {
        return (
            <div className="p-8 text-white">
                <div className="animate-pulse">Carregando modelos...</div>
            </div>
        )
    }

    return (
        <AnimatedGradientBg className="p-8 space-y-8 min-h-full">
            <div>
                <h2 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">Modelos Disponíveis</h2>
                <p className="text-muted-foreground mt-1">Explore os modelos de IA disponíveis para integração</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {models.map(model => (
                    <Card
                        key={model.id}
                        className={`group cursor-pointer transition-all duration-300 hover:scale-[1.02] ${model.isOrchestrator
                            ? 'glass-card border-primary/30 bg-primary/5 hover:bg-primary/10 hover:shadow-glow-primary'
                            : 'glass-subtle hover:bg-white/5'
                            }`}
                        onClick={() => setSelectedModel(model)}
                    >
                        <CardHeader className="pb-3">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                    {model.isOrchestrator ? (
                                        <div className="p-2 rounded-lg bg-primary/10 ring-1 ring-primary/20 group-hover:ring-primary/40 transition-all">
                                            <Zap className="h-5 w-5 text-primary" />
                                        </div>
                                    ) : (
                                        <div className="p-2 rounded-lg bg-white/5 ring-1 ring-white/10">
                                            <Cpu className="h-5 w-5 text-muted-foreground" />
                                        </div>
                                    )}
                                    <CardTitle className="text-lg group-hover:text-primary transition-colors">{model.name}</CardTitle>
                                </div>
                                {model.isOrchestrator && (
                                    <Badge className="bg-primary/20 text-primary border-primary/20 animate-pulse-glow">
                                        Funções
                                    </Badge>
                                )}
                            </div>
                            <CardDescription className="text-white/50 line-clamp-2">
                                {model.description || "Modelo de IA para processamento de texto"}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center gap-4 text-sm">
                                <div className="flex items-center gap-1 text-white/50">
                                    <span>
                                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(model.costIn)} / {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(model.costOut)}
                                    </span>
                                </div>
                                <div className="flex items-center gap-1 text-white/50">
                                    <Clock className="h-3 w-3" />
                                    <span>{model.rpm} RPM</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {models.length === 0 && (
                <div className="text-center py-12 text-white/50">
                    Nenhum modelo disponível no momento.
                </div>
            )}

            {/* Model Detail Dialog */}
            <Dialog open={!!selectedModel} onOpenChange={() => setSelectedModel(null)}>
                <DialogContent className="glass-ultra border-white/10 text-foreground sm:max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            {selectedModel?.isOrchestrator ? (
                                <Zap className="h-5 w-5 text-purple-400" />
                            ) : (
                                <Cpu className="h-5 w-5" />
                            )}
                            {selectedModel?.name}
                        </DialogTitle>
                        <DialogDescription className="text-white/60">
                            {selectedModel?.description || "Modelo de IA para processamento de texto"}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-6 py-4">
                        {/* Stats */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-white/5 rounded-lg p-4 text-center">
                                <p className="text-2xl font-bold text-emerald-400">${selectedModel?.costIn}</p>
                                <p className="text-xs text-white/50">Custo Input (1K tokens)</p>
                            </div>
                            <div className="bg-white/5 rounded-lg p-4 text-center">
                                <p className="text-2xl font-bold text-blue-400">${selectedModel?.costOut}</p>
                                <p className="text-xs text-white/50">Custo Output (1K tokens)</p>
                            </div>
                            <div className="bg-white/5 rounded-lg p-4 text-center">
                                <p className="text-2xl font-bold text-amber-400">{selectedModel?.rpm}</p>
                                <p className="text-xs text-white/50">Requisições/min</p>
                            </div>
                        </div>

                        {/* Integration Example */}
                        <div className="space-y-2">
                            <h4 className="font-medium flex items-center gap-2">
                                <Copy className="h-4 w-4" /> Como Integrar
                            </h4>
                            <div className="relative">
                                <pre className="bg-black/50 rounded-lg p-4 text-sm overflow-x-auto text-white/80">
                                    {`curl -X POST http://localhost:8001/api/chat/completions \\
  -H "Authorization: Bearer sk-agent-SUA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${selectedModel?.name}",
    "messages": [{
      "role": "user",
      "content": "Sua mensagem aqui"
    }]
  }'`}
                                </pre>
                                <button
                                    onClick={() => copyToClipboard(`curl -X POST http://localhost:8001/api/chat/completions -H "Authorization: Bearer sk-agent-SUA_API_KEY" -H "Content-Type: application/json" -d '{"model": "${selectedModel?.name}", "messages": [{"role": "user", "content": "Sua mensagem"}]}'`)}
                                    className="absolute top-2 right-2 p-2 bg-white/10 rounded hover:bg-white/20"
                                >
                                    {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                                </button>
                            </div>
                        </div>

                        {/* Additional Integration Guide */}
                        {selectedModel?.integrationGuide && (
                            <div className="space-y-2">
                                <h4 className="font-medium">Guia de Integração</h4>
                                <div className="bg-white/5 rounded-lg p-4 text-sm text-white/70 whitespace-pre-wrap">
                                    {selectedModel.integrationGuide}
                                </div>
                            </div>
                        )}

                        {selectedModel?.isOrchestrator && (
                            <div className="space-y-4">
                                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
                                    <p className="text-sm text-purple-300 font-medium mb-2">
                                        🚀 Modelo Orquestrador
                                    </p>
                                    <p className="text-sm text-white/60">
                                        Este modelo executa suas funções de extração automaticamente.
                                        Configure suas funções em <a href="/dashboard/functions" className="text-purple-400 underline">Minhas Funções</a>.
                                    </p>
                                </div>

                                <div className="bg-white/5 rounded-lg p-4">
                                    <p className="text-sm font-medium mb-2">📌 Formato de Padrões</p>
                                    <p className="text-xs text-white/60 mb-2">Use suas chaves configuradas para direcionar dados específicos:</p>
                                    <pre className="bg-black/30 rounded p-2 text-xs text-purple-200">{`CEP_origem: 01310-100
CEP_destino: 04567-890
CPF_remetente: 123.456.789-00`}</pre>
                                    <p className="text-xs text-white/40 mt-2">
                                        💡 Se não usar o formato, a IA classificará automaticamente.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </AnimatedGradientBg>
    )
}

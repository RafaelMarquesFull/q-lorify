import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Bot, User, Trash2 } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import api from "@/lib/api"
import { useAuthStore } from "@/store/auth"
import { toast } from "sonner"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"

interface Message {
    role: "user" | "assistant"
    content: string
}

interface Model {
    id: string
    name: string
    provider: string
}

export default function Playground() {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [loading, setLoading] = useState(false)
    const [models, setModels] = useState<Model[]>([])
    const [selectedModel, setSelectedModel] = useState<string>("")
    const [systemPrompt, setSystemPrompt] = useState<string>("")
    const [streamingContent, setStreamingContent] = useState<string>("")
    const scrollRef = useRef<HTMLDivElement>(null)
    const abortControllerRef = useRef<AbortController | null>(null)

    useEffect(() => {
        fetchModels()
    }, [])

    // Auto-scroll to bottom when messages change or streaming content updates
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages, streamingContent])

    async function fetchModels() {
        try {
            const res = await api.get("/public/models")
            setModels(res.data)
            if (res.data.length > 0) {
                // Try to select gpt-4 or first
                const defaultModel = res.data.find((m: Model) => m.name.toLowerCase().includes('gpt-4')) || res.data[0]
                setSelectedModel(defaultModel.id)
            }
        } catch (error) {
            toast.error("Falha ao carregar modelos")
        }
    }

    const sendMessage = useCallback(async () => {
        if (!input.trim() || !selectedModel || loading) return

        const newMessage: Message = { role: "user", content: input }
        const updatedMessages = [...messages, newMessage]
        setMessages(updatedMessages)
        setInput("")
        setLoading(true)
        setStreamingContent("")

        const CONTEXT_WINDOW_LIMIT = 10
        const fullMessages = [
            ...(systemPrompt.trim() ? [{ role: "system" as const, content: systemPrompt.trim() }] : []),
            ...updatedMessages.slice(-CONTEXT_WINDOW_LIMIT)
        ]

        // Try streaming first
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
        const token = useAuthStore.getState().token

        const controller = new AbortController()
        abortControllerRef.current = controller

        try {
            const response = await fetch(`${apiUrl}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    model: selectedModel,
                    messages: fullMessages,
                    stream: true,
                }),
                signal: controller.signal,
            })

            if (!response.ok) {
                // If streaming fails, fallback to non-streaming
                const errorData = await response.json().catch(() => ({ error: response.statusText }))
                const errorMsg = errorData?.error?.message || errorData?.error || `Erro ${response.status}`
                toast.error(errorMsg)
                setMessages(prev => [...prev, { role: "assistant", content: `Erro: ${errorMsg}` }])
                setLoading(false)
                return
            }

            const contentType = response.headers.get('content-type') || ''

            if (contentType.includes('text/event-stream') && response.body) {
                // SSE Streaming mode
                const reader = response.body.getReader()
                const decoder = new TextDecoder()
                let accumulated = ""
                let buffer = ""

                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break

                    buffer += decoder.decode(value, { stream: true })

                    // Process complete SSE lines from buffer
                    const lines = buffer.split('\n')
                    // Keep the last potentially incomplete line in buffer
                    buffer = lines.pop() || ""

                    for (const line of lines) {
                        const trimmed = line.trim()
                        if (!trimmed) continue

                        if (trimmed === 'data: [DONE]') {
                            // Stream complete
                            continue
                        }

                        if (trimmed.startsWith('data: ')) {
                            try {
                                const chunk = JSON.parse(trimmed.slice(6))
                                const delta = chunk?.choices?.[0]?.delta
                                if (delta?.content) {
                                    accumulated += delta.content
                                    setStreamingContent(accumulated)
                                }
                            } catch {
                                // Ignore malformed chunks
                            }
                        }
                    }
                }

                // Finalize: move accumulated content to messages
                if (accumulated) {
                    setMessages(prev => [...prev, { role: "assistant", content: accumulated }])
                }
                setStreamingContent("")
            } else {
                // Non-streaming JSON response (e.g. orchestrator or sentiment models)
                const data = await response.json()
                const content = data?.choices?.[0]?.message?.content || JSON.stringify(data, null, 2)
                setMessages(prev => [...prev, { role: "assistant", content }])
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                // User cancelled
                if (streamingContent) {
                    setMessages(prev => [...prev, { role: "assistant", content: streamingContent + "\n\n*(cancelado)*" }])
                    setStreamingContent("")
                }
            } else {
                const errorMsg = error.message || "Falha ao gerar resposta"
                toast.error(`Erro: ${errorMsg}`)
                setMessages(prev => [...prev, { role: "assistant", content: `Erro: ${errorMsg}` }])
            }
        } finally {
            setLoading(false)
            abortControllerRef.current = null
        }
    }, [input, selectedModel, loading, messages, systemPrompt, streamingContent])

    function handleStop() {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
        }
    }

    return (
        <div className="h-[calc(100vh-44px)] flex text-foreground overflow-hidden ">
            {/* Settings Sidebar */}
            <div className="w-80 border-r border-white/10 p-6 space-y-6 overflow-y-auto glass-ultra rounded-l-3xl">
                <div className="space-y-4">
                    <h2 className="text-xl font-semibold">Configuração</h2>
                    <div className="space-y-2">
                        <label className="text-sm text-muted-foreground">Modelo</label>
                        <Select value={selectedModel} onValueChange={setSelectedModel}>
                            <SelectTrigger className="bg-white/5 border-white/10 text-foreground">
                                <SelectValue placeholder="Selecionar Modelo" />
                            </SelectTrigger>
                            <SelectContent className="glass-ultra border-white/10 text-foreground">
                                {models.map((m) => (
                                    <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm text-muted-foreground">Prompt do Sistema</label>
                        <Textarea
                            value={systemPrompt}
                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSystemPrompt(e.target.value)}
                            placeholder="Prompt do sistema (opcional)..."
                            className="bg-white/5 border-white/10 text-foreground h-32 text-xs focus:border-primary/50 transition-colors"
                        />
                        <p className="text-xs text-muted-foreground/60">Define o comportamento padrão do modelo.</p>
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 flex flex-col relative">
                <AnimatedGradientBg className="absolute inset-0 z-0" variant="subtle" />
                <div className="relative z-10 flex-1 flex flex-col">
                    <ScrollArea className="flex-1 p-6" ref={scrollRef}>
                        <div className="max-w-3xl mx-auto space-y-6">
                            {messages.length === 0 && !streamingContent && (
                                <div className="flex flex-col items-center justify-center h-[50vh] text-muted-foreground/40">
                                    <Bot className="h-12 w-12 mb-4 animate-float-slow" />
                                    <p>Selecione um agente e comece a conversar.</p>
                                </div>
                            )}
                            {messages.map((m, i) => (
                                <div key={i} className={`flex items-start gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${m.role === 'user' ? 'bg-primary text-primary-foreground' : 'glass-ultra text-foreground'}`}>
                                        {m.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                                    </div>
                                    <div className={`px-4 py-3 rounded-2xl max-w-[80%] shadow-md backdrop-blur-sm ${m.role === 'user' ? 'bg-primary text-primary-foreground rounded-tr-sm' : 'glass-subtle text-foreground rounded-tl-sm border border-white/5'}`}>
                                        <div className="prose prose-invert prose-sm">
                                            <ReactMarkdown>{m.content}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {/* Streaming indicator — shows live content as it arrives */}
                            {streamingContent && (
                                <div className="flex items-start gap-4">
                                    <div className="w-8 h-8 rounded-full glass-ultra flex items-center justify-center">
                                        <Bot className="w-5 h-5 text-foreground" />
                                    </div>
                                    <div className="px-4 py-3 rounded-2xl max-w-[80%] shadow-md backdrop-blur-sm glass-subtle text-foreground rounded-tl-sm border border-white/5">
                                        <div className="prose prose-invert prose-sm">
                                            <ReactMarkdown>{streamingContent}</ReactMarkdown>
                                            <span className="inline-block w-2 h-4 bg-primary/70 animate-pulse ml-0.5" />
                                        </div>
                                    </div>
                                </div>
                            )}
                            {/* Loading dots when waiting for first token */}
                            {loading && !streamingContent && (
                                <div className="flex items-start gap-4">
                                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center animate-pulse">
                                        <Bot className="w-5 h-5 text-primary" />
                                    </div>
                                    <div className="px-4 py-3 rounded-2xl glass-subtle text-foreground rounded-tl-sm border border-white/5">
                                        <div className="flex gap-1 items-center h-5">
                                            <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-1.5 h-1.5 bg-foreground/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </ScrollArea>

                    {/* Input Area */}
                    <div className="p-4 border-t border-white/10 glass-ultra">
                        <div className="max-w-3xl mx-auto flex gap-3">
                            <Button variant="ghost" size="icon" onClick={() => { setMessages([]); setStreamingContent("") }} className="text-white/40 hover:text-white">
                                <Trash2 className="w-5 h-5" />
                            </Button>
                            <Textarea
                                value={input}
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
                                placeholder="Digite sua mensagem..."
                                className="min-h-[50px] bg-white/5 border-white/10 text-foreground resize-none focus:border-primary/50 transition-colors"
                                onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault()
                                        sendMessage()
                                    }
                                }}
                            />
                            {loading ? (
                                <Button onClick={handleStop} className="h-[50px] w-[50px] p-0 bg-red-500/80 hover:bg-red-500" variant="glow">
                                    <div className="w-4 h-4 rounded-sm bg-white" />
                                </Button>
                            ) : (
                                <Button onClick={sendMessage} disabled={!input.trim()} className="h-[50px] w-[50px] p-0" variant="glow">
                                    <Send className="w-5 h-5" />
                                </Button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>

    )
}


import { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Loader2, TrendingUp, Zap } from "lucide-react"
import api from "@/lib/api"
import { Badge } from "@/components/ui/badge"

interface PerformanceData {
    hit_rates: {
        cache: number
        model: number
        ai: number
        rule: number
        guardrail: number
    }
    distribution: Record<string, number>
    latency_by_source: Record<string, number>
    total_requests: number
}

const COLORS = {
    cache: "#4ade80", // green-400
    model: "#60a5fa", // blue-400
    ai: "#c084fc",    // purple-400
    rule: "#2dd4bf",  // teal-400
    guardrail: "#f87171" // red-400
}

export function PerformanceStats({ domain = "transport" }: { domain?: string }) {
    const [data, setData] = useState<PerformanceData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchStats()
    }, [domain])

    async function fetchStats() {
        setLoading(true)
        try {
            const res = await api.get(`/ai/sentiment/stats/performance?domain=${domain}&days=7`)
            setData(res.data)
        } catch (error) {
            console.error("Failed to fetch performance stats", error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="h-64 flex items-center justify-center text-white/50"><Loader2 className="h-8 w-8 animate-spin" /></div>
    }

    if (!data) return null

    // Prepare Pie Data
    const pieData = [
        { name: "Cache (0ms)", value: data.hit_rates.cache, color: COLORS.cache },
        { name: "Local ML (High Speed)", value: data.hit_rates.model, color: COLORS.model },
        { name: "Rules/Guardrails", value: data.hit_rates.rule + data.hit_rates.guardrail, color: COLORS.rule },
        { name: "AI (Fallback)", value: data.hit_rates.ai, color: COLORS.ai },
    ].filter(d => d.value > 0)

    // Prepare Bar Data (Latency)
    const barData = Object.entries(data.latency_by_source)
        .map(([key, val]) => ({
            name: key.replace(/_/g, ' '),
            ms: Math.round(val)
        }))
        .sort((a, b) => a.ms - b.ms)

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-zinc-950 border-white/10 text-white">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-white/60">Latência Média Global</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold flex items-center gap-2">
                            {Math.round(
                                Object.values(data.latency_by_source).reduce((a, b) => a + b, 0) /
                                (Object.keys(data.latency_by_source).length || 1)
                            )}ms
                            <Zap className="h-4 w-4 text-yellow-400" />
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950 border-white/10 text-white">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-white/60">Taxa de Automação</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold flex items-center gap-2 text-green-400">
                            {100 - data.hit_rates.ai}%
                            <TrendingUp className="h-4 w-4" />
                        </div>
                        <p className="text-xs text-white/40">Requisições sem GPT-4</p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950 border-white/10 text-white">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-white/60">Contradições Bloqueadas</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold flex items-center gap-2 text-red-400">
                            {data.distribution.logic_guardrail || 0}
                            <Badge variant="outline" className="border-red-400/30 text-red-400 text-[10px] ml-2">SAFETY</Badge>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="bg-zinc-950 border-white/10 text-white">
                    <CardHeader>
                        <CardTitle>Distribuição de Tráfego</CardTitle>
                        <CardDescription className="text-white/60">Qual camada está respondendo às requisições?</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {pieData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", color: "#fff" }}
                                    itemStyle={{ color: "#fff" }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950 border-white/10 text-white">
                    <CardHeader>
                        <CardTitle>Latência por Camada (ms)</CardTitle>
                        <CardDescription className="text-white/60">Tempo de resposta comparativo</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={barData} layout="vertical" margin={{ left: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" horizontal={false} />
                                <XAxis type="number" stroke="#71717a" />
                                <YAxis dataKey="name" type="category" stroke="#71717a" width={100} tick={{ fontSize: 12 }} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", color: "#fff" }}
                                />
                                <Bar dataKey="ms" fill="#60a5fa" radius={[0, 4, 4, 0]}>
                                    {barData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.name.includes("ai") ? COLORS.ai : entry.name.includes("model") ? COLORS.model : COLORS.cache} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}

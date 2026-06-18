import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell, Legend, LineChart, Line } from "recharts"
import { useState, useEffect } from "react"
import { Activity, CreditCard, Zap, Sparkles, ArrowDownToLine, ArrowUpFromLine, Smile, Key, Timer } from "lucide-react"
import { BentoCard } from "@/components/bento-card"
import { StatCard } from "@/components/stat-card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import api from "@/lib/api"

interface DashboardStats {
    total_requests: number
    total_cost: number
    active_agents: number // kept for efficiency calc
    api_keys_count: number
    function_requests: number
    input_tokens: number
    output_tokens: number
    sentiment_requests: number
    avg_latency: number
}

interface ActivityItem {
    id: string
    description: string
    timestamp: string
    status: string
    meta: string
}

interface ChartData {
    name: string
    tokens?: number // keeping optional for backward compat if needed, but we use input/output/total now
    input: number
    output: number
    total: number
    cost: number
}

interface ApiKey {
    id: string
    name: string
    key: string
}

export default function DashboardOverview() {
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [chartData, setChartData] = useState<ChartData[]>([])
    const [costDistribution, setCostDistribution] = useState<{ name: string, value: number }[]>([])
    const [activity, setActivity] = useState<ActivityItem[]>([])
    const [_, setActivityPage] = useState(1)
    const [hasMoreActivity, setHasMoreActivity] = useState(true)
    const [isLoadingActivity, setIsLoadingActivity] = useState(false)
    const [apiKeys, setApiKeys] = useState<ApiKey[]>([])

    const [timeRange, setTimeRange] = useState("7d")
    const [selectedApiKey, setSelectedApiKey] = useState("all")
    const [loading, setLoading] = useState(true)

    const fetchData = async () => {
        setLoading(true)
        try {
            // Fetch Stats
            const statsRes = await api.get(`/dashboard/stats?timeRange=${timeRange}&apiKey=${selectedApiKey}`)
            setStats(statsRes.data)

            // Fetch Chart
            const chartRes = await api.get(`/dashboard/chart?timeRange=${timeRange}&apiKey=${selectedApiKey}`)
            setChartData(chartRes.data)

            // Fetch Cost Distribution
            const distRes = await api.get(`/dashboard/chart/distribution?timeRange=${timeRange}&apiKey=${selectedApiKey}`)
            setCostDistribution(distRes.data)

            // Initial Activity Fetch (Reset)
            setActivityPage(1)
            setHasMoreActivity(true)
            await fetchActivity(1, true) // Await this to ensure activity is loaded before stats if needed, or just call it.


        } catch (error) {
            console.error("Failed to fetch dashboard data:", error)
        } finally {
            setLoading(false)
        }
    }

    const fetchActivity = async (page: number, reset = false) => {
        try {
            setIsLoadingActivity(true)
            const limit = 6
            const res = await api.get(`/dashboard/activity?page=${page}&limit=${limit}`)
            const newData = res.data

            if (newData.length < limit) {
                setHasMoreActivity(false)
            }

            if (reset) {
                setActivity(newData)
            } else {
                setActivity(prev => [...prev, ...newData])
            }
        } catch (error) {
            console.error(error)
        } finally {
            setIsLoadingActivity(false)
        }
    }

    const handleActivityScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, clientHeight, scrollHeight } = e.currentTarget
        if (scrollHeight - scrollTop <= clientHeight + 50 && hasMoreActivity && !isLoadingActivity) {
            setActivityPage(prev => {
                const nextPage = prev + 1
                fetchActivity(nextPage)
                return nextPage
            })
        }
    }

    useEffect(() => {
        // Fetch API Keys once
        api.get("/keys").then(res => setApiKeys(res.data)).catch(console.error)
    }, [])

    useEffect(() => {
        fetchData()
    }, [timeRange, selectedApiKey])

    return (
        <div className="space-y-8 animate-fade-in pb-10">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent animate-fade-in">
                        Dashboard
                    </h2>
                    <p className="text-muted-foreground mt-2 text-lg">Visão geral do uso e desempenho da sua IA.</p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <Select value={selectedApiKey} onValueChange={setSelectedApiKey}>
                        <SelectTrigger className="w-[200px] bg-white/5 border-white/10 text-foreground">
                            <SelectValue placeholder="Todas as Chaves" />
                        </SelectTrigger>
                        <SelectContent className="glass-ultra border-white/10 text-foreground">
                            <SelectItem value="all">Todas as Chaves</SelectItem>
                            {apiKeys.map(k => (
                                <SelectItem key={k.id} value={k.key}>{k.name || k.key.substring(0, 8) + '...'}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <Tabs value={timeRange} onValueChange={setTimeRange} className="bg-white/5 p-1 rounded-lg border border-white/10">
                        <TabsList className="bg-transparent h-8 p-0">
                            <TabsTrigger value="24h" className="h-full px-3 text-xs data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-md transition-all">24h</TabsTrigger>
                            <TabsTrigger value="7d" className="h-full px-3 text-xs data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-md transition-all">7d</TabsTrigger>
                            <TabsTrigger value="30d" className="h-full px-3 text-xs data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-md transition-all">30d</TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <Button variant="glass" onClick={fetchData} className="hover:bg-primary/20 hover:text-primary transition-all duration-300">
                        <Sparkles className="mr-2 h-4 w-4" />
                        Atualizar
                    </Button>
                </div>
            </div>

            {/* Loading Overlay or Spinner could go here */}
            {loading && <div className="fixed inset-0 bg-background/50 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>}

            {/* Bento Grid Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 auto-rows-min">

                {/* Main Stats - Top Row */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-primary/5 to-transparent border-primary/10">
                    <StatCard
                        label="Total de Requisições"
                        value={stats?.total_requests.toLocaleString('pt-BR') || "0"}
                        icon={Activity}
                        trend="neutral"
                        trendValue="Requisições"
                        variant="ghost"
                        iconBgColor="hsla(var(--primary)/20%)"
                        iconColor="hsl(var(--primary))"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1">
                    <StatCard
                        label="Custo Total"
                        value={stats?.total_cost.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) || "R$ 0,00"}
                        icon={CreditCard}
                        trend="neutral"
                        trendValue="BRL"
                        variant="ghost"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1">
                    <StatCard
                        label="Chaves de API"
                        value={stats?.api_keys_count || 0}
                        icon={Key}
                        trend="neutral"
                        trendValue="Ativas"
                        variant="ghost"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1" className="bg-gradient-to-br from-accent/5 to-transparent border-accent/10">
                    <StatCard
                        label="Chamadas de Função"
                        value={stats?.function_requests.toLocaleString('pt-BR') || "0"}
                        icon={Zap}
                        trend="neutral"
                        trendValue="Execuções"
                        variant="ghost"
                        iconBgColor="hsla(var(--accent)/20%)"
                        iconColor="hsl(var(--accent))"
                        className="p-0"
                    />
                </BentoCard>

                {/* New Metric Cards - 2nd Row */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-pink-500/5 to-transparent border-pink-500/10">
                    <StatCard
                        label="Análise de Sentimento"
                        value={stats?.sentiment_requests.toLocaleString('pt-BR') || "0"}
                        icon={Smile}
                        trend="neutral"
                        trendValue="Requisições"
                        variant="ghost"
                        iconBgColor="rgba(236, 72, 153, 0.2)"
                        iconColor="rgb(236, 72, 153)"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1">
                    <StatCard
                        label="Tokens de Entrada"
                        value={stats?.input_tokens.toLocaleString('pt-BR') || "0"}
                        icon={ArrowDownToLine}
                        trend="neutral"
                        trendValue="Tokens"
                        variant="ghost"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1">
                    <StatCard
                        label="Tokens de Saída"
                        value={stats?.output_tokens.toLocaleString('pt-BR') || "0"}
                        icon={ArrowUpFromLine}
                        trend="neutral"
                        trendValue="Tokens"
                        variant="ghost"
                        className="p-0"
                    />
                </BentoCard>

                <BentoCard size="1x1" className="flex flex-col justify-center items-center text-center gap-3 bg-white/5 border-white/5">
                    <div className="flex flex-col items-center justify-center h-full w-full">
                        <Timer className="w-8 h-8 text-amber-400 mb-2 opacity-80" />
                        <h4 className="text-muted-foreground text-sm uppercase tracking-wider mb-1">Latência Média</h4>
                        <span className="text-2xl font-bold text-amber-400">
                            {stats?.avg_latency ? `${stats.avg_latency.toLocaleString('pt-BR')} ms` : '0 ms'}
                        </span>
                        <p className="text-xs text-muted-foreground">Tempo de Resposta</p>
                    </div>
                </BentoCard>


                {/* Input Tokens Chart - 2x1 */}
                <BentoCard size="1x2" glassmorphism className="flex flex-col md:col-span-2">
                    <div className="mb-2 flex justify-between items-start">
                        <div>
                            <h3 className="font-semibold text-lg flex items-center gap-2">
                                <ArrowDownToLine className="w-4 h-4 text-primary" />
                                Tokens de Entrada
                            </h3>
                            <p className="text-xs text-muted-foreground">Consumo de prompts</p>
                        </div>
                        <div className="text-2xl font-bold bg-primary/10 text-primary px-3 py-1 rounded-lg">
                            {stats?.input_tokens?.toLocaleString('pt-BR') || 0}
                        </div>
                    </div>
                    <div className="flex-1 w-full min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorInput" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="name"
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: 'hsl(var(--primary)/0.1)' }}
                                    contentStyle={{
                                        backgroundColor: 'hsl(var(--card))',
                                        borderColor: 'hsl(var(--border))',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Bar
                                    dataKey="input"
                                    name="Entrada"
                                    fill="url(#colorInput)"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </BentoCard>

                {/* Output Tokens Chart - 2x1 */}
                <BentoCard size="1x2" glassmorphism className="flex flex-col md:col-span-2">
                    <div className="mb-2">
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                            <ArrowUpFromLine className="w-4 h-4 text-accent" />
                            Tokens de Saída
                        </h3>
                        <p className="text-xs text-muted-foreground">Geração de respostas</p>
                    </div>
                    <div className="flex-1 w-full min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorOutput" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="hsl(var(--accent))" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="hsl(var(--accent))" stopOpacity={0.3} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="name"
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: 'hsl(var(--accent)/0.1)' }}
                                    contentStyle={{
                                        backgroundColor: 'hsl(var(--card))',
                                        borderColor: 'hsl(var(--border))',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Bar
                                    dataKey="output"
                                    name="Saída"
                                    fill="url(#colorOutput)"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </BentoCard>

                {/* Cost Chart - 2x1 */}
                <BentoCard size="1x2" glassmorphism className="flex flex-col md:col-span-2">
                    <div className="mb-2">
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-emerald-400" />
                            Evolução de Custos
                        </h3>
                        <p className="text-xs text-muted-foreground">Gastos estimados em BRL</p>
                    </div>
                    <div className="flex-1 w-full min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart margin={{ top: 20, bottom: 20, left: 0, right: 0 }}>
                                <Pie
                                    data={costDistribution}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {costDistribution.map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={['#34d399', '#3b82f6', '#ec4899', '#f59e0b', '#8b5cf6'][index % 5]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value: number | undefined) => `R$ ${(value || 0).toFixed(4)}`}
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                                    itemStyle={{ color: 'hsl(var(--foreground))' }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </BentoCard>

                {/* Request Evolution Chart - 2x1 */}
                <BentoCard size="1x2" glassmorphism className="flex flex-col md:col-span-2">
                    <div className="mb-2">
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                            <Activity className="w-4 h-4 text-blue-400" />
                            Evolução de Requisições
                        </h3>
                        <p className="text-xs text-muted-foreground">Volume de chamadas</p>
                    </div>
                    <div className="flex-1 w-full min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <XAxis
                                    dataKey="name"
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    allowDecimals={false}
                                />
                                <Tooltip
                                    cursor={{ stroke: '#3b82f6' }}
                                    contentStyle={{
                                        backgroundColor: 'hsl(var(--card))',
                                        borderColor: 'hsl(var(--border))',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="requests"
                                    name="Requisições"
                                    stroke="#3b82f6"
                                    strokeWidth={3}
                                    dot={{ fill: '#3b82f6', r: 4 }}
                                    activeDot={{ r: 6 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </BentoCard>

                {/* Usage Overview - Now at bottom, taking full width if possible or 2x2 next to activity */}
                {/* User said "Usage Overview below". Let's make it 2 cols, and Activity 2 cols? Or Usage 3 cols? */}
                {/* Let's try: Usage Overview (md:col-span-3), Activity (md:col-span-1) */}

                <BentoCard size="2x2" glassmorphism className="flex flex-col col-span-1 md:col-span-2 lg:col-span-3 row-span-2">
                    <div className="mb-4 flex items-center justify-between">
                        <div>
                            <h3 className="font-semibold text-lg">Visão Geral de Uso</h3>
                            <p className="text-sm text-muted-foreground">Consumo total de tokens ({timeRange})</p>
                        </div>
                    </div>
                    <div className="flex-1 min-h-[250px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="hsl(var(--foreground))" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="hsl(var(--foreground))" stopOpacity={0.1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted)/0.2)" />
                                <XAxis
                                    dataKey="name"
                                    stroke="hsl(var(--muted-foreground))"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    dy={10}
                                />
                                <YAxis
                                    stroke="hsl(var(--muted-foreground))"
                                    fontSize={12}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => `${value}`}
                                />
                                <Tooltip
                                    cursor={{ fill: 'hsl(var(--muted)/0.1)' }}
                                    contentStyle={{
                                        backgroundColor: 'hsl(var(--card))',
                                        borderColor: 'hsl(var(--border))',
                                        borderRadius: '12px',
                                        boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
                                    }}
                                />
                                {/* Stacked Bar for Input/Output or just Total? User said "Usage Overview" which usually implies total or breakdown. */}
                                {/* Let's show stacked for better detail since we have the split now */}
                                <Bar dataKey="input" stackId="a" fill="hsl(var(--primary))" radius={[0, 0, 4, 4]} name="Entrada" />
                                <Bar dataKey="output" stackId="a" fill="hsl(var(--accent))" radius={[4, 4, 0, 0]} name="Saída" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </BentoCard>

                {/* Recent Activity - 1x2 - Moved to side of Usage Overview or below? */}
                {/* 3 cols used by Usage. 1 col left. Perfect. */}
                <BentoCard size="1x2" className="flex flex-col relative overflow-hidden h-full md:col-span-1 lg:col-span-1 row-span-2">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none" />
                    <h3 className="font-semibold mb-4 text-lg">Atividade Recente</h3>
                    <div className="space-y-4 pr-2 overflow-y-auto custom-scrollbar flex-1 max-h-[380px]" onScroll={handleActivityScroll}>
                        {activity.length === 0 ? (
                            <div className="text-muted-foreground text-sm text-center py-4">Nenhuma atividade recente</div>
                        ) : activity.map((item, i) => (
                            <div key={`${item.id}-${i}`} className="flex items-center gap-4 p-3 rounded-xl hover:bg-primary/5 transition-all duration-300 group cursor-pointer border border-transparent hover:border-primary/10">
                                <div className={`h-2.5 w-2.5 rounded-full ${item.status === 'completed' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]'} group-hover:scale-125 transition-transform`} />
                                <div className="flex-1">
                                    <p className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-1">{item.description}</p>
                                    <p className="text-xs text-muted-foreground">{new Date(item.timestamp).toLocaleDateString('pt-BR')} {new Date(item.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</p>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs text-muted-foreground bg-white/5 px-2 py-0.5 rounded whitespace-nowrap">{item.meta}</span>
                                </div>
                            </div>
                        ))}
                        {isLoadingActivity && (
                            <div className="text-center text-xs text-muted-foreground py-2 flex justify-center">
                                <span className="animate-spin mr-2">⏳</span> Carregando...
                            </div>
                        )}
                    </div>
                </BentoCard>
            </div>
        </div>
    )
}


import { useEffect, useState } from "react"
import { BentoCard } from "@/components/bento-card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Brain, Database, Activity, BarChart3, AlertCircle } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { FinancialSavingsCard } from "@/components/dashboard/FinancialSavingsCard"

interface DomainStatsData {
    domain: string
    domain_name: string
    total_logs: number
    pending_reviews: number
    source_breakdown: { source: string; count: number }[]
    total_synonyms: number
    total_patterns: number
}

const DOMAINS = [
    { value: "transport", label: "Transport & Logistics" },
    { value: "health", label: "Health & Medicine" },
    { value: "food", label: "Food & Delivery" },
    { value: "ecommerce", label: "E-commerce & Retail" },
    { value: "automotive", label: "Automotive" },
    { value: "custom", label: "Custom Domain" },
]

export function DomainStats() {
    const [domain, setDomain] = useState("transport")
    const [loading, setLoading] = useState(false)
    const [stats, setStats] = useState<DomainStatsData | null>(null)

    useEffect(() => {
        fetchStats()
    }, [domain])

    async function fetchStats() {
        setLoading(true)
        try {
            const res = await api.get(`/ai/sentiment/stats/domain?domain=${domain}`)
            setStats(res.data)
        } catch (error) {
            console.error(error)
            toast.error("Failed to fetch domain statistics")
        } finally {
            setLoading(false)
        }
    }

    if (!stats && loading) {
        return <div className="p-8 text-center text-muted-foreground">Loading statistics...</div>
    }

    if (!stats) return null

    // Calculate Efficiency (Cache + Sticky + Rule)
    const total = stats.total_logs || 1
    const efficientSources = ['learned_cache', 'sticky_session', 'rule_match', 'rule_match_ai_validated', 'exception_pattern_match']
    const efficientCount = stats.source_breakdown
        .filter(s => efficientSources.includes(s.source))
        .reduce((acc, curr) => acc + curr.count, 0)

    const efficiencyRate = Math.round((efficientCount / total) * 100)

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-semibold text-white">Domain Performance</h3>
                <div className="w-[250px]">
                    <Select value={domain} onValueChange={setDomain}>
                        <SelectTrigger className="bg-white/5 border-white/10 text-foreground">
                            <SelectValue placeholder="Select Domain" />
                        </SelectTrigger>
                        <SelectContent className="glass-ultra border-white/10 text-foreground">
                            {DOMAINS.map(d => (
                                <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="mb-6">
                <FinancialSavingsCard domain={domain} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 1. Traffic Volume */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-500/20">
                    <div className="flex flex-col h-full justify-between">
                        <div className="p-2 bg-blue-500/20 w-fit rounded-lg">
                            <Activity className="h-6 w-6 text-blue-400" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground mb-1">Total Requests</p>
                            <h4 className="text-3xl font-bold text-white">{stats.total_logs}</h4>
                            <div className="flex items-center mt-2 text-xs text-blue-300 bg-blue-500/10 w-fit px-2 py-1 rounded">
                                <Activity className="h-3 w-3 mr-1" /> Active
                            </div>
                        </div>
                    </div>
                </BentoCard>

                {/* 2. Intelligence Asset */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-500/20">
                    <div className="flex flex-col h-full justify-between">
                        <div className="p-2 bg-purple-500/20 w-fit rounded-lg">
                            <Brain className="h-6 w-6 text-purple-400" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground mb-1">Knowledge Base</p>
                            <div className="flex gap-4 items-baseline">
                                <div>
                                    <h4 className="text-2xl font-bold text-white">{stats.total_synonyms}</h4>
                                    <p className="text-xs text-muted-foreground">Synonyms</p>
                                </div>
                                <div>
                                    <h4 className="text-2xl font-bold text-white">{stats.total_patterns}</h4>
                                    <p className="text-xs text-muted-foreground">Patterns</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </BentoCard>

                {/* 3. Efficiency Rate */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-500/20">
                    <div className="flex flex-col h-full justify-between">
                        <div className="p-2 bg-green-500/20 w-fit rounded-lg">
                            <Database className="h-6 w-6 text-green-400" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground mb-1">Efficiency (Non-AI)</p>
                            <h4 className="text-3xl font-bold text-white">{efficiencyRate}%</h4>
                            <p className="text-xs text-muted-foreground mt-1">
                                {efficientCount} requests handled without expensive AI
                            </p>
                        </div>
                    </div>
                </BentoCard>

                {/* 4. Action Items */}
                <BentoCard size="1x1" className="bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-500/20">
                    <div className="flex flex-col h-full justify-between">
                        <div className="p-2 bg-orange-500/20 w-fit rounded-lg">
                            <AlertCircle className="h-6 w-6 text-orange-400" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground mb-1">Pending Review</p>
                            <h4 className="text-3xl font-bold text-white">{stats.pending_reviews}</h4>
                            <Button variant="link" className="p-0 h-auto text-orange-400 text-xs mt-2">
                                Review Logs &rarr;
                            </Button>
                        </div>
                    </div>
                </BentoCard>

                {/* 5. Source Breakdown (Wide) */}
                <BentoCard size="2x1" className="glass-ultra">
                    <div className="flex flex-col h-full">
                        <div className="flex items-center gap-2 mb-4">
                            <BarChart3 className="h-5 w-5 text-muted-foreground" />
                            <h4 className="font-semibold text-white">Classification Source Distribution</h4>
                        </div>

                        <div className="space-y-3 mt-2 pr-4 custom-scrollbar overflow-y-auto max-h-[150px]">
                            {stats.source_breakdown.map((item, idx) => {
                                const percentage = Math.round((item.count / total) * 100)
                                return (
                                    <div key={idx} className="space-y-1">
                                        <div className="flex justify-between text-xs">
                                            <span className="text-muted-foreground uppercase tracking-wider">{item.source.replace(/_/g, ' ')}</span>
                                            <span className="text-white font-mono">{item.count} ({percentage}%)</span>
                                        </div>
                                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full ${item.source === 'learned_cache' ? 'bg-green-500' :
                                                    item.source.includes('ai') ? 'bg-purple-500' :
                                                        item.source === 'fallback' ? 'bg-orange-500' :
                                                            'bg-blue-500'
                                                    }`}
                                                style={{ width: `${percentage}%` }}
                                            />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </BentoCard>
            </div>
        </div>
    )
}

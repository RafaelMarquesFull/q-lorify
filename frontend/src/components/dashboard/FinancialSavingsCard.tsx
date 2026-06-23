
import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import api from "@/lib/api"
import { Loader2 } from "lucide-react"

interface FinancialData {
    requests_deflected: number
    tokens_saved_est: number
    money_saved_usd: number
    avg_tokens_per_req: number
}

export function FinancialSavingsCard({ domain = "transport" }: { domain?: string }) {
    const [data, setData] = useState<FinancialData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchFinancials()
    }, [domain])

    async function fetchFinancials() {
        setLoading(true)
        try {
            const res = await api.get(`/ai/sentiment/stats/financial?domain=${domain}`)
            setData(res.data)
        } catch (error) {
            console.error("Failed to fetch financial stats", error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <div className="h-40 flex items-center justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>
    if (!data) return null

    return (
        <Card className="bg-gradient-to-r from-emerald-900/20 to-teal-900/10 border-emerald-500/30">
            {/* <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-emerald-400">
                    <PiggyBank className="h-5 w-5" /> Economia Inteligente
                </CardTitle>
            </CardHeader> */}
            {/* <CardContent>
                <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-2 bg-black/20 rounded border border-white/5">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">USD Economizados</p>
                        <p className="text-2xl font-bold text-white">${data.money_saved_usd.toFixed(4)}</p>
                    </div>
                    <div className="p-2 bg-black/20 rounded border border-white/5">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Tokens Poupados</p>
                        <p className="text-xl font-bold text-emerald-300">~{(data.tokens_saved_est / 1000).toFixed(1)}k</p>
                    </div>
                    <div className="p-2 bg-black/20 rounded border border-white/5">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Requests Offloaded</p>
                        <p className="text-xl font-bold text-blue-300">{data.requests_deflected}</p>
                    </div>
                </div>
                <p className="text-xs text-emerald-500/60 mt-4 text-center">
                    *Baseado em custo médio de GPT-4o por 1k tokens.
                </p>
            </CardContent> */}
        </Card>
    )
}

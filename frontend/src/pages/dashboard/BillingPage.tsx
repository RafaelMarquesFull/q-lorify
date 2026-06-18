import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Wallet, CreditCard, RefreshCw, Zap, TrendingUp, ExternalLink, ArrowUpRight, ArrowDownLeft, Edit2, Check, X } from "lucide-react"
import api from "@/lib/api"
import { toast } from "sonner"
import { useSearchParams } from "react-router-dom"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"

interface Transaction {
    id: string
    type: string
    amount: number
    description: string
    date: string
}

interface BalanceData {
    balance: number
    autoRechargeEnabled: boolean
    rechargeThreshold: number
    rechargeAmount: number
    paymentMethodSet: boolean
    transactions: Transaction[]
}

function SettingsForm({ data, refresh }: { data: BalanceData, refresh: () => void }) {
    const [loading, setLoading] = useState(false)
    // Modes: 'view' vs 'edit'. Default to view if enabled, otherwise edit to encourage setup.
    const [isEditing, setIsEditing] = useState(!data.autoRechargeEnabled)

    // Form States
    const [enabled, setEnabled] = useState(data.autoRechargeEnabled)
    const [threshold, setThreshold] = useState(data.rechargeThreshold)
    const [amount, setAmount] = useState(data.rechargeAmount)

    // Sync state if data changes externally
    useEffect(() => {
        setEnabled(data.autoRechargeEnabled)
        setThreshold(data.rechargeThreshold)
        setAmount(data.rechargeAmount)
    }, [data])

    async function handleSave() {
        if (!data.paymentMethodSet && enabled) {
            toast.error("Para ativar a recarga automática, adicione um cartão primeiro.")
            return
        }

        setLoading(true)
        try {
            await api.post("/billing/settings", {
                enabled,
                threshold,
                amount
            })
            toast.success("Configurações atualizadas")
            refresh()
            setIsEditing(false)
        } catch (error) {
            toast.error("Falha ao atualizar configurações")
        } finally {
            setLoading(false)
        }
    }

    async function handleAddCard() {
        setLoading(true)
        try {
            const res = await api.post("/billing/checkout/setup")
            window.location.href = res.data.url
        } catch (error) {
            toast.error("Falha ao iniciar checkout")
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label className="text-base text-white flex items-center gap-2">
                        Recarga Automática
                        {!data.paymentMethodSet && (
                            <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Cartão Necessário</span>
                        )}
                    </Label>
                    <p className="text-sm text-white/50">
                        Adiciona fundos automaticamente quando o saldo está baixo.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold ${!enabled ? 'text-white' : 'text-white/30'}`}>OFF</span>
                    <Switch
                        checked={enabled}
                        onCheckedChange={(val) => {
                            if (!data.paymentMethodSet && val) {
                                toast.error("Adicione um cartão antes de ativar.")
                                return
                            }
                            setEnabled(val)
                            // Always enter edit mode so user can save the change
                            setIsEditing(true)
                        }}
                        disabled={!data.paymentMethodSet && !enabled}
                    />
                    <span className={`text-xs font-bold ${enabled ? 'text-green-400' : 'text-white/30'}`}>ON</span>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 relative">
                {/* Visual Block for Disabled State */}
                {!isEditing && (
                    <div className="absolute inset-0 z-10 bg-black/10 cursor-not-allowed" title="Clique em Editar para alterar" />
                )}

                <div className="space-y-2">
                    <Label className="text-white">Limite para Gatilho (R$)</Label>
                    <Input
                        type="number"
                        value={threshold}
                        onChange={(e) => setThreshold(parseFloat(e.target.value))}
                        disabled={!isEditing}
                        className="bg-zinc-950 border-white/10 text-white disabled:opacity-50"
                    />
                    <p className="text-xs text-white/50">Recarregar quando saldo for menor que isso.</p>
                </div>
                <div className="space-y-2">
                    <Label className="text-white">Valor da Recarga (R$)</Label>
                    <Input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(parseFloat(e.target.value))}
                        disabled={!isEditing}
                        className="bg-zinc-950 border-white/10 text-white disabled:opacity-50"
                    />
                    <p className="text-xs text-white/50">Valor a ser cobrado no cartão.</p>
                </div>
            </div>

            <div className="flex gap-3">
                {isEditing ? (
                    <>
                        <Button onClick={handleSave} disabled={loading} className="flex-1 bg-white text-black hover:bg-white/90">
                            {loading ? "Salvando..." : (<><Check className="mr-2 h-4 w-4" /> Salvar Alterações</>)}
                        </Button>
                        <Button variant="outline" onClick={() => setIsEditing(false)} disabled={loading} className="bg-transparent border-white/10 text-white hover:bg-white/10">
                            <X className="h-4 w-4" />
                        </Button>
                    </>
                ) : (
                    <Button onClick={() => setIsEditing(true)} className="w-full bg-zinc-800 text-white hover:bg-zinc-700">
                        <Edit2 className="mr-2 h-4 w-4" /> Editar Configuração
                    </Button>
                )}
            </div>

            <Separator className="bg-white/10 my-4" />

            <div className="space-y-4">
                <div className="flex items-center gap-2 text-white">
                    <CreditCard className="h-4 w-4" />
                    <h3 className="font-medium">Método de Pagamento</h3>
                </div>

                {data.paymentMethodSet ? (
                    <div className="space-y-3">
                        <div className="p-3 rounded bg-green-500/10 border border-green-500/20 text-green-400 text-sm flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            Cartão ativo configurado para auto-recarga.
                        </div>
                        <Button onClick={handleAddCard} variant="outline" size="sm" className="w-full border-white/10 text-white bg-transparent hover:bg-white/10">
                            Atualizar Cartão (Redireciona para Stripe)
                        </Button>
                    </div>
                ) : (
                    <div className="p-4 rounded border border-white/10 bg-black text-center space-y-3">
                        <p className="text-sm text-white/60">Nenhum cartão salvo para auto-recarga.</p>
                        <Button onClick={handleAddCard} disabled={loading} className="w-full">
                            Adicionar Cartão via Stripe <ExternalLink className="ml-2 h-3 w-3" />
                        </Button>
                    </div>
                )}
            </div>
        </div>
    )
}

function BalanceCard({ data }: { data: BalanceData }) {
    const [loading, setLoading] = useState(false)
    const [customAmount, setCustomAmount] = useState("")

    async function addFunds(amount: number) {
        if (amount <= 0) return
        setLoading(true)
        try {
            const res = await api.post("/billing/checkout/recharge", { amount })
            window.location.href = res.data.url
        } catch (error) {
            toast.error("Falha ao iniciar recarga.")
            setLoading(false)
        }
    }

    return (
        <Card className="glass-card border-primary/20 bg-gradient-to-br from-zinc-900/50 to-black/50 overflow-hidden relative group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none group-hover:bg-primary/20 transition-all duration-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                <CardTitle className="text-lg font-medium text-muted-foreground">Saldo Disponível</CardTitle>
                <div className="p-2 rounded-lg bg-primary/10 ring-1 ring-primary/20">
                    <Wallet className="h-5 w-5 text-primary" />
                </div>
            </CardHeader>
            <CardContent className="relative z-10">
                <div className="text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-white/70">
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(data.balance)}
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                    Créditos disponíveis para geração de IA.
                </p>

                <div className="mt-6 space-y-3">
                    <Label className="text-white/80">Recarga Rápida</Label>
                    <div className="flex gap-2">
                        <Button onClick={() => addFunds(10)} disabled={loading} variant="outline" className="flex-1 border-white/10 bg-white/5 text-white hover:bg-white/10">
                            + R$ 10
                        </Button>
                        <Button onClick={() => addFunds(30)} disabled={loading} variant="outline" className="flex-1 border-white/10 bg-white/5 text-white hover:bg-white/10">
                            + R$ 30
                        </Button>
                        <Button onClick={() => addFunds(50)} disabled={loading} variant="outline" className="flex-1 border-white/10 bg-white/5 text-white hover:bg-white/10">
                            + R$ 50
                        </Button>
                    </div>

                    <div className="flex gap-2 items-end">
                        <div className="flex-1 space-y-2">
                            <Label className="text-xs text-muted-foreground">Outro Valor (R$)</Label>
                            <Input
                                type="number"
                                placeholder="0.00"
                                value={customAmount}
                                onChange={(e) => setCustomAmount(e.target.value)}
                                className="bg-black/20 border-white/10 text-foreground focus:border-primary/50 transition-colors"
                            />
                        </div>
                        <Button
                            onClick={() => addFunds(parseFloat(customAmount))}
                            disabled={loading || !customAmount || parseFloat(customAmount) <= 0}
                            className="bg-white text-black hover:bg-white/90"
                        >
                            Recarregar
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

function HistoryCard({ transactions }: { transactions: Transaction[] }) {
    if (!transactions || transactions.length === 0) {
        return (
            <Card className="bg-zinc-950 border-white/10 text-white">
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Histórico de Uso
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-white/50">Nenhuma transação recente.</p>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="glass-subtle border-white/10 text-foreground">
            <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-primary" /> Histórico de Uso
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <div className="max-h-[315px] overflow-y-auto custom-scrollbar px-4 pb-2 space-y-2">
                    {transactions.map((tx) => (
                        <div key={tx.id} className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0 last:pb-0 hover:bg-white/5 p-2 rounded-lg transition-colors">
                            <div className="flex items-center gap-3">
                                <div className={`p-1.5 rounded-full ${tx.type === 'CREDIT' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                    {tx.type === 'CREDIT' ? <ArrowDownLeft className="h-3.5 w-3.5" /> : <ArrowUpRight className="h-3.5 w-3.5" />}
                                </div>
                                <div>
                                    <p className="text-sm font-medium">{tx.description || (tx.type === 'CREDIT' ? 'Recarga' : 'Uso')}</p>
                                    <p className="text-[10px] text-white/50">{new Date(tx.date).toLocaleDateString('pt-BR')} {new Date(tx.date).toLocaleTimeString('pt-BR')}</p>
                                </div>
                            </div>
                            <div className={`text-xs font-bold ${tx.type === 'CREDIT' ? 'text-green-400' : 'text-white'}`}>
                                {tx.type === 'CREDIT' ? '+' : '-'} {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: tx.type === 'CREDIT' ? 2 : 6, maximumFractionDigits: tx.type === 'CREDIT' ? 2 : 6 }).format(tx.amount)}
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}

export default function BillingPage() {
    const [data, setData] = useState<BalanceData | null>(null)
    const [searchParams] = useSearchParams()

    useEffect(() => {
        fetchData()

        if (searchParams.get("setup_success")) {
            toast.success("Método de pagamento salvo com sucesso!")
        }
        if (searchParams.get("recharge_success")) {
            toast.success("Recarga realizada! Seu saldo será atualizado em breve.")
        }
        if (searchParams.get("canceled")) {
            toast.info("Operação cancelada.")
        }
    }, [searchParams])

    async function fetchData() {
        try {
            const res = await api.get("/billing/balance")
            setData(res.data)
        } catch (error) {
            console.error(error)
        }
    }

    if (!data) return <div className="p-8 text-white">Carregando informações financeiras...</div>

    return (
        <AnimatedGradientBg className="p-8 space-y-8 min-h-full">
            <div>
                <h2 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">Faturamento e Créditos</h2>
                <p className="text-muted-foreground mb-4">Gerencie seu saldo e configurações de recarga automática.</p>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
                {/* Left Column: Balance & Stats */}
                <div className="space-y-6">
                    <BalanceCard data={data} key={data.balance} />
                    <HistoryCard transactions={data.transactions} />
                </div>

                {/* Right Column: Settings */}
                <div className="space-y-6">
                    <Card className="glass-card border-white/10 text-foreground">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <RefreshCw className="h-5 w-5 text-primary" /> Configurar Auto-Recarga
                            </CardTitle>
                            <CardDescription className="text-muted-foreground">
                                Garanta que seus serviços não parem configurando recargas automáticas.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <SettingsForm data={data} refresh={fetchData} />
                        </CardContent>
                    </Card>
                </div>
            </div>
        </AnimatedGradientBg>
    )
}

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { ArrowRight, Bot, Cpu, Zap, Shield, Sparkles, Globe } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"
import { BentoCard } from "@/components/bento-card"
import Logotipo from "@/assets/logotipo.png"
import HeroBg from "@/assets/hero-bg.png"
import api from "@/lib/api"
import { Badge } from "@/components/ui/badge"

interface Model {
    id: string
    name: string
    costIn: number
    costOut: number
    description?: string
}

export default function LandingPage() {
    const navigate = useNavigate()
    const [models, setModels] = useState<Model[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.get("/public/models")
            .then(res => {
                setModels(res.data)
                setLoading(false)
            })
            .catch(err => {
                console.error("Failed to load models", err)
                setLoading(false)
            })
    }, [])

    return (
        <AnimatedGradientBg variant="intense" className="min-h-screen text-foreground selection:bg-primary/20 overflow-x-hidden font-sans">
            {/* Navbar */}
            <nav className="fixed w-full z-50 glass-ultra border-b border-white/5 backdrop-blur-md">
                <div className="container mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center space-x-3 group cursor-pointer hover:opacity-80 transition-opacity" onClick={() => navigate("/")}>
                        <div className="p-2 ">
                            <img src={Logotipo} alt="Logo" className="h-12 w-full text-primary invert dark:invert-0" />
                        </div>

                    </div>
                    <div className="hidden md:flex items-center space-x-8">
                        <a href="#features" className="text-sm font-medium text-muted-foreground hover:text-white transition-colors">Recursos</a>
                        <a href="#models" className="text-sm font-medium text-muted-foreground hover:text-white transition-colors">Modelos</a>
                        <a href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-white transition-colors">Preços</a>
                    </div>
                    <div className="flex items-center space-x-4">
                        <Button variant="ghost" onClick={() => navigate("/login")} className="hover:bg-white/5 text-muted-foreground hover:text-white">
                            Entrar
                        </Button>
                        <Button onClick={() => navigate("/register")} variant="glow" className="font-semibold shadow-lg shadow-primary/20">
                            Começar Agora
                        </Button>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-32 pb-40 overflow-hidden">
                {/* Background Image showing Technology impact */}
                <div className="absolute inset-0 z-0">
                    <img
                        src={HeroBg}
                        alt="Background AI Network"
                        className="w-full h-full object-cover opacity-40 mix-blend-screen scale-105 animate-pulse-slow"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
                </div>

                <div className="container mx-auto px-6 relative z-10 text-center max-w-5xl">
                    <div className="inline-flex items-center px-4 py-1.5 rounded-full border border-primary/20 bg-primary/10 mb-8 animate-fade-in backdrop-blur-sm">
                        <Sparkles className="h-3 w-3 text-primary mr-2" />
                        <span className="text-xs font-semibold text-primary tracking-wide uppercase">Infraestrutura de IA de Próxima Geração</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white via-white/90 to-white/50 mb-8 tracking-tighter leading-[1.1] animate-slide-up drop-shadow-2xl">
                        Construa e Escale <br />
                        <span className="bg-gradient-to-r from-primary via-purple-400 to-accent bg-clip-text text-transparent">Agentes Inteligentes</span>
                    </h1>

                    <p className="text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed animate-slide-up delay-100 drop-shadow-md">
                        Orquestre fluxos de trabalho de IA poderosos com latência imbatível.
                        Gerencie modelos, monitore o uso e monetize seus agentes em uma plataforma unificada e robusta.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up delay-200">
                        <Button size="lg" variant="glow" onClick={() => navigate("/register")} className="h-16 px-10 text-lg rounded-2xl w-full sm:w-auto shadow-xl shadow-primary/25 hover:scale-105 transition-transform">
                            Criar Conta Grátis <ArrowRight className="ml-2 h-5 w-5" />
                        </Button>
                        <Button size="lg" variant="glass" className="h-16 px-10 text-lg rounded-2xl w-full sm:w-auto hover:bg-white/10 hover:border-white/20 transition-all border border-white/10">
                            Ver Documentação
                        </Button>
                    </div>

                    {/* Stats */}
                    <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-8 border-t border-white/5 pt-12 animate-fade-in delay-300">
                        <div>
                            <div className="text-3xl font-bold text-white mb-1">99.9%</div>
                            <div className="text-sm text-muted-foreground">Uptime Garantido</div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold text-white mb-1">&lt;50ms</div>
                            <div className="text-sm text-muted-foreground">Latência Média</div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold text-white mb-1">10k+</div>
                            <div className="text-sm text-muted-foreground">Req/seg Suportados</div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold text-white mb-1">24/7</div>
                            <div className="text-sm text-muted-foreground">Suporte Especializado</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-32 relative bg-black/20">
                <div className="container mx-auto px-6">
                    <div className="text-center mb-20">
                        <h2 className="text-3xl md:text-5xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
                            Potência Máxima para seus Agentes
                        </h2>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            Nossa plataforma oferece tudo o que você precisa para criar, implantar e escalar aplicações de IA de nível empresarial.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <BentoCard size="1x1" className="group" glassmorphism>
                            <div className="p-8 h-full flex flex-col relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-32 bg-blue-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
                                <div className="mb-8 p-4 rounded-2xl bg-blue-500/10 w-fit ring-1 ring-blue-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <Cpu className="h-8 w-8 text-blue-400" />
                                </div>
                                <h3 className="text-2xl font-bold mb-4 text-white">Multi-Modelos</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Acesse uma variedade de LLMs de ponta através de uma única API unificada. Troque de modelos sem mudar seu código.
                                </p>
                            </div>
                        </BentoCard>

                        <BentoCard size="1x1" className="group" glassmorphism>
                            <div className="p-8 h-full flex flex-col relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-32 bg-amber-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
                                <div className="mb-8 p-4 rounded-2xl bg-amber-500/10 w-fit ring-1 ring-amber-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <Zap className="h-8 w-8 text-amber-400" />
                                </div>
                                <h3 className="text-2xl font-bold mb-4 text-white">Alta Performance</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Infraestrutura otimizada para inferência rápida. Reduza o tempo de resposta dos seus bots e melhore a UX.
                                </p>
                            </div>
                        </BentoCard>

                        <BentoCard size="1x1" className="group" glassmorphism>
                            <div className="p-8 h-full flex flex-col relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-32 bg-green-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
                                <div className="mb-8 p-4 rounded-2xl bg-green-500/10 w-fit ring-1 ring-green-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <Shield className="h-8 w-8 text-green-400" />
                                </div>
                                <h3 className="text-2xl font-bold mb-4 text-white">Segurança Enterprise</h3>
                                <p className="text-muted-foreground leading-relaxed">
                                    Controle de acesso granular, criptografia de ponta a ponta e conformidade com padrões de segurança.
                                </p>
                            </div>
                        </BentoCard>
                    </div>
                </div>
            </section>

            {/* Dynamic Models Pricing Section */}
            <section id="models" className="py-32 relative">
                <div className="container mx-auto px-6">
                    <div className="text-center mb-20 animate-on-scroll">
                        <Badge variant="outline" className="mb-4 border-primary/30 text-primary">Preços Transparentes</Badge>
                        <h2 className="text-3xl md:text-5xl font-bold mb-6 text-white">
                            Modelos Disponíveis
                        </h2>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            Escolha o modelo ideal para sua aplicação. Cobrança por token, sem taxas ocultas.
                        </p>
                    </div>

                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="h-64 rounded-xl bg-white/5 border border-white/10" />
                            ))}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {models.map((model) => (
                                <BentoCard key={model.id} size="1x1" className="bg-gradient-to-br from-white/5 to-transparent border-white/10 hover:border-primary/30 transition-all duration-300">
                                    <div className="p-6">
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="p-3 bg-white/5 rounded-lg">
                                                <Bot className="h-6 w-6 text-primary" />
                                            </div>
                                            <Badge variant="secondary" className="bg-white/10 text-xs">
                                                Produção
                                            </Badge>
                                        </div>

                                        <h3 className="text-xl font-bold text-white mb-2">{model.name}</h3>
                                        <p className="text-sm text-muted-foreground mb-6 h-10 line-clamp-2">
                                            {model.description || "Modelo de alta performance para tarefas gerais e raciocínio complexo."}
                                        </p>

                                        <div className="space-y-3 pt-6 border-t border-white/5">
                                            <div className="flex justify-between items-center text-sm">
                                                <span className="text-muted-foreground">Entrada (1M tokens)</span>
                                                <span className="font-mono text-white font-medium">R$ {(model.costIn * 1000000).toFixed(2).replace('.', ',')}</span>
                                            </div>
                                            <div className="flex justify-between items-center text-sm">
                                                <span className="text-muted-foreground">Saída (1M tokens)</span>
                                                <span className="font-mono text-white font-medium">R$ {(model.costOut * 1000000).toFixed(2).replace('.', ',')}</span>
                                            </div>
                                        </div>

                                        <Button className="w-full mt-6 bg-white/5 hover:bg-white/10 border border-white/10" onClick={() => navigate("/register")}>
                                            Começar a usar
                                        </Button>
                                    </div>
                                </BentoCard>
                            ))}
                            {/* CTA Card if few models */}
                            {models.length < 3 && (
                                <BentoCard size="1x1" className="bg-primary/5 border-primary/20 flex items-center justify-center text-center p-6 border-dashed">
                                    <div>
                                        <Globe className="h-10 w-10 text-primary mx-auto mb-4 opacity-50" />
                                        <h3 className="font-bold text-lg text-white mb-2">Mais modelos em breve</h3>
                                        <p className="text-sm text-muted-foreground">Adicionamos novos modelos semanalmente.</p>
                                    </div>
                                </BentoCard>
                            )}
                        </div>
                    )}
                </div>
            </section>

            {/* Final CTA */}
            <section className="py-24 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-accent/10 pointer-events-none" />
                <div className="container mx-auto px-6 relative z-10">
                    <div className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
                        <h2 className="text-4xl font-bold mb-6 text-white">Pronto para transformar sua operação?</h2>
                        <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
                            Junte-se a centenas de desenvolvedores que já estão construindo o futuro com a nossa infraestrutura.
                        </p>
                        <Button size="lg" variant="glow" onClick={() => navigate("/register")} className="h-14 px-12 text-lg rounded-full shadow-2xl shadow-primary/30">
                            Criar Conta Gratuita
                        </Button>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-white/5 py-12 relative bg-black/40 backdrop-blur-md">
                <div className="container mx-auto px-6">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-8">
                        <div className="flex items-center space-x-2 opacity-70 hover:opacity-100 transition-opacity">
                            <Bot className="h-5 w-5 text-primary" />
                            <span className="font-semibold tracking-tight text-white">Qlorify</span>
                        </div>
                        <div className="flex gap-8 text-sm text-muted-foreground">
                            <a href="#" className="hover:text-primary transition-colors">Privacidade</a>
                            <a href="#" className="hover:text-primary transition-colors">Termos</a>
                            <a href="#" className="hover:text-primary transition-colors">Status</a>
                            <a href="#" className="hover:text-primary transition-colors">Contato</a>
                        </div>
                        <div className="text-sm text-muted-foreground/60">
                            &copy; 2024 Qlorify. Todos os direitos reservados.
                        </div>
                    </div>
                </div>
            </footer>
        </AnimatedGradientBg>
    )
}

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useNavigate, Link } from "react-router-dom"
import api from "@/lib/api"
import { toast } from "sonner"
import { Loader2, User, Mail, Lock, Sparkles, Rocket, Target, Globe } from "lucide-react"
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google"
import { useAuthStore } from "@/store/auth"
import heroBg from "@/assets/hero-bg.png"
import Logotipo from "@/assets/logotipo.png"

const formSchema = z.object({
    name: z.string().min(2, "O nome deve ter pelo menos 2 caracteres"),
    email: z.string().email("Email inválido"),
    password: z.string().min(6, "A senha deve ter pelo menos 6 caracteres"),
})

export default function RegisterPage() {
    const navigate = useNavigate()
    const login = useAuthStore((state) => state.login)
    const [loading, setLoading] = useState(false)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            email: "",
            password: "",
        },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setLoading(true)
        try {
            const registerRes = await api.post("/auth/register", values)
            if (registerRes.status === 201) {
                toast.success("Conta criada com sucesso! Faça login.")
                navigate("/login")
            }
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha no cadastro")
        } finally {
            setLoading(false)
        }
    }

    const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
        if (!credentialResponse.credential) return
        try {
            setLoading(true)
            const res = await api.post("/auth/google", { credential: credentialResponse.credential })
            const { token, user } = res.data
            login(token, user)
            toast.success("Login com Google realizado!")
            if (user.role === "ADMIN") {
                navigate("/admin")
            } else {
                navigate("/dashboard")
            }
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha no login Google")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen w-full flex relative overflow-hidden">
            {/* Background Image (Global) */}
            <div
                className="absolute inset-0 z-0 bg-cover bg-center"
                style={{ backgroundImage: `url(${heroBg})` }}
            />
            <div className="absolute inset-0 z-0 bg-black/60 backdrop-blur-[2px]" />

            {/* Left Side - Visuals (Hidden on Mobile) */}
            <div className="hidden lg:flex w-1/2 relative z-10 items-center justify-center border-r border-white/10 bg-black/40 backdrop-blur-sm">
                <div className="max-w-lg p-10 space-y-8">
                    <div className="flex items-center space-x-3 group cursor-pointer hover:opacity-80 transition-opacity" onClick={() => navigate("/")}>
                        <div className="p-2 ">
                            <img src={Logotipo} alt="Logo" className="h-10 w-full text-primary invert dark:invert-0" />
                        </div>
                    </div>

                    <h1 className="text-4xl font-bold text-white leading-tight">
                        Comece a construir o <span className="text-primary">Futuro da IA</span> hoje
                    </h1>

                    <p className="text-gray-300 text-lg">
                        Junte-se a milhares de desenvolvedores criando aplicações inteligentes com nossa infraestrutura escalável.
                    </p>

                    <div className="grid grid-cols-1 gap-4 pt-4">
                        {[
                            { icon: Rocket, title: "Implantação Rápida", desc: "Leve suas ideias do conceito à produção em minutos" },
                            { icon: Target, title: "Precisão e Controle", desc: "Ajuste fino de modelos e parâmetros para suas necessidades" },
                            { icon: Globe, title: "Escala Global", desc: "Infraestrutura distribuída para atender usuários em qualquer lugar" }
                        ].map((item, i) => (
                            <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-white/5 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-colors">
                                <div className="p-2 rounded-lg bg-primary/10 text-primary mt-1">
                                    <item.icon className="h-5 w-5" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-white">{item.title}</h3>
                                    <p className="text-sm text-gray-400">{item.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right Side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center relative z-10 p-8 lg:p-16 bg-black/80 lg:bg-black/60 backdrop-blur-md">
                <div className="w-full max-w-md space-y-8 animate-in fade-in slide-in-from-right-10 duration-500">
                    <div className="text-center lg:text-left space-y-2">
                        {/* Mobile Logo (Visible only on lg:hidden) */}
                        <div className="lg:hidden flex justify-center mb-6">
                            <div className="p-2 rounded-xl bg-gradient-to-tr from-primary/20 to-accent/20 border border-white/10 inline-block">
                                <img src={Logotipo} alt="Logo" className="h-10 w-10 text-primary invert dark:invert-0" />
                            </div>
                        </div>

                        <h2 className="text-3xl font-bold tracking-tight text-white">Crie sua conta</h2>
                        <p className="text-gray-400">Preencha os dados abaixo para começar</p>
                    </div>

                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                            <FormField
                                control={form.control}
                                name="name"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className="text-gray-300">Nome Completo</FormLabel>
                                        <FormControl>
                                            <div className="relative">
                                                <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                <Input
                                                    placeholder="Seu nome"
                                                    {...field}
                                                    className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:bg-white/10 transition-colors h-11"
                                                />
                                            </div>
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className="text-gray-300">Email</FormLabel>
                                        <FormControl>
                                            <div className="relative">
                                                <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                <Input
                                                    placeholder="seu@email.com"
                                                    {...field}
                                                    className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:bg-white/10 transition-colors h-11"
                                                />
                                            </div>
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="password"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel className="text-gray-300">Senha</FormLabel>
                                        <FormControl>
                                            <div className="relative">
                                                <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                <Input
                                                    type="password"
                                                    placeholder="••••••••"
                                                    {...field}
                                                    className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:bg-white/10 transition-colors h-11"
                                                />
                                            </div>
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <Button type="submit" variant="glow" className="w-full h-11 text-base font-semibold shadow-lg shadow-primary/20" disabled={loading}>
                                {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
                                Criar Conta Gratuita <Sparkles className="ml-2 h-4 w-4" />
                            </Button>
                        </form>
                    </Form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t border-white/10" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-black/50 px-2 text-gray-400 backdrop-blur-sm">Ou continue com</span>
                        </div>
                    </div>

                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={() => toast.error('Falha no Registro Google')}
                        theme="filled_black"
                        width="100%"
                        text="signup_with"
                    />

                    <p className="text-center text-sm text-gray-400">
                        Já tem uma conta?{" "}
                        <Link to="/login" className="text-primary hover:text-primary/80 font-semibold underline underline-offset-4">
                            Fazer Login
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useNavigate, useSearchParams, Link } from "react-router-dom"
import api from "@/lib/api"
import { toast } from "sonner"
import { Loader2, Lock, ArrowLeft } from "lucide-react"
import heroBg from "@/assets/hero-bg.png"
import Logotipo from "@/assets/logotipo.png"

const formSchema = z.object({
    password: z.string().min(6, "A senha deve ter pelo menos 6 caracteres"),
    confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
    message: "As senhas não coincidem",
    path: ["confirmPassword"],
})

export default function ResetPasswordPage() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const token = searchParams.get("token")
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)

    useEffect(() => {
        if (!token) {
            toast.error("Token de recuperação inválido ou não fornecido.")
        }
    }, [token])

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: { password: "", confirmPassword: "" },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        if (!token) return
        setLoading(true)
        try {
            await api.post("/auth/reset-password", { token, password: values.password })
            setSuccess(true)
            toast.success("Senha redefinida com sucesso!")
            setTimeout(() => navigate("/login"), 3000)
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao redefinir a senha. O link pode ter expirado.")
        } finally {
            setLoading(false)
        }
    }

    if (!token) {
        return (
            <div className="min-h-screen w-full flex items-center justify-center bg-black">
                <div className="text-center space-y-4">
                    <p className="text-red-400">Token inválido ou ausente.</p>
                    <Link to="/login" className="text-primary hover:underline">Voltar para o Login</Link>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen w-full flex relative overflow-hidden">
            <div className="absolute inset-0 z-0 bg-cover bg-center" style={{ backgroundImage: `url(${heroBg})` }} />
            <div className="absolute inset-0 z-0 bg-black/60 backdrop-blur-[2px]" />

            <div className="w-full flex items-center justify-center relative z-10 p-8 lg:p-16">
                <div className="w-full max-w-md space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 bg-black/80 p-8 rounded-2xl border border-white/10 backdrop-blur-md">
                    
                    <div className="text-center space-y-2">
                        <div className="flex justify-center mb-6">
                            <div className="p-2 rounded-xl bg-gradient-to-tr from-primary/20 to-accent/20 border border-white/10 inline-block cursor-pointer" onClick={() => navigate("/")}>
                                <img src={Logotipo} alt="Logo" className="h-10 w-10 text-primary invert dark:invert-0" />
                            </div>
                        </div>

                        <h2 className="text-3xl font-bold tracking-tight text-white">Criar Nova Senha</h2>
                        <p className="text-gray-400">Digite sua nova senha abaixo.</p>
                    </div>

                    {!success ? (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-gray-300">Nova Senha</FormLabel>
                                            <FormControl>
                                                <div className="relative">
                                                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                    <Input
                                                        type="password"
                                                        placeholder="••••••••"
                                                        {...field}
                                                        className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:bg-white/10 h-11"
                                                    />
                                                </div>
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="confirmPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-gray-300">Confirme a Nova Senha</FormLabel>
                                            <FormControl>
                                                <div className="relative">
                                                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                    <Input
                                                        type="password"
                                                        placeholder="••••••••"
                                                        {...field}
                                                        className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:bg-white/10 h-11"
                                                    />
                                                </div>
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <Button type="submit" variant="glow" className="w-full h-11 text-base font-semibold shadow-lg shadow-primary/20" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
                                    Salvar Nova Senha
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center space-y-4 p-4 border border-emerald-500/30 bg-emerald-500/10 rounded-xl">
                            <p className="text-emerald-400 font-medium">Senha atualizada!</p>
                            <p className="text-sm text-gray-400">Você será redirecionado para o login em instantes...</p>
                        </div>
                    )}

                    <div className="text-center mt-6">
                        <Link to="/login" className="text-sm text-gray-400 hover:text-white flex items-center justify-center gap-2 transition-colors">
                            <ArrowLeft className="w-4 h-4" /> Voltar para o Login
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}

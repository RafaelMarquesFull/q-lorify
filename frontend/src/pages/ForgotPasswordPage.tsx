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
import { Loader2, ArrowLeft, Mail } from "lucide-react"
import heroBg from "@/assets/hero-bg.png"
import Logotipo from "@/assets/logotipo.png"

const formSchema = z.object({
    email: z.string().email("Email inválido"),
})

export default function ForgotPasswordPage() {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: { email: "" },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setLoading(true)
        try {
            await api.post("/auth/request-password-reset", values)
            setSuccess(true)
            toast.success("Se o e-mail existir, você receberá um link de recuperação.")
        } catch (error: any) {
            toast.error(error.response?.data?.error || "Falha ao solicitar redefinição.")
        } finally {
            setLoading(false)
        }
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

                        <h2 className="text-3xl font-bold tracking-tight text-white">Esqueci minha senha</h2>
                        <p className="text-gray-400">Enviaremos um link para redefinir sua senha.</p>
                    </div>

                    {!success ? (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel className="text-gray-300">Seu E-mail</FormLabel>
                                            <FormControl>
                                                <div className="relative">
                                                    <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                                    <Input
                                                        placeholder="seu@email.com"
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
                                    Enviar Link
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center space-y-4 p-4 border border-emerald-500/30 bg-emerald-500/10 rounded-xl">
                            <p className="text-emerald-400 font-medium">Link enviado!</p>
                            <p className="text-sm text-gray-400">Verifique sua caixa de entrada e siga as instruções para redefinir sua senha.</p>
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

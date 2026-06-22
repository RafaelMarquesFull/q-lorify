import { useEffect, useState, useRef } from "react"
import { useNavigate, useSearchParams, Link } from "react-router-dom"
import api from "@/lib/api"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"

export default function VerifyEmailPage() {
    const [searchParams] = useSearchParams()
    const token = searchParams.get("token")
    const navigate = useNavigate()
    
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
    const [errorMessage, setErrorMessage] = useState("")
    const hasFetched = useRef(false)

    useEffect(() => {
        if (!token) {
            setStatus("error")
            setErrorMessage("Nenhum token fornecido na URL.")
            return
        }

        if (hasFetched.current) return
        hasFetched.current = true

        const verify = async () => {
            try {
                await api.get(`/auth/verify-email?token=${token}`)
                setStatus("success")
                // Redireciona para o login informando sucesso apos 2 segundos
                setTimeout(() => {
                    navigate("/login?verified=true")
                }, 2000)
            } catch (error: any) {
                setStatus("error")
                setErrorMessage(error.response?.data?.error || "Falha ao verificar e-mail. O link pode ser inválido ou já ter sido usado.")
            }
        }

        verify()
    }, [token, navigate])

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-black/90 p-4">
            <div className="max-w-md w-full bg-[#18181b] border border-white/10 rounded-2xl p-8 text-center space-y-6 animate-in fade-in zoom-in duration-300">
                
                {status === "loading" && (
                    <div className="flex flex-col items-center space-y-4">
                        <div className="p-4 bg-primary/10 rounded-full">
                            <Loader2 className="w-8 h-8 text-primary animate-spin" />
                        </div>
                        <h2 className="text-xl font-semibold text-white">Verificando seu e-mail...</h2>
                        <p className="text-gray-400">Por favor, aguarde um momento.</p>
                    </div>
                )}

                {status === "success" && (
                    <div className="flex flex-col items-center space-y-4">
                        <div className="p-4 bg-emerald-500/10 rounded-full">
                            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                        </div>
                        <h2 className="text-xl font-semibold text-white">E-mail Validado!</h2>
                        <p className="text-emerald-400">Sua conta foi ativada com sucesso.</p>
                        <p className="text-sm text-gray-500">Redirecionando para o login...</p>
                    </div>
                )}

                {status === "error" && (
                    <div className="flex flex-col items-center space-y-4">
                        <div className="p-4 bg-red-500/10 rounded-full">
                            <XCircle className="w-8 h-8 text-red-500" />
                        </div>
                        <h2 className="text-xl font-semibold text-white">Erro na Validação</h2>
                        <p className="text-red-400">{errorMessage}</p>
                        <Link to="/login" className="inline-block mt-4 px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors font-medium">
                            Ir para o Login
                        </Link>
                    </div>
                )}

            </div>
        </div>
    )
}

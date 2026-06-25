import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AnimatedGradientBg } from "@/components/animated-gradient-bg"
import { ArrowLeft, Terminal, Key, Box, Cpu } from "lucide-react"
import Logotipo from "@/assets/logotipo.png"

export default function DocsPage() {
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState<'orchestrator' | 'sentiment'>('orchestrator')

    return (
        <AnimatedGradientBg variant="subtle" className="min-h-screen text-foreground overflow-x-hidden font-sans">
            {/* Navbar */}
            <nav className="fixed w-full z-50 glass-ultra border-b border-white/5 backdrop-blur-md">
                <div className="container mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center space-x-3 group cursor-pointer hover:opacity-80 transition-opacity" onClick={() => navigate("/")}>
                        <div className="p-2">
                            <img src={Logotipo} alt="Logo" className="h-12 w-full text-primary invert dark:invert-0" />
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        <Button variant="ghost" onClick={() => navigate("/")} className="hover:bg-white/5 text-muted-foreground hover:text-white">
                            <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
                        </Button>
                        <Button onClick={() => navigate("/register")} variant="glow" className="font-semibold shadow-lg shadow-primary/20">
                            Começar Agora
                        </Button>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto px-6 pt-32 pb-24 flex flex-col md:flex-row gap-12">
                
                {/* Sidebar Navigation */}
                <aside className="w-full md:w-64 shrink-0">
                    <div className="sticky top-32 space-y-2">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-3">Endpoints</h3>
                        
                        <button 
                            onClick={() => setActiveTab('orchestrator')}
                            className={`w-full flex items-center px-4 py-3 rounded-lg transition-colors text-left ${activeTab === 'orchestrator' ? 'bg-primary/20 text-primary border border-primary/30' : 'hover:bg-white/5 text-muted-foreground hover:text-white border border-transparent'}`}
                        >
                            <Cpu className="w-5 h-5 mr-3" />
                            <span className="font-medium">Orquestrador</span>
                        </button>

                        <button 
                            onClick={() => setActiveTab('sentiment')}
                            className={`w-full flex items-center px-4 py-3 rounded-lg transition-colors text-left ${activeTab === 'sentiment' ? 'bg-primary/20 text-primary border border-primary/30' : 'hover:bg-white/5 text-muted-foreground hover:text-white border border-transparent'}`}
                        >
                            <Box className="w-5 h-5 mr-3" />
                            <span className="font-medium">Análise de Sentimento</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="flex-1 max-w-4xl">
                    <div className="mb-10">
                        <Badge variant="outline" className="mb-4 border-primary/30 text-primary">Documentação Oficial</Badge>
                        <h1 className="text-4xl font-bold text-white mb-4">
                            API de Modelos
                        </h1>
                        <p className="text-lg text-muted-foreground">
                            Utilize nossa API unificada para acessar os modelos de orquestração e de análise de sentimento. Todas as requisições exigem autenticação via Bearer Token.
                        </p>
                    </div>

                    <div className="mb-8 p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
                        <h3 className="text-xl font-semibold text-white flex items-center mb-4">
                            <Key className="w-5 h-5 mr-2 text-primary" /> Autenticação
                        </h3>
                        <p className="text-muted-foreground mb-4">
                            Para autenticar suas requisições, passe sua API Key no cabeçalho <code className="text-primary bg-primary/10 px-1.5 py-0.5 rounded">Authorization</code>:
                        </p>
                        <div className="bg-black/50 p-4 rounded-lg border border-white/10 overflow-x-auto">
                            <pre className="text-sm text-gray-300">
                                <code>Authorization: Bearer <span className="text-green-400">sk-sua-api-key-aqui</span></code>
                            </pre>
                        </div>
                    </div>

                    {activeTab === 'orchestrator' && (
                        <div className="space-y-8 animate-fade-in">
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <Badge className="bg-green-500/20 text-green-400 hover:bg-green-500/30 border-green-500/50">POST</Badge>
                                    <h2 className="text-2xl font-bold text-white">/api/ai/orchestrate</h2>
                                </div>
                                <p className="text-muted-foreground">
                                    Endpoint principal para processamento de linguagem natural e extração estruturada de dados.
                                </p>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Parâmetros de Requisição (Body)</h3>
                                <div className="bg-black/50 rounded-xl border border-white/10 overflow-hidden">
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-white/5 border-b border-white/10">
                                            <tr>
                                                <th className="px-6 py-3 font-medium text-white">Parâmetro</th>
                                                <th className="px-6 py-3 font-medium text-white">Tipo</th>
                                                <th className="px-6 py-3 font-medium text-white">Descrição</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/10 text-muted-foreground">
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">content</td>
                                                <td className="px-6 py-4">String</td>
                                                <td className="px-6 py-4">Obrigatório. O texto de entrada do usuário.</td>
                                            </tr>
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">schema</td>
                                                <td className="px-6 py-4">Objeto JSON</td>
                                                <td className="px-6 py-4">Opcional. Um objeto JSON definindo a estrutura esperada para extração de dados.</td>
                                            </tr>
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">model_id</td>
                                                <td className="px-6 py-4">String</td>
                                                <td className="px-6 py-4">Opcional. O ID do modelo específico que você quer usar.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white flex items-center">
                                    <Terminal className="w-5 h-5 mr-2" /> Exemplo de Requisição
                                </h3>
                                <Tabs defaultValue="curl" className="w-full">
                                    <TabsList className="bg-white/5 border border-white/10 text-muted-foreground w-full justify-start h-auto flex-wrap">
                                        <TabsTrigger value="curl" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">cURL</TabsTrigger>
                                        <TabsTrigger value="javascript" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">JavaScript (Fetch)</TabsTrigger>
                                        <TabsTrigger value="python" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">Python</TabsTrigger>
                                        <TabsTrigger value="php" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">PHP</TabsTrigger>
                                        <TabsTrigger value="ruby" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">Ruby</TabsTrigger>
                                    </TabsList>
                                    <TabsContent value="curl" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`curl -X POST https://api.qlorify.com/api/ai/orchestrate \\
  -H "Authorization: Bearer sk-..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "Olá, meu nome é Carlos e meu email é carlos@teste.com",
    "schema": {
      "nome": "string",
      "email": "string"
    }
  }'`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="javascript" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`const response = await fetch('https://api.qlorify.com/api/ai/orchestrate', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer sk-...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    content: "Olá, meu nome é Carlos e meu email é carlos@teste.com",
    schema: {
      nome: "string",
      email: "string"
    }
  })
});
const data = await response.json();
console.log(data);`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="python" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`import requests

url = "https://api.qlorify.com/api/ai/orchestrate"
headers = {
    "Authorization": "Bearer sk-...",
    "Content-Type": "application/json"
}
payload = {
    "content": "Olá, meu nome é Carlos e meu email é carlos@teste.com",
    "schema": {
        "nome": "string",
        "email": "string"
    }
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="php" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`<?php
$ch = curl_init('https://api.qlorify.com/api/ai/orchestrate');
$payload = json_encode([
    'content' => 'Olá, meu nome é Carlos e meu email é carlos@teste.com',
    'schema' => ['nome' => 'string', 'email' => 'string']
]);

curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Authorization: Bearer sk-...',
    'Content-Type: application/json'
]);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);

$response = curl_exec($ch);
curl_close($ch);
echo $response;
?>`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="ruby" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`require 'uri'
require 'net/http'
require 'json'

uri = URI('https://api.qlorify.com/api/ai/orchestrate')
http = Net::HTTP.new(uri.host, uri.port)
http.use_ssl = true

request = Net::HTTP::Post.new(uri.path, {
  'Authorization' => 'Bearer sk-...',
  'Content-Type' => 'application/json'
})

request.body = {
  content: "Olá, meu nome é Carlos e meu email é carlos@teste.com",
  schema: { nome: "string", email: "string" }
}.to_json

response = http.request(request)
puts response.body`}</code></pre>
                                        </div>
                                    </TabsContent>
                                </Tabs>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Exemplo de Resposta</h3>
                                <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                    <pre className="text-sm text-green-400"><code>{`{
  "nome": "Carlos",
  "email": "carlos@teste.com",
  "total_cost": 0.00015,
  "duration_ms": 350
}`}</code></pre>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'sentiment' && (
                        <div className="space-y-8 animate-fade-in">
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <Badge className="bg-green-500/20 text-green-400 hover:bg-green-500/30 border-green-500/50">POST</Badge>
                                    <h2 className="text-2xl font-bold text-white">/api/ai/sentiment/analyze</h2>
                                </div>
                                <p className="text-muted-foreground">
                                    Classifica intenções e sentimentos de mensagens com suporte avançado a domínios de negócio e categorias customizadas.
                                </p>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Parâmetros de Requisição (Body)</h3>
                                <div className="bg-black/50 rounded-xl border border-white/10 overflow-hidden">
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-white/5 border-b border-white/10">
                                            <tr>
                                                <th className="px-6 py-3 font-medium text-white">Parâmetro</th>
                                                <th className="px-6 py-3 font-medium text-white">Tipo</th>
                                                <th className="px-6 py-3 font-medium text-white">Descrição</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/10 text-muted-foreground">
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">intent</td>
                                                <td className="px-6 py-4">String</td>
                                                <td className="px-6 py-4">Obrigatório. A mensagem ou intenção do usuário a ser analisada.</td>
                                            </tr>
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">domain</td>
                                                <td className="px-6 py-4">String</td>
                                                <td className="px-6 py-4">Opcional. O domínio de atuação (ex: <code className="text-primary">transport</code>).</td>
                                            </tr>
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">categories</td>
                                                <td className="px-6 py-4">Array&lt;String&gt;</td>
                                                <td className="px-6 py-4">Opcional. Lista personalizada de categorias para a classificação.</td>
                                            </tr>
                                            <tr>
                                                <td className="px-6 py-4 font-mono text-primary">status</td>
                                                <td className="px-6 py-4">Objeto JSON</td>
                                                <td className="px-6 py-4">Opcional. Estado atual do fluxo/sessão do usuário.</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white flex items-center">
                                    <Terminal className="w-5 h-5 mr-2" /> Exemplo de Requisição
                                </h3>
                                <Tabs defaultValue="curl" className="w-full">
                                    <TabsList className="bg-white/5 border border-white/10 text-muted-foreground w-full justify-start h-auto flex-wrap">
                                        <TabsTrigger value="curl" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">cURL</TabsTrigger>
                                        <TabsTrigger value="javascript" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">JavaScript (Fetch)</TabsTrigger>
                                        <TabsTrigger value="python" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">Python</TabsTrigger>
                                        <TabsTrigger value="php" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">PHP</TabsTrigger>
                                        <TabsTrigger value="ruby" className="data-[state=active]:bg-white/10 data-[state=active]:text-white">Ruby</TabsTrigger>
                                    </TabsList>
                                    <TabsContent value="curl" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`curl -X POST https://api.qlorify.com/api/ai/sentiment/analyze \\
  -H "Authorization: Bearer sk-..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "domain": "transport",
    "intent": "eu quero cancelar a minha entrega por favor",
    "categories": ["cotacao", "rastreio", "finalizar"]
  }'`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="javascript" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`const response = await fetch('https://api.qlorify.com/api/ai/sentiment/analyze', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer sk-...',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    domain: "transport",
    intent: "eu quero cancelar a minha entrega por favor",
    categories: ["cotacao", "rastreio", "finalizar"]
  })
});
const data = await response.json();
console.log(data);`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="python" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`import requests

url = "https://api.qlorify.com/api/ai/sentiment/analyze"
headers = {
    "Authorization": "Bearer sk-...",
    "Content-Type": "application/json"
}
payload = {
    "domain": "transport",
    "intent": "eu quero cancelar a minha entrega por favor",
    "categories": ["cotacao", "rastreio", "finalizar"]
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="php" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`<?php
$ch = curl_init('https://api.qlorify.com/api/ai/sentiment/analyze');
$payload = json_encode([
    'domain' => 'transport',
    'intent' => 'eu quero cancelar a minha entrega por favor',
    'categories' => ['cotacao', 'rastreio', 'finalizar']
]);

curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Authorization: Bearer sk-...',
    'Content-Type: application/json'
]);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);

$response = curl_exec($ch);
curl_close($ch);
echo $response;
?>`}</code></pre>
                                        </div>
                                    </TabsContent>
                                    <TabsContent value="ruby" className="mt-2">
                                        <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                            <pre className="text-sm text-gray-300"><code>{`require 'uri'
require 'net/http'
require 'json'

uri = URI('https://api.qlorify.com/api/ai/sentiment/analyze')
http = Net::HTTP.new(uri.host, uri.port)
http.use_ssl = true

request = Net::HTTP::Post.new(uri.path, {
  'Authorization' => 'Bearer sk-...',
  'Content-Type' => 'application/json'
})

request.body = {
  domain: "transport",
  intent: "eu quero cancelar a minha entrega por favor",
  categories: ["cotacao", "rastreio", "finalizar"]
}.to_json

response = http.request(request)
puts response.body`}</code></pre>
                                        </div>
                                    </TabsContent>
                                </Tabs>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-semibold text-white">Exemplo de Resposta</h3>
                                <div className="bg-black/50 p-6 rounded-xl border border-white/10 overflow-x-auto">
                                    <pre className="text-sm text-green-400"><code>{`{
  "classification": "finalizar",
  "confidence": 1.0,
  "source": "local_model",
  "classifications": ["finalizar"],
  "domain": "transport",
  "token_usage": {
    "prompt_tokens": 120,
    "completion_tokens": 5,
    "total_tokens": 125
  }
}`}</code></pre>
                                </div>
                            </div>
                        </div>
                    )}
                </main>
            </div>
        </AnimatedGradientBg>
    )
}

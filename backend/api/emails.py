import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Variables loaded dynamically inside the function

# Function to get styled CSS dynamically with FRONTEND_URL
def get_email_style(frontend_url):
    return f"""
<style>
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #09090b; color: #fafafa; margin: 0; padding: 0; }}
    .wrapper {{ background-color: #09090b; background-image: url('{frontend_url}/hero-bg.png'); background-size: cover; background-position: center; padding: 40px 20px; min-height: 100vh; }}
    .container {{ max-width: 600px; margin: 0 auto; }}
    .card {{ background-color: rgba(24, 24, 27, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; text-align: center; box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5); }}
    .logo {{ margin-bottom: 32px; display: inline-block; }}
    .logo img {{ height: 48px; width: auto; }}
    h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 16px; color: #fff; letter-spacing: -0.5px; }}
    p {{ font-size: 16px; line-height: 1.6; color: #a1a1aa; margin-bottom: 24px; }}
    .btn {{ display: inline-block; background-color: #8b5cf6; background: linear-gradient(135deg, #a855f7, #6366f1); color: #fff !important; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-bottom: 24px; box-shadow: 0 4px 14px 0 rgba(139, 92, 246, 0.39); }}
    .btn:hover {{ opacity: 0.9; }}
    .footer {{ font-size: 13px; color: #52525b; margin-top: 32px; text-align: center; line-height: 1.5; }}
    .feature-list {{ text-align: left; background: rgba(9, 9, 11, 0.8); padding: 24px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 32px; }}
    .feature-item {{ margin-bottom: 12px; color: #e4e4e7; font-size: 15px; display: flex; align-items: center; }}
    .feature-icon {{ color: #a855f7; margin-right: 12px; font-weight: bold; }}
</style>
"""

def send_email_async(to_email, subject, html_content):
    def _send():
        from dotenv import load_dotenv
        load_dotenv("/Users/rafaeldasilvamarques/Desktop/Agents/backend/.env", override=True)
        SMTP_HOST = os.environ.get("SMTP_HOST", "mail.qlorify.com")
        SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
        SMTP_USER = os.environ.get("SMTP_USER", "contato@qlorify.com")
        SMTP_PASS = os.environ.get("SMTP_PASS", "")

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Qlorify <{SMTP_USER}>"
            msg["To"] = to_email
            
            part = MIMEText(html_content, "html")
            msg.attach(part)
            
            if SMTP_PORT == 465:
                # SSL
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                    server.login(SMTP_USER, SMTP_PASS)
                    server.sendmail(SMTP_USER, to_email, msg.as_string())
            else:
                # TLS
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASS)
                    server.sendmail(SMTP_USER, to_email, msg.as_string())
                    
            print(f"[EmailService] Email '{subject}' sent to {to_email}", flush=True)
        except Exception as e:
            print(f"[EmailService] Failed to send email to {to_email}: {e}", flush=True)
            
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

def send_validation_email(to_email, name, token):
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <html>
    <head>{get_email_style(FRONTEND_URL)}</head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="card">
                    <div class="logo">
                        <img src="{FRONTEND_URL}/logotipo.png" alt="Qlorify Logo" />
                    </div>
                    <h1>Quase lá, {name or 'Desenvolvedor'}! 🚀</h1>
                <p>Obrigado por criar sua conta na Qlorify. Você está a um clique de acessar a plataforma definitiva de orquestração de IA. Para garantir a segurança da sua conta, por favor confirme o seu endereço de e-mail.</p>
                
                <a href="{link}" class="btn">Ativar Minha Conta</a>
                
                <p style="margin-top: 16px; font-size: 14px;">Ou copie e cole o link no seu navegador:<br><a href="{link}" style="color: #8b5cf6; text-decoration: none; word-break: break-all;">{link}</a></p>
            </div>
            <div class="footer">
                Este e-mail foi enviado automaticamente.<br>
                Se você não se cadastrou na Qlorify, pode ignorar esta mensagem.
            </div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_async(to_email, "Valide seu E-mail - Qlorify", html)

def send_welcome_email(to_email, name):
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    html = f"""
    <html>
    <head>{get_email_style(FRONTEND_URL)}</head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="card">
                    <div class="logo">
                        <img src="{FRONTEND_URL}/logotipo.png" alt="Qlorify Logo" />
                    </div>
                    <h1>Tudo Pronto! 🎉</h1>
                <p>Sua conta está oficialmente ativada. Bem-vindo à nova era do desenvolvimento com IA. Agora você já pode acessar o painel e começar a orquestrar seus agentes e fluxos de trabalho com alta performance.</p>
                
                <div class="feature-list">
                    <div class="feature-item"><span class="feature-icon">✦</span> Acesso aos modelos mais modernos e treinados especialmente para sua operação</div>
                    <div class="feature-item"><span class="feature-icon">✦</span> Gestão centralizada de chaves e custos</div>
                    <div class="feature-item"><span class="feature-icon">✦</span> Criação e acionamento de funções inteligentes</div>
                </div>

                <a href="{FRONTEND_URL}/dashboard" class="btn">Acessar Meu Painel</a>
                </div>
                <div class="footer">Equipe Qlorify &copy; 2026. Todos os direitos reservados.</div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_async(to_email, "Bem-vindo à Qlorify!", html)

def send_login_warning(to_email, ip, device, time_str):
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    html = f"""
    <html>
    <head>{get_email_style(FRONTEND_URL)}</head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="card">
                    <div class="logo">
                        <img src="{FRONTEND_URL}/logotipo.png" alt="Qlorify Logo" />
                    </div>
                    <h1>Novo Acesso Detectado</h1>
                <p>Detectamos um novo login na sua conta Qlorify com as seguintes informações:</p>
                <div style="background-color: #09090b; padding: 16px; border-radius: 8px; text-align: left; margin-bottom: 24px; border: 1px solid #27272a;">
                    <p style="margin-bottom: 8px; color: #e4e4e7;"><strong>Data e Hora:</strong> {time_str}</p>
                    <p style="margin-bottom: 8px; color: #e4e4e7;"><strong>IP:</strong> {ip}</p>
                    <p style="margin-bottom: 0; color: #e4e4e7;"><strong>Dispositivo:</strong> {device}</p>
                </div>
                <p>Se foi você, nenhuma ação é necessária.</p>
                <p style="color: #ef4444; font-weight: bold;">Não foi você?</p>
                <p>Acesse imediatamente sua conta e altere sua senha, ou responda este e-mail para contatar o suporte.</p>
                </div>
                <div class="footer">Este e-mail é gerado automaticamente para a sua segurança.</div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_async(to_email, "Alerta de Segurança: Novo Login Detectado", html)

def send_password_reset(to_email, token):
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <html>
    <head>{get_email_style(FRONTEND_URL)}</head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="card">
                    <div class="logo">
                        <img src="{FRONTEND_URL}/logotipo.png" alt="Qlorify Logo" />
                    </div>
                    <h1>Recuperação de Senha</h1>
                <p>Você solicitou a redefinição da sua senha. Clique no botão abaixo para criar uma nova senha. Este link expira em 1 hora.</p>
                <a href="{link}" class="btn">Redefinir Minha Senha</a>
                <p>Se você não solicitou isso, pode ignorar este e-mail com segurança.</p>
                </div>
                <div class="footer">Este e-mail é gerado automaticamente. Por favor, não responda.</div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_async(to_email, "Redefinição de Senha - Qlorify", html)

def send_recharge_receipt(to_email, name, amount, type_desc, date_str):
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    html = f"""
    <html>
    <head>{get_email_style(FRONTEND_URL)}</head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="card">
                    <div class="logo">
                        <img src="{FRONTEND_URL}/logotipo.png" alt="Qlorify Logo" />
                    </div>
                    <h1>Recarga Confirmada</h1>
                <p>Olá, {name or 'Usuário'}! Sua recarga foi processada com sucesso.</p>
                <div style="background-color: #09090b; padding: 16px; border-radius: 8px; text-align: left; margin-bottom: 24px; border: 1px solid #27272a;">
                    <p style="margin-bottom: 8px; color: #e4e4e7;"><strong>Valor:</strong> ${amount:.2f}</p>
                    <p style="margin-bottom: 8px; color: #e4e4e7;"><strong>Modalidade:</strong> {type_desc}</p>
                    <p style="margin-bottom: 0; color: #e4e4e7;"><strong>Data:</strong> {date_str}</p>
                </div>
                <p>Seus créditos já estão disponíveis na sua conta.</p>
                <a href="{FRONTEND_URL}/dashboard" class="btn">Ir para o Dashboard</a>
                </div>
                <div class="footer">Este é o recibo da sua transação. Obrigado por usar a Qlorify!</div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_async(to_email, "Recibo de Recarga - Qlorify", html)

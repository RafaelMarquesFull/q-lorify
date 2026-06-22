from django.urls import path
from . import auth, users, admin_controllers, agent_controllers, engine_controllers, stripe_controllers, apikey_controllers, sentiment_controller, dashboard_controllers
from .orchestrator import controllers as orchestrator_controllers
from .orchestrator import admin as orchestrator_admin
from .orchestrator import user_controllers as orchestrator_user

urlpatterns = [
    path('auth/register', auth.register, name='register'),
    path('auth/login', auth.login, name='login'),
    path('auth/google', auth.google_login, name='google_login'),
    path('auth/verify-email', auth.verify_email, name='verify_email'),
    path('auth/request-password-reset', auth.request_password_reset, name='request_password_reset'),
    path('auth/reset-password', auth.reset_password, name='reset_password'),
    path('users/me', users.me, name='users_me'),
    path('users/update', users.update_me, name='users_update'),
    
    path('admin/providers', admin_controllers.providers, name='admin_providers'),
    path('admin/providers/<str:provider_id>/keys', admin_controllers.provider_keys, name='admin_provider_keys'),
    path('admin/providers/<str:provider_id>/sync', admin_controllers.sync_provider_models, name='sync_provider_models'),
    path('admin/models', admin_controllers.models, name='admin_models'),
    path('admin/users', admin_controllers.users, name='admin_users'),
    path('admin/users/balance', admin_controllers.manage_balance, name='admin_manage_balance'),
    path('admin/stats', admin_controllers.stats, name='admin_stats'),
    
    # New Admin Dashboard
    path('admin/dashboard/stats', admin_controllers.admin_stats, name='admin_dashboard_stats'),
    path('admin/dashboard/chart', admin_controllers.admin_chart, name='admin_dashboard_chart'),
    path('admin/dashboard/chart/distribution', admin_controllers.admin_cost_distribution, name='admin_dashboard_cost_distribution'),
    path('admin/dashboard/activity', admin_controllers.admin_activity, name='admin_dashboard_activity'),
    
    # Orchestrator Admin
    path('admin/orchestrator/functions', orchestrator_admin.functions, name='admin_orch_functions'),
    path('admin/orchestrator/functions/sync', orchestrator_admin.sync_functions, name='admin_orch_sync_functions'),
    path('admin/orchestrator/clients', orchestrator_admin.clients, name='admin_orch_clients'),
    path('admin/orchestrator/clients/<str:client_id>/regenerate-token', orchestrator_admin.regenerate_client_token, name='admin_orch_regenerate_token'),
    path('admin/orchestrator/executions', orchestrator_admin.executions, name='admin_orch_executions'),
    
    path('admin/settings/rules-model', agent_controllers.admin_settings_rules_model, name='admin_settings_rules_model'),
    path('agents', agent_controllers.list_create_agents, name='list_create_agents'),
    path('admin/agents', agent_controllers.admin_agents, name='admin_agents'),
    path('admin/agents/<str:agent_id>/compile-rules', agent_controllers.compile_agent_rules, name='compile_agent_rules'),
    path('admin/agents/<str:agent_id>/rules', agent_controllers.get_agent_rules, name='get_agent_rules'),
    path('public/models', agent_controllers.list_models_public, name='list_models_public'),
    path('public/functions', agent_controllers.list_functions_public, name='list_functions_public'),
    
    path('keys', apikey_controllers.list_create_keys, name='list_create_keys'),
    path('keys/<str:key_id>', apikey_controllers.revoke_key, name='revoke_key'),
    
    path('chat/completions', engine_controllers.chat_completions, name='chat_completions'),
    
    # AI Orchestrator - User
    path('user/functions', orchestrator_user.user_functions, name='user_functions'),
    path('user/functions/<str:function_name>/keys', orchestrator_user.user_function_keys, name='user_function_keys'),
    
    # AI Orchestrator - Execute
    path('ai/execute', orchestrator_controllers.execute, name='orchestrator_execute'),
    path('ai/functions', orchestrator_controllers.list_available_functions, name='orchestrator_functions'),
    
    # Sentiment Analysis Orchestrator
    path('ai/sentiment/analyze', sentiment_controller.sentiment_analyze, name='sentiment_analyze'),
    
    # Sentiment Self-Learning Admin
    path('ai/sentiment/logs', sentiment_controller.sentiment_logs_list, name='sentiment_logs_list'),
    path('ai/sentiment/logs/<str:log_id>/review', sentiment_controller.sentiment_logs_review, name='sentiment_logs_review'),
    path('ai/sentiment/logs/<str:log_id>/evaluate', sentiment_controller.sentiment_logs_evaluate, name='sentiment_logs_evaluate'),
    path('ai/sentiment/synonyms', sentiment_controller.sentiment_synonyms_list, name='sentiment_synonyms_list'),
    path('ai/sentiment/synonyms/<str:synonym_id>', sentiment_controller.sentiment_synonyms_delete, name='sentiment_synonyms_delete'),
    path('ai/sentiment/patterns', sentiment_controller.sentiment_patterns_list, name='sentiment_patterns_list'),
    path('ai/sentiment/stats', sentiment_controller.sentiment_stats, name='sentiment_stats'),
    path('ai/sentiment/stats/domain', sentiment_controller.sentiment_stats_by_domain, name='sentiment_stats_by_domain'),
    path('ai/sentiment/train', sentiment_controller.train_sentiment_model, name='train_sentiment_model'),
    path('ai/sentiment/stats/performance', dashboard_controllers.get_performance_stats, name='get_performance_stats'),
    path('ai/sentiment/stats/financial', dashboard_controllers.get_financial_stats, name='get_financial_stats'),
    
    # Billing & Balance
    path('billing/balance', stripe_controllers.get_balance, name='get_balance'),
    path('billing/checkout/setup', stripe_controllers.create_setup_checkout_session, name='create_setup_checkout_session'),
    path('billing/checkout/recharge', stripe_controllers.create_recharge_checkout_session, name='create_recharge_checkout_session'),

    path('billing/settings', stripe_controllers.update_settings, name='update_settings'),
    path('billing/webhook', stripe_controllers.webhook, name='stripe_webhook'),

    # Real Dashboard Analytics
    path('dashboard/stats', dashboard_controllers.get_overview_stats, name='dashboard_stats'),
    path('dashboard/chart', dashboard_controllers.get_usage_chart, name='dashboard_chart'),
    path('dashboard/activity', dashboard_controllers.get_recent_activity, name='dashboard_activity'),
    path('dashboard/chart/distribution', dashboard_controllers.get_cost_distribution, name='dashboard_cost_distribution'),
]




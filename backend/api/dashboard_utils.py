
from datetime import timedelta
import pytz
from django.utils import timezone as django_timezone

SP_TZ = pytz.timezone('America/Sao_Paulo')
WEEKDAYS_PT = {
    "Mon": "Seg", "Tue": "Ter", "Wed": "Qua", "Thu": "Qui", "Fri": "Sex", "Sat": "Sáb", "Sun": "Dom"
}

def get_date_range(time_range):
    now = django_timezone.now()
    if time_range == '24h':
        start_date = now - timedelta(hours=24)
    elif time_range == '30d':
        start_date = now - timedelta(days=30)
    else: # 7d default
        start_date = now - timedelta(days=7)
    return now, start_date

def get_iterations_and_format(time_range):
    if time_range == '24h':
        return 24, "%H:00"
    elif time_range == '30d':
        return 30, "%d/%m"
    else: # 7d
        return 7, "%a"

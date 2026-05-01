import pandas as pd
import numpy as np
import re
import random
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# Налаштування стилю графіків
sns.set_theme(style="whitegrid")

# ==========================================
# 1. ГЕНЕРАЦІЯ СИНТЕТИЧНИХ ДАНИХ
# ==========================================
def generate_fake_logs(filename, num_entries=15000):
    """Генерує файл логів у форматі Nginx Combined для тестування"""
    ips = [f"192.168.1.{random.randint(1, 255)}" for _ in range(50)]
    ips.extend(["45.33.22.11", "185.212.131.44"]) # Аномальні IP
    
    methods = ["GET", "POST", "HEAD"]
    resources = ["/", "/login", "/api/data", "/admin", "/config"]
    status_codes = [200, 200, 200, 301, 404, 500, 403]
    
    start_time = datetime.now() - timedelta(days=1)
    
    with open(filename, 'w') as f:
        for _ in range(num_entries):
            ip = random.choice(ips)
            log_time = start_time + timedelta(seconds=random.randint(0, 86400))
            time_str = log_time.strftime('%d/%b/%Y:%H:%M:%S +0300')
            method = random.choice(methods)
            resource = random.choice(resources)
            status = random.choice(status_codes)
            size = random.randint(200, 5000)
            
            log_line = f'{ip} - - [{time_str}] "{method} {resource} HTTP/1.1" {status} {size} "https://google.com" "Mozilla/5.0"\n'
            f.write(log_line)

# ==========================================
# 2. ПАРСИНГ ТА ПОПЕРЕДНЯ ОБРОБКА
# ==========================================
def parse_logs(file_content):
    """Парсинг лог-файлу за допомогою регулярних виразів та Pandas"""
    log_pattern = r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<timestamp>.*?)\] "(?P<method>\w+) (?P<url>.*?) HTTP/.*?" (?P<status>\d+) (?P<size>\d+)'
    
    parsed_data = []
    # Обробка як списку рядків (для завантажених файлів у Streamlit)
    for line in file_content:
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        match = re.search(log_pattern, line)
        if match:
            parsed_data.append(match.groupdict())
    
    df = pd.DataFrame(parsed_data)
    
    if df.empty:
        return df

    # Оптимізація типів даних
    df['status'] = df['status'].astype('category')
    df['size'] = pd.to_numeric(df['size'], errors='coerce').fillna(0).astype('int32')
    
    # Конвертація часу (важливо для ресемплінгу)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%d/%b/%Y:%H:%M:%S +0300')
    
    df.dropna(subset=['timestamp'], inplace=True)
    return df

# ==========================================
# 3. АНАЛІТИЧНА АГРЕГАЦІЯ (ВИПРАВЛЕНО)
# ==========================================
def perform_analysis(df):
    """Проведення статистичного аналізу даних без помилок ValueError"""
    
    # 1. Топ-10 активних IP
    top_ips = df['ip'].value_counts().head(10)
    
    # 2. Розрахунок помилок
    total_requests = len(df)
    error_4xx = len(df[df['status'].astype(str).str.startswith('4')])
    error_5xx = len(df[df['status'].astype(str).str.startswith('5')])
    
    # 3. Ресемплінг (ВИПРАВЛЕННЯ ПОМИЛКИ З ТРЕЙСБЕКУ)
    # Використовуємо аргумент 'on', щоб не змінювати індекс всього DataFrame передчасно
    hourly_activity = df.resample('H', on='timestamp').size()
    
    return top_ips, hourly_activity, total_requests, error_4xx, error_5xx

# ==========================================
# 4. STREAMLIT ІНТЕРФЕЙС
# ==========================================
st.set_page_config(page_title="CyberLog Analyzer", layout="wide")
st.title("🛡️ Аналізатор мережевих логів (Pandas Edition)")

# Генерація тестового файлу, якщо його немає
if st.sidebar.button("Згенерувати тестові логи"):
    generate_fake_logs("test_access.log", 20000)
    st.sidebar.success("Файл test_access.log створено!")

uploaded_file = st.sidebar.file_uploader("Завантажте .log файл", type=["log", "txt"])

if uploaded_file is not None:
    # Читаємо файл
    lines = uploaded_file.readlines()
    df = parse_logs(lines)
    
    if not df.empty:
        # Аналіз
        top_ips, hourly_activity, total, e4xx, e5xx = perform_analysis(df)
        
        # Метрики
        col1, col2, col3 = st.columns(3)
        col1.metric("Усього запитів", total)
        col2.metric("Помилки 4xx", e4xx, f"{e4xx/total:.1%}", delta_color="inverse")
        col3.metric("Помилки 5xx", e5xx, f"{e5xx/total:.1%}", delta_color="inverse")
        
        # Візуалізація
        st.subheader("📊 Аналіз активності")
        
        # Графік 1: Часова активність
        st.line_chart(hourly_activity)
        
        # Графік 2: Топ IP
        st.subheader("🔝 Топ-10 джерел трафіку")
        st.bar_chart(top_ips)
        
        # Детальна таблиця
        if st.checkbox("Показати сирі дані"):
            st.dataframe(df.head(100), use_container_width=True)
    else:
        st.error("Не вдалося розпізнати дані у файлі. Перевірте формат логів.")
else:
    st.info("Будь ласка, завантажте файл через бічне меню або згенеруйте тестовий набір.")

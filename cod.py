import pandas as pd
import numpy as np
import re
import random
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Налаштування стилю графіків
sns.set_theme(style="whitegrid")

# ==========================================
# 1. ГЕНЕРАЦІЯ СИНТЕТИЧНИХ ДАНИХ
# ==========================================
def generate_fake_logs(filename, num_entries=15000):
    """Генерує файл логів у форматі Nginx Combined для тестування"""
    ips = [f"192.168.1.{random.randint(1, 255)}" for _ in range(50)]
    # Додаємо кілька "підозрілих" IP для аномалій
    ips.extend(["45.33.22.11", "185.212.131.44"]) 
    
    methods = ["GET", "POST", "HEAD"]
    resources = ["/", "/login", "/api/data", "/admin", "/config", "/static/css/style.css"]
    status_codes = [200, 200, 200, 301, 404, 500, 403]
    
    start_time = datetime.now() - timedelta(days=1)
    
    with open(filename, 'w') as f:
        for _ in range(num_entries):
            ip = random.choice(ips)
            # Випадковий час протягом останньої доби
            log_time = start_time + timedelta(seconds=random.randint(0, 86400))
            time_str = log_time.strftime('%d/%b/%Y:%H:%M:%S +0300')
            method = random.choice(methods)
            resource = random.choice(resources)
            status = random.choice(status_codes)
            size = random.randint(200, 5000)
            
            log_line = f'{ip} - - [{time_str}] "{method} {resource} HTTP/1.1" {status} {size} "https://google.com" "Mozilla/5.0"\n'
            f.write(log_line)
    print(f"Файл {filename} успішно згенеровано ({num_entries} рядків).")

# ==========================================
# 2. ПАРСИНГ ТА ПОПЕРЕДНЯ ОБРОБКА
# ==========================================
def parse_logs(filename):
    """Парсинг лог-файлу за допомогою регулярних виразів та Pandas"""
    # Регулярний вираз для Combined Log Format
    log_pattern = r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<timestamp>.*?)\] "(?P<method>\w+) (?P<url>.*?) HTTP/.*?" (?P<status>\d+) (?P<size>\d+)'
    
    parsed_data = []
    
    with open(filename, 'r') as f:
        for line in f:
            match = re.search(log_pattern, line)
            if match:
                parsed_data.append(match.groupdict())
    
    df = pd.DataFrame(parsed_data)
    
    # Конвертація типів для оптимізації пам'яті
    df['status'] = df['status'].astype('category')  # Категоріальний тип для кодів
    df['size'] = pd.to_numeric(df['size'], errors='coerce').astype('int32')
    
    # Обробка часу (видаляємо часовий пояс для простоти аналізу)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%d/%b/%Y:%H:%M:%S +0300')
    
    # Очищення від порожніх значень
    df.dropna(inplace=True)
    
    return df

# ==========================================
# 3. АНАЛІТИЧНА АГРЕГАЦІЯ
# ==========================================
def perform_analysis(df):
    """Проведення статистичного аналізу даних"""
    print("\n--- АНАЛІТИЧНИЙ ЗВІТ ---")
    
    # 1. Топ-10 активних IP
    top_ips = df['ip'].value_counts().head(10)
    print("\nТоп-10 IP-адрес:")
    print(top_ips)
    
    # 2. Відсоток помилок
    total_requests = len(df)
    error_4xx = len(df[df['status'].str.startswith('4')])
    error_5xx = len(df[df['status'].str.startswith('5')])
    
    print(f"\nЗагальна кількість запитів: {total_requests}")
    print(f"Помилки 4xx (Client Error): {error_4xx} ({error_4xx/total_requests:.2%})")
    print(f"Помилки 5xx (Server Error): {error_5xx} ({error_5xx/total_requests:.2%})")
    
    # 3. Ресемплінг: активність по годинах
    df.set_index('timestamp', inplace=True)
    hourly_activity = df.resample('H').size()
    
    return top_ips, hourly_activity, df

# ==========================================
# 4. ВІЗУАЛІЗАЦІЯ
# ==========================================
def visualize_results(top_ips, hourly_activity, df_indexed):
    """Побудова графіків для аналізу"""
    plt.figure(figsize=(15, 12))
    
    # ГРАФІК 1: Інтенсивність трафіку за часом
    plt.subplot(3, 1, 1)
    hourly_activity.plot(kind='line', marker='o', color='teal', lw=2)
    plt.title('Інтенсивність мережевого трафіку (за годинами)', fontsize=14)
    plt.ylabel('Кількість запитів')
    
    # ГРАФІК 2: Топ IP-адрес
    plt.subplot(3, 1, 2)
    sns.barplot(x=top_ips.index, y=top_ips.values, palette='viridis')
    plt.title('Топ-10 найактивніших IP-адрес', fontsize=14)
    plt.xticks(rotation=45)
    plt.ylabel('Кількість запитів')
    
    # ГРАФІК 3: Heatmap активності (Година vs День тижня)
    plt.subplot(3, 1, 3)
    df_indexed['hour'] = df_indexed.index.hour
    df_indexed['day'] = df_indexed.index.day_name()
    
    # Створюємо зведену таблицю для теплової карти
    pivot_table = df_indexed.pivot_table(index='hour', columns='day', values='ip', aggfunc='count').fillna(0)
    sns.heatmap(pivot_table, annot=False, cmap='YlGnBu')
    plt.title('Теплова карта активності (Година доби vs День тижня)', fontsize=14)
    
    plt.tight_layout()
    plt.show()

# ==========================================
# ГОЛОВНИЙ БЛОК ВИКОНАННЯ
# ==========================================
if __name__ == "__main__":
    LOG_FILE = "access_logs_sample.log"
    
    # Крок 1: Генеруємо дані
    generate_fake_logs(LOG_FILE, 15000)
    
    # Крок 2: Парсимо дані
    log_df = parse_logs(LOG_FILE)
    
    # Крок 3: Аналізуємо
    top_ips, hourly_data, df_indexed = perform_analysis(log_df)
    
    # Крок 4: Візуалізуємо
    visualize_results(top_ips, hourly_data, df_indexed)
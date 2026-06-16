import sqlite3
import threading
import os
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_PATH


class DatabaseConnection:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return

        self.db_path = db_path or DATABASE_PATH
        self._local = threading.local()
        self._initialized = True

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._init_database()

    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # ========== ОСНОВНЫЕ ТАБЛИЦЫ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    organization_type TEXT DEFAULT 'average',
                    industry TEXT DEFAULT 'education',
                    auto_detected_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    block_id INTEGER NOT NULL,
                    block_name TEXT NOT NULL,
                    factor_id INTEGER NOT NULL,
                    factor_name TEXT NOT NULL,
                    description TEXT,
                    tooltip TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    user_id INTEGER,
                    assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    final_score REAL,
                    technical_factor REAL,
                    cognitive_factor REAL,
                    personal_factor REAL,
                    organization_type_auto TEXT,
                    FOREIGN KEY (org_id) REFERENCES organizations(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assessment_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL,
                    indicator_code TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    base_growth REAL NOT NULL,
                    cost REAL NOT NULL,
                    risk REAL NOT NULL,
                    inertia_shock REAL NOT NULL,
                    cognitive_load REAL NOT NULL,
                    resource_type TEXT
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ АУТЕНТИФИКАЦИИ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'viewer',
                    email TEXT,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ ОТРАСЛЕЙ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS industries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    default_alpha REAL DEFAULT 0.1,
                    default_beta REAL DEFAULT 0.3,
                    default_gamma REAL DEFAULT 0.15,
                    default_delta REAL DEFAULT 0.05,
                    default_kappa REAL DEFAULT 2.0,
                    default_lambda REAL DEFAULT 1.5,
                    benchmark_25 REAL,
                    benchmark_50 REAL,
                    benchmark_75 REAL,
                    benchmark_leader REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS industry_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry_code TEXT NOT NULL,
                    factor_name TEXT NOT NULL,
                    adjustment REAL DEFAULT 1.0,
                    description TEXT,
                    FOREIGN KEY (industry_code) REFERENCES industries(code)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ БЕНЧМАРКОВ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry_code TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    percentile_25 REAL,
                    percentile_50 REAL,
                    percentile_75 REAL,
                    leader_value REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (industry_code) REFERENCES industries(code)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ АНАЛИТИКИ ROI ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roi_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    sprint_id INTEGER NOT NULL,
                    planned_cost REAL,
                    actual_cost REAL,
                    planned_growth REAL,
                    actual_growth REAL,
                    roi REAL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (org_id) REFERENCES organizations(id),
                    FOREIGN KEY (sprint_id) REFERENCES sprints(id)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ СПРИНТОВ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transformation_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    user_id INTEGER,
                    plan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_reward REAL,
                    final_maturity REAL,
                    peak_inertia REAL,
                    success INTEGER,
                    plan_data TEXT,
                    rationale TEXT,
                    status TEXT DEFAULT 'active',
                    is_template INTEGER DEFAULT 0,
                    template_name TEXT,
                    FOREIGN KEY (org_id) REFERENCES organizations(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    number INTEGER NOT NULL,
                    action_ids TEXT NOT NULL,
                    planned_start DATE NOT NULL,
                    planned_end DATE NOT NULL,
                    actual_start DATE,
                    actual_end DATE,
                    planned_growth REAL,
                    actual_growth REAL,
                    planned_cost REAL DEFAULT 0,
                    actual_cost REAL DEFAULT 0,
                    status TEXT DEFAULT 'planned',
                    notes TEXT,
                    FOREIGN KEY (plan_id) REFERENCES transformation_plans(id)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ УВЕДОМЛЕНИЙ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT NOT NULL,
                    related_entity_type TEXT,
                    related_entity_id INTEGER,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS export_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    export_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    entity_id INTEGER,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ ПРОГНОЗИРОВАНИЯ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    horizon_months INTEGER NOT NULL,
                    predicted_score REAL,
                    confidence_lower REAL,
                    confidence_upper REAL,
                    model_version TEXT,
                    FOREIGN KEY (org_id) REFERENCES organizations(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_success_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id INTEGER NOT NULL,
                    industry_code TEXT NOT NULL,
                    times_used INTEGER DEFAULT 0,
                    avg_actual_growth REAL,
                    success_rate REAL,
                    FOREIGN KEY (action_id) REFERENCES actions(id),
                    FOREIGN KEY (industry_code) REFERENCES industries(code)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ ЗАВИСИМОСТЕЙ ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id INTEGER NOT NULL,
                    depends_on_action_id INTEGER NOT NULL,
                    dependency_type TEXT DEFAULT 'required',
                    FOREIGN KEY (action_id) REFERENCES actions(id),
                    FOREIGN KEY (depends_on_action_id) REFERENCES actions(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plan_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    industry_code TEXT,
                    plan_data TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (industry_code) REFERENCES industries(code),
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            ''')

            # ========== ТАБЛИЦЫ ДЛЯ СИСТЕМНЫХ МЕТРИК ==========

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id INTEGER,
                    details TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            # ========== ДОБАВЛЕНИЕ ОТСУТСТВУЮЩИХ КОЛОНОК ==========

            # Добавляем колонку industry в organizations, если её нет
            try:
                cursor.execute("ALTER TABLE organizations ADD COLUMN industry TEXT DEFAULT 'education'")
                print("[INFO] Добавлена колонка industry в таблицу organizations")
            except sqlite3.OperationalError:
                pass  # колонка уже существует

            # Добавляем колонку auto_detected_type в organizations, если её нет
            try:
                cursor.execute("ALTER TABLE organizations ADD COLUMN auto_detected_type TEXT")
                print("[INFO] Добавлена колонка auto_detected_type в таблицу organizations")
            except sqlite3.OperationalError:
                pass

            # Добавляем колонку is_template в transformation_plans, если её нет
            try:
                cursor.execute("ALTER TABLE transformation_plans ADD COLUMN is_template INTEGER DEFAULT 0")
                print("[INFO] Добавлена колонка is_template в таблицу transformation_plans")
            except sqlite3.OperationalError:
                pass

            # Добавляем колонку template_name в transformation_plans, если её нет
            try:
                cursor.execute("ALTER TABLE transformation_plans ADD COLUMN template_name TEXT")
                print("[INFO] Добавлена колонка template_name в таблицу transformation_plans")
            except sqlite3.OperationalError:
                pass

            # Добавляем колонку planned_cost в sprints, если её нет
            try:
                cursor.execute("ALTER TABLE sprints ADD COLUMN planned_cost REAL DEFAULT 0")
                print("[INFO] Добавлена колонка planned_cost в таблицу sprints")
            except sqlite3.OperationalError:
                pass

            # Добавляем колонку actual_cost в sprints, если её нет
            try:
                cursor.execute("ALTER TABLE sprints ADD COLUMN actual_cost REAL DEFAULT 0")
                print("[INFO] Добавлена колонка actual_cost в таблицу sprints")
            except sqlite3.OperationalError:
                pass

            conn.commit()

            # Инициализация начальных данных
            self._init_indicators()
            self._init_industries()
            self._init_benchmarks()
            self._init_default_settings()
            self._ensure_admin_user()

    def _init_indicators(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM indicators")
            if cursor.fetchone()[0] > 0:
                return

            indicators_data = [
                ('1.1', 'Адекватность понимания нравственных аспектов цифровизации', 1, 'Личностный фактор', 1,
                 'Личностный',
                 'Оцените, насколько сотрудники понимают этические и социальные последствия цифровизации',
                 '0: полное непонимание; 1: базовые знания; 2: системное понимание; 3: проактивная позиция'),
                ('1.2', 'Демократичность цифровизации процессов', 1, 'Личностный фактор', 1, 'Личностный',
                 'Степень вовлечения сотрудников в принятие решений',
                 '0: решения сверху; 1: отдельные консультации; 2: регулярные обсуждения; 3: совместные решения'),
                ('1.3', 'Воздействие цифровизации на личностный рост', 1, 'Личностный фактор', 1, 'Личностный',
                 'Как цифровая трансформация способствует развитию',
                 '0: негативно; 1: нейтрально; 2: положительно; 3: драйвер развития'),
                ('2.1', 'Уровень развития цифровых компетенций сотрудников', 2, 'Компетенции', 2, 'Когнитивный',
                 'Владение цифровыми навыками сотрудниками',
                 '0: нет навыков; 1: базовые; 2: уверенное владение; 3: экспертный уровень'),
                ('2.2', 'Уровень владения цифровыми и аналитическими инструментами', 2, 'Компетенции', 2, 'Когнитивный',
                 'Умение работать с аналитикой и цифровыми инструментами',
                 '0: только Excel; 1: специализированные системы; 2: BI-инструменты; 3: продвинутая аналитика'),
                ('2.3', 'Зрелость подхода к развитию цифровых компетенций', 2, 'Компетенции', 2, 'Когнитивный',
                 'Системность обучения и развития компетенций',
                 '0: не проводится; 1: эпизодически; 2: регулярно; 3: непрерывное развитие'),
                ('3.1', 'Развитость цифровых инструментов управления задачами', 3, 'Организационная культура', 3,
                 'Технический',
                 'Наличие систем управления проектами и задачами',
                 '0: бумажные журналы; 1: простые системы; 2: автоматизация; 3: единая среда'),
                ('3.2', 'Инициативность исполнителей при управлении задачами', 3, 'Организационная культура', 3,
                 'Технический',
                 'Поощрение инициативы и предложений по улучшению',
                 '0: не поощряется; 1: допускается; 2: поощряется; 3: культура инноваций'),
                ('3.3', 'Осуществление промежуточного контроля и оценки результатов', 3, 'Организационная культура', 3,
                 'Технический',
                 'Мониторинг выполнения задач и KPI',
                 '0: только финальный; 1: эпизодический; 2: регулярный; 3: непрерывный'),
                ('4.1', 'Зрелость управления процессами', 4, 'Процессы', 3, 'Технический',
                 'Описание и стандартизация процессов',
                 '0: не описаны; 1: частично; 2: стандартизированы; 3: непрерывное улучшение'),
                ('4.2', 'Возможности оптимизации процессов', 4, 'Процессы', 3, 'Технический',
                 'Анализ и оптимизация процессов',
                 '0: не проводится; 1: по запросу; 2: регулярно; 3: предиктивная оптимизация'),
                ('4.3', 'Степень автоматизации процессов', 4, 'Процессы', 3, 'Технический',
                 'Уровень автоматизации бизнес-процессов',
                 '0: ручной ввод; 1: частичная; 2: сквозная; 3: роботизация RPA'),
                ('5.1', 'Участие в создании цифровых продуктов', 5, 'Продукты', 2, 'Когнитивный',
                 'Разработка цифровых продуктов и сервисов',
                 '0: не создаются; 1: по запросу; 2: регулярно; 3: инновационная экосистема'),
                ('5.2', 'Управление требованиями к цифровым продуктам', 5, 'Продукты', 2, 'Когнитивный',
                 'Сбор и приоритизация требований',
                 '0: не документируются; 1: фиксируются; 2: системно; 3: Agile методологии'),
                ('5.3', 'Применение цифровых технологий в создании продуктов', 5, 'Продукты', 2, 'Когнитивный',
                 'Использование современных технологий',
                 '0: устаревшие; 1: современные; 2: системное применение; 3: передовые технологии AI/IoT'),
                ('6.1', 'Уровень владения аналитическими методами', 6, 'Модели', 2, 'Когнитивный',
                 'Использование аналитики в принятии решений',
                 '0: не используется; 1: описательная; 2: диагностическая; 3: прогнозная'),
                ('6.2', 'Уровень цифровизации траекторий развития обучающихся', 6, 'Модели', 2, 'Когнитивный',
                 'Индивидуальные образовательные траектории',
                 '0: единая программа; 1: выбор модулей; 2: индивидуальные траектории; 3: адаптивное обучение'),
                ('7.1', 'Степень систематизации данных', 7, 'Данные', 3, 'Технический',
                 'Структурированность и хранение данных',
                 '0: хаотично; 1: структурированы; 2: единое хранилище; 3: Data Lake'),
                ('7.2', 'Уровень обработки данных', 7, 'Данные', 3, 'Технический',
                 'Автоматизация обработки данных',
                 '0: вручную; 1: автоматизирована; 2: потоковая; 3: ML и AI'),
                ('7.3', 'Качество данных', 7, 'Данные', 3, 'Технический',
                 'Очистка и проверка данных',
                 '0: много ошибок; 1: периодическая; 2: автоматическая; 3: управление качеством'),
                ('8.1', 'Организация рабочих мест', 8, 'Инфраструктура', 3, 'Технический',
                 'Оснащение сотрудников оборудованием',
                 '0: устаревшее; 1: современное; 2: стандартизировано; 3: BYOD/удалёнка'),
                ('8.2', 'Развитость цифровых сервисов для сотрудников', 8, 'Инфраструктура', 3, 'Технический',
                 'Доступность цифровых сервисов',
                 '0: минимальный; 1: базовые; 2: широкий спектр; 3: экосистема сервисов'),
                ('8.3', 'Обеспечение информационной безопасности', 8, 'Инфраструктура', 3, 'Технический',
                 'Уровень защищённости информационных систем',
                 '0: базовый; 1: политики; 2: MFA/DLP; 3: SOC'),
                ('9.1', 'Степень цифрового единства', 9, 'Глобальная среда', 2, 'Когнитивный',
                 'Интеграция систем и единое пространство',
                 '0: разрозненные; 1: частичная; 2: единое пространство; 3: полная интеграция'),
                (
                '9.2', 'Степень ясности понимания принадлежности к глобальной цифровой среде', 9, 'Глобальная среда', 2,
                'Когнитивный',
                'Понимание глобальных трендов и участие в сообществах',
                '0: отсутствует; 1: отдельные сотрудники; 2: системный мониторинг; 3: активное участие')
            ]

            for data in indicators_data:
                cursor.execute(
                    '''INSERT INTO indicators (code, name, block_id, block_name, factor_id, factor_name, description, tooltip) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    data
                )

            conn.commit()

    def _init_industries(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM industries")
            if cursor.fetchone()[0] > 0:
                return

            industries_data = [
                ('education', 'Образование', 'Образовательные организации',
                 0.08, 0.35, 0.12, 0.04, 2.2, 1.8, 38, 52, 68, 89),
                ('it', 'IT-компания', 'Разработка ПО, IT-услуги',
                 0.15, 0.20, 0.18, 0.08, 1.5, 1.2, 58, 71, 85, 96),
                ('manufacturing', 'Производство', 'Промышленные предприятия',
                 0.06, 0.40, 0.10, 0.03, 2.5, 2.0, 31, 44, 58, 78),
                ('finance', 'Финансы', 'Банки, страховые компании',
                 0.12, 0.25, 0.14, 0.06, 1.8, 1.5, 52, 65, 79, 92),
                ('healthcare', 'Здравоохранение', 'Медицинские учреждения',
                 0.07, 0.30, 0.11, 0.04, 2.3, 1.9, 35, 48, 62, 84),
                ('retail', 'Розничная торговля', 'Торговые сети, e-commerce',
                 0.13, 0.22, 0.16, 0.07, 1.7, 1.4, 45, 58, 72, 88),
                ('government', 'Госсектор', 'Государственные организации',
                 0.05, 0.45, 0.08, 0.02, 2.8, 2.3, 28, 40, 55, 75)
            ]

            for data in industries_data:
                cursor.execute(
                    '''INSERT INTO industries 
                       (code, name, description, default_alpha, default_beta, default_gamma, 
                        default_delta, default_kappa, default_lambda, benchmark_25, 
                        benchmark_50, benchmark_75, benchmark_leader) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    data
                )

            conn.commit()

    def _init_benchmarks(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM benchmarks")
            if cursor.fetchone()[0] > 0:
                return

            benchmarks_data = [
                ('education', 'final_score', 38, 52, 68, 89),
                ('education', 'technical_factor', 35, 48, 62, 85),
                ('education', 'cognitive_factor', 32, 45, 60, 82),
                ('education', 'personal_factor', 30, 42, 55, 78),
                ('it', 'final_score', 58, 71, 85, 96),
                ('it', 'technical_factor', 60, 75, 88, 98),
                ('it', 'cognitive_factor', 55, 70, 84, 95),
                ('it', 'personal_factor', 50, 65, 78, 90),
                ('manufacturing', 'final_score', 31, 44, 58, 78),
                ('finance', 'final_score', 52, 65, 79, 92),
                ('healthcare', 'final_score', 35, 48, 62, 84),
                ('retail', 'final_score', 45, 58, 72, 88),
                ('government', 'final_score', 28, 40, 55, 75)
            ]

            for data in benchmarks_data:
                cursor.execute(
                    '''INSERT INTO benchmarks 
                       (industry_code, metric_name, percentile_25, percentile_50, 
                        percentile_75, leader_value) 
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    data
                )

            conn.commit()

    def _init_default_settings(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            default_settings = [
                ('dqn_learning_rate', '0.001', 'Скорость обучения DQN'),
                ('dqn_gamma', '0.95', 'Дисконт-фактор'),
                ('dqn_epsilon_start', '1.0', 'Начальный epsilon'),
                ('dqn_epsilon_end', '0.01', 'Конечный epsilon'),
                ('dqn_epsilon_decay', '0.995', 'Скорость затухания epsilon'),
                ('dqn_batch_size', '64', 'Размер батча для обучения'),
                ('dqn_buffer_size', '100000', 'Размер буфера воспроизведения'),
                ('target_score_increment', '25', 'Целевой прирост (баллов)'),
                ('auto_train_enabled', 'true', 'Автоматическое дообучение DQN'),
                ('auto_train_interval_hours', '24', 'Интервал дообучения (часы)'),
                ('max_plan_steps', '8', 'Максимальное количество шагов в плане'),
                ('weak_block_threshold', '1.0', 'Порог слабого блока (0-3)'),
                ('sprint_default_weeks', '2', 'Длительность спринта по умолчанию (недели)'),
                ('notification_enabled', 'true', 'Включены ли уведомления'),
                ('notification_days_before', '3', 'За сколько дней напоминать о спринте'),
                ('prediction_horizons', '3,6,12', 'Горизонты прогнозирования (месяцы)'),
                ('prediction_model_version', '1.0', 'Версия модели прогнозирования'),
            ]

            for key, value, desc in default_settings:
                cursor.execute(
                    '''INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description) 
                       VALUES (?, ?, ?)''',
                    (key, value, desc)
                )

            conn.commit()

    def _ensure_admin_user(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE role = 'admin'")
            if not cursor.fetchone():
                import hashlib
                import os
                salt = os.urandom(32)
                password = 'admin123'
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

                cursor.execute(
                    '''INSERT INTO users (username, password_hash, salt, role, email, full_name) 
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    ('admin', password_hash.hex(), salt.hex(), 'admin', 'admin@system.local', 'Системный администратор')
                )
                conn.commit()
                print("[INFO] Создан администратор по умолчанию: admin / admin123")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def query(self, query: str, params: tuple = ()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def query_one(self, query: str, params: tuple = ()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
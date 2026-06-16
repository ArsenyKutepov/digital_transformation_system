"""
Конфигурационные параметры системы
"""

import os

# ========== ПАРАМЕТРЫ ДИНАМИЧЕСКОЙ МОДЕЛИ ==========
ALPHA = 0.1
BETA = 0.3
GAMMA = 0.15
DELTA = 0.05
KAPPA = 2.0
LAMBDA = 1.5

# ========== ПАРАМЕТРЫ ФУНКЦИИ ВОЗНАГРАЖДЕНИЯ ==========
W_Z = 1.0
W_R = 0.5
W_I = 0.8
W_C = 0.6
W_RISK = 0.4

# ========== ПАРАМЕТРЫ DQN ==========
STATE_DIM = 28
ACTION_DIM = 25
BUFFER_SIZE = 100000
BATCH_SIZE = 64
GAMMA_DQN = 0.95
EPSILON_START = 1.0
EPSILON_END = 0.01
EPSILON_DECAY = 0.995
LEARNING_RATE = 0.001
TARGET_UPDATE_FREQ = 100
NUM_EPISODES = 500
MAX_STEPS_PER_EPISODE = 50

# ========== ПАРАМЕТРЫ ТИПОВ ОРГАНИЗАЦИЙ ==========
ORGANIZATION_TYPES = {
    'flexible': {
        'name': 'Гибкая',
        'alpha': 0.15, 'beta': 0.2, 'gamma': 0.2, 'delta': 0.1,
        'kappa': 1.5, 'lambda': 1.0,
        'initial_inertia': 0.2, 'initial_cognitive_load': 0.2
    },
    'average': {
        'name': 'Средняя',
        'alpha': 0.1, 'beta': 0.3, 'gamma': 0.15, 'delta': 0.05,
        'kappa': 2.0, 'lambda': 1.5,
        'initial_inertia': 0.4, 'initial_cognitive_load': 0.35
    },
    'inertial': {
        'name': 'Инерционная',
        'alpha': 0.05, 'beta': 0.5, 'gamma': 0.08, 'delta': 0.02,
        'kappa': 3.0, 'lambda': 2.5,
        'initial_inertia': 0.6, 'initial_cognitive_load': 0.5
    }
}

# ========== WEB-СЕРВЕР ==========
HOST = '127.0.0.1'
PORT = 8080
STATIC_DIR = 'web/static'
TEMPLATE_DIR = 'templates'

# ========== ПУТИ К ФАЙЛАМ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'digital_transformation.db')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')

for directory in [DATABASE_PATH, MODELS_DIR, LOGS_DIR, REPORTS_DIR, BACKUPS_DIR]:
    dir_path = os.path.dirname(directory) if '.' in directory else directory
    if not os.path.exists(dir_path) and dir_path:
        os.makedirs(dir_path, exist_ok=True)
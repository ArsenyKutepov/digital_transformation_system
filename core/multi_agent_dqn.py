import random
import math
import pickle
import os
from typing import List, Dict
from database.connection import DatabaseConnection
from core.dqn_agent import DQNAgent
from core.neural_network import NeuralNetwork
from config import STATE_DIM, ACTION_DIM


class MultiAgentDQN:
    """Multi-agent DQN с отдельными агентами для разных типов организаций"""

    def __init__(self):
        self.db = DatabaseConnection()
        self.agents = {}
        self._load_agents()

    def _load_agents(self):
        """Загрузка или создание агентов для каждого типа организации"""
        industry_types = ['education', 'it', 'manufacturing', 'finance', 'healthcare', 'retail', 'government']

        for industry in industry_types:
            model_path = f'models/dqn_agent_{industry}.pkl'

            if os.path.exists(model_path):
                agent = DQNAgent(STATE_DIM, ACTION_DIM, {})
                agent.load(model_path)
                self.agents[industry] = agent
            else:
                # Создаём нового агента с параметрами, оптимизированными для отрасли
                params = self._get_industry_params(industry)
                self.agents[industry] = DQNAgent(STATE_DIM, ACTION_DIM, params)

    def _get_industry_params(self, industry: str) -> dict:
        """Получение параметров агента в зависимости от отрасли"""
        params_base = {
            'LEARNING_RATE': 0.001,
            'GAMMA_DQN': 0.95,
            'BUFFER_SIZE': 100000,
            'BATCH_SIZE': 64,
            'EPSILON_START': 1.0,
            'EPSILON_END': 0.01,
            'EPSILON_DECAY': 0.995,
            'TARGET_UPDATE_FREQ': 100
        }

        # Отраслевые корректировки
        adjustments = {
            'it': {'LEARNING_RATE': 0.0015, 'GAMMA_DQN': 0.93, 'EPSILON_DECAY': 0.99},
            'finance': {'LEARNING_RATE': 0.0008, 'GAMMA_DQN': 0.97, 'EPSILON_DECAY': 0.998},
            'manufacturing': {'LEARNING_RATE': 0.0005, 'GAMMA_DQN': 0.98, 'EPSILON_DECAY': 0.999},
            'education': {'LEARNING_RATE': 0.001, 'GAMMA_DQN': 0.95, 'EPSILON_DECAY': 0.995},
            'healthcare': {'LEARNING_RATE': 0.0007, 'GAMMA_DQN': 0.96, 'EPSILON_DECAY': 0.997},
            'retail': {'LEARNING_RATE': 0.0012, 'GAMMA_DQN': 0.94, 'EPSILON_DECAY': 0.992},
            'government': {'LEARNING_RATE': 0.0003, 'GAMMA_DQN': 0.99, 'EPSILON_DECAY': 0.9995}
        }

        if industry in adjustments:
            params_base.update(adjustments[industry])

        return params_base

    def get_agent(self, industry: str) -> DQNAgent:
        """Получение агента для конкретной отрасли"""
        if industry not in self.agents:
            self.agents[industry] = self._create_agent(industry)
        return self.agents[industry]

    def _create_agent(self, industry: str) -> DQNAgent:
        """Создание нового агента для отрасли"""
        params = self._get_industry_params(industry)
        return DQNAgent(STATE_DIM, ACTION_DIM, params)

    def act(self, state: List[float], industry: str, training: bool = False) -> int:
        """Выбор действия специализированным агентом"""
        agent = self.get_agent(industry)
        return agent.act(state, training)

    def learn(self, industry: str):
        """Обучение специализированного агента"""
        agent = self.get_agent(industry)
        agent.learn()

    def remember(self, industry: str, state: List[float], action: int,
                 reward: float, next_state: List[float], done: bool):
        """Сохранение опыта для специализированного агента"""
        agent = self.get_agent(industry)
        agent.remember(state, action, reward, next_state, done)

    def save_all(self):
        """Сохранение всех агентов"""
        for industry, agent in self.agents.items():
            model_path = f'models/dqn_agent_{industry}.pkl'
            agent.save(model_path)

    def train_on_industry_data(self, industry: str, num_episodes: int = 100):
        """Обучение агента на данных конкретной отрасли"""
        from core.environment import DigitalTransformationEnvironment

        agent = self.get_agent(industry)

        # Получаем реальные данные организаций этой отрасли
        orgs = self.db.query(
            "SELECT id FROM organizations WHERE industry = ?",
            (industry,)
        )

        for episode in range(num_episodes):
            # Инициализация среды на основе реальных данных
            if orgs and len(orgs) > 0:
                org_id = random.choice(orgs)['id']
                assessment = self.db.query_one(
                    "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
                    (org_id,)
                )
                if assessment:
                    initial_scores = self._get_scores_from_assessment(assessment['id'])
                else:
                    initial_scores = None
            else:
                initial_scores = None

            env = DigitalTransformationEnvironment(initial_scores, 0.5, industry)
            state = env.reset()
            total_reward = 0

            for step in range(50):
                action = agent.act(state, training=True)
                next_state, reward, done, _ = env.step(action)
                agent.remember(state, action, reward, next_state, done)
                agent.learn()
                state = next_state
                total_reward += reward
                if done:
                    break

            if (episode + 1) % 10 == 0:
                print(f"[Multi-Agent] {industry}: Episode {episode + 1}, Reward: {total_reward:.2f}")

        self.save_all()

    def _get_scores_from_assessment(self, assessment_id: int) -> dict:
        """Получение оценок из БД по assessment_id"""
        details = self.db.query(
            "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
            (assessment_id,)
        )
        return {d['indicator_code']: d['value'] for d in details}
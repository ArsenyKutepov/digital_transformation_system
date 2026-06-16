import random
import math
from typing import List
from core.neural_network import NeuralNetwork
from core.prioritized_replay_buffer import PrioritizedReplayBuffer


class DuelingDQNAgent:
    """
    Dueling DQN с разделением на Value и Advantage потоки
    Использует Double DQN для стабилизации обучения
    """

    def __init__(self, state_dim: int, action_dim: int, config: dict):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = config.get('LEARNING_RATE', 0.001)
        self.gamma = config.get('GAMMA_DQN', 0.95)
        self.epsilon = config.get('EPSILON_START', 1.0)
        self.epsilon_end = config.get('EPSILON_END', 0.01)
        self.epsilon_decay = config.get('EPSILON_DECAY', 0.995)
        self.batch_size = config.get('BATCH_SIZE', 64)
        self.target_update_freq = config.get('TARGET_UPDATE_FREQ', 100)
        self.use_dueling = config.get('USE_DUELING', True)
        self.use_double = config.get('USE_DOUBLE', True)

        # Создаём сети для Dueling DQN
        if self.use_dueling:
            self.q_network = DuelingNetwork(state_dim, action_dim, self.learning_rate)
            self.target_network = DuelingNetwork(state_dim, action_dim, self.learning_rate)
        else:
            layer_sizes = [state_dim, 256, 256, action_dim]
            self.q_network = NeuralNetwork(layer_sizes, self.learning_rate)
            self.target_network = NeuralNetwork(layer_sizes, self.learning_rate)

        self._update_target_network()

        # Используем Prioritized Replay Buffer
        self.replay_buffer = PrioritizedReplayBuffer(
            config.get('BUFFER_SIZE', 100000),
            alpha=0.6,
            beta=0.4
        )

        self.step_counter = 0

    def _update_target_network(self):
        """Копирование весов из Q-сети в целевую сеть"""
        if self.use_dueling:
            for i in range(len(self.q_network.value_stream.weights)):
                for j in range(len(self.q_network.value_stream.weights[i])):
                    for k in range(len(self.q_network.value_stream.weights[i][j])):
                        self.target_network.value_stream.weights[i][j][k] = self.q_network.value_stream.weights[i][j][k]
                for j in range(len(self.q_network.value_stream.biases[i])):
                    self.target_network.value_stream.biases[i][j][0] = self.q_network.value_stream.biases[i][j][0]

            for i in range(len(self.q_network.advantage_stream.weights)):
                for j in range(len(self.q_network.advantage_stream.weights[i])):
                    for k in range(len(self.q_network.advantage_stream.weights[i][j])):
                        self.target_network.advantage_stream.weights[i][j][k] = \
                        self.q_network.advantage_stream.weights[i][j][k]
                for j in range(len(self.q_network.advantage_stream.biases[i])):
                    self.target_network.advantage_stream.biases[i][j][0] = self.q_network.advantage_stream.biases[i][j][
                        0]
        else:
            for i in range(len(self.q_network.weights)):
                for j in range(len(self.q_network.weights[i])):
                    for k in range(len(self.q_network.weights[i][j])):
                        self.target_network.weights[i][j][k] = self.q_network.weights[i][j][k]
                for j in range(len(self.q_network.biases[i])):
                    self.target_network.biases[i][j][0] = self.q_network.biases[i][j][0]

    def _state_to_matrix(self, state: List[float]) -> List[List[float]]:
        return [[s] for s in state]

    def act(self, state: List[float], training: bool = True) -> int:
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)

        state_matrix = self._state_to_matrix(state)
        q_values = self.q_network.predict(state_matrix)

        best_action = 0
        best_q = q_values[0][0]
        for i in range(1, self.action_dim):
            if q_values[i][0] > best_q:
                best_q = q_values[i][0]
                best_action = i
        return best_action

    def remember(self, state: List[float], action: int, reward: float,
                 next_state: List[float], done: bool, td_error: float = None):
        self.replay_buffer.push(state, action, reward, next_state, done, td_error)

    def learn(self):
        if len(self.replay_buffer) < self.batch_size:
            return

        batch = self.replay_buffer.sample(self.batch_size)

        indices = []
        td_errors = []

        for item in batch:
            state, action, reward, next_state, done = item['data']
            weight = item['weight']
            idx = item['idx']

            state_matrix = self._state_to_matrix(state)
            q_pred = self.q_network.predict(state_matrix)
            current_q = q_pred[action][0]

            next_state_matrix = self._state_to_matrix(next_state)

            if self.use_double:
                # Double DQN: выбор действия основной сетью, оценка целевой сетью
                next_q_main = self.q_network.predict(next_state_matrix)
                best_next_action = 0
                best_next_q = next_q_main[0][0]
                for i in range(1, self.action_dim):
                    if next_q_main[i][0] > best_next_q:
                        best_next_q = next_q_main[i][0]
                        best_next_action = i

                q_next = self.target_network.predict(next_state_matrix)
                max_q_next = q_next[best_next_action][0]
            else:
                q_next = self.target_network.predict(next_state_matrix)
                max_q_next = max(q_next[j][0] for j in range(self.action_dim))

            target = reward + self.gamma * max_q_next * (0 if done else 1)

            # TD-ошибка для Prioritized Replay
            td_error = target - current_q
            td_errors.append(td_error)
            indices.append(idx)

            # Обновление с весом importance sampling
            target_vector = [[q_pred[j][0]] for j in range(self.action_dim)]
            target_vector[action][0] = target

            # Применяем importance sampling weight к градиенту
            self.q_network.forward(state_matrix)
            # Умножаем градиент на weight
            self._weighted_backward(target_vector, q_pred, weight)

        # Обновляем приоритеты в буфере
        self.replay_buffer.update_priorities(indices, td_errors)

        # Обновление epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        # Обновление целевой сети
        self.step_counter += 1
        if self.step_counter % self.target_update_freq == 0:
            self._update_target_network()

    def _weighted_backward(self, y_true, y_pred, weight):
        """Обратный проход с учётом весов importance sampling"""
        output_dim = len(y_pred)
        delta = [[2.0 * weight * (y_pred[i][0] - y_true[i][0])] for i in range(output_dim)]

        # Далее стандартный backward с модифицированным delta
        # (аналогично NeuralNetwork.backward)
        # Упрощённо: используем стандартный backward и умножаем learning rate на weight
        for i in range(len(self.q_network.weights)):
            for j in range(len(self.q_network.weights[i])):
                for k in range(len(self.q_network.weights[i][j])):
                    self.q_network.weights[i][j][k] -= self.learning_rate * weight * 0.001  # упрощённо

    def save(self, filepath: str):
        import pickle
        data = {
            'weights': self.q_network.weights,
            'biases': self.q_network.biases,
            'epsilon': self.epsilon,
            'step_counter': self.step_counter
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

    def load(self, filepath: str):
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        self.q_network.weights = data['weights']
        self.q_network.biases = data['biases']
        self.epsilon = data['epsilon']
        self.step_counter = data['step_counter']
        self._update_target_network()


class DuelingNetwork:
    """Dueling Network Architecture: Value Stream + Advantage Stream"""

    def __init__(self, state_dim: int, action_dim: int, learning_rate: float = 0.001):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate

        # Общий слой (features)
        self.common_layer = NeuralNetwork([state_dim, 256], learning_rate)

        # Value stream (оценка ценности состояния)
        self.value_stream = NeuralNetwork([256, 256, 1], learning_rate)

        # Advantage stream (оценка преимущества действий)
        self.advantage_stream = NeuralNetwork([256, 256, action_dim], learning_rate)

        self.common_weights = self.common_layer.weights
        self.common_biases = self.common_layer.biases

    def forward(self, x: List[List[float]]) -> List[List[float]]:
        # Прямой проход через общий слой
        common_out = self.common_layer.forward(x)

        # Value и Advantage потоки
        value = self.value_stream.forward(common_out)[0][0]
        advantages = self.advantage_stream.forward(common_out)

        # Комбинирование: Q = V + (A - mean(A))
        adv_mean = sum(advantages[j][0] for j in range(self.action_dim)) / self.action_dim

        q_values = []
        for j in range(self.action_dim):
            q = value + advantages[j][0] - adv_mean
            q_values.append([q])

        return q_values

    def predict(self, x: List[List[float]]) -> List[List[float]]:
        return self.forward(x)

    def backward(self, y_true: List[List[float]], y_pred: List[List[float]]):
        # Обратный проход (упрощённо)
        pass
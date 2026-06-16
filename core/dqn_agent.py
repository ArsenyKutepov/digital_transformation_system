import random
import math
from typing import List, Tuple
from .neural_network import NeuralNetwork, ReplayBuffer, Matrix


class DQNAgent:
    """Deep Q-Network агент"""

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

        layer_sizes = [state_dim, 256, 256, action_dim]
        self.q_network = NeuralNetwork(layer_sizes, self.learning_rate)
        self.target_network = NeuralNetwork(layer_sizes, self.learning_rate)
        self._update_target_network()

        self.replay_buffer = ReplayBuffer(config.get('BUFFER_SIZE', 100000))
        self.step_counter = 0

    def _update_target_network(self):
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
                 next_state: List[float], done: bool):
        self.replay_buffer.push(state, action, reward, next_state, done)

    def learn(self):
        if len(self.replay_buffer) < self.batch_size:
            return

        batch = self.replay_buffer.sample(self.batch_size)

        for state, action, reward, next_state, done in batch:
            state_matrix = self._state_to_matrix(state)
            q_pred = self.q_network.predict(state_matrix)
            current_q = q_pred[action][0]

            next_state_matrix = self._state_to_matrix(next_state)
            q_next = self.target_network.predict(next_state_matrix)
            max_q_next = max(q_next[j][0] for j in range(self.action_dim))

            target = reward + self.gamma * max_q_next * (0 if done else 1)

            target_vector = [[q_pred[j][0]] for j in range(self.action_dim)]
            target_vector[action][0] = target

            self.q_network.forward(state_matrix)
            self.q_network.backward(target_vector, q_pred)

        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        self.step_counter += 1
        if self.step_counter % self.target_update_freq == 0:
            self._update_target_network()

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

    def plan_sequence(self, env, max_steps: int = 50) -> List[dict]:
        """Построение последовательности действий для заданной среды"""
        state = env.reset()
        actions_sequence = []

        for _ in range(max_steps):
            action_idx = self.act(state, training=False)
            action = env.get_actions()[action_idx]
            actions_sequence.append(action)
            state, _, done, _ = env.step(action_idx)
            if done:
                break

        return actions_sequence
import math
import random
from typing import List


class Matrix:
    """Простая реализация матричных операций"""

    @staticmethod
    def zeros(rows: int, cols: int) -> List[List[float]]:
        return [[0.0 for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def random(rows: int, cols: int, seed: int = None) -> List[List[float]]:
        if seed is not None:
            random.seed(seed)
        return [[random.uniform(-0.1, 0.1) for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        if not a or not b:
            return []
        rows_a, cols_a = len(a), len(a[0])
        rows_b, cols_b = len(b), len(b[0])

        if cols_a != rows_b:
            raise ValueError(f"Несовместимые размеры: {cols_a} != {rows_b}")

        result = Matrix.zeros(rows_a, cols_b)
        for i in range(rows_a):
            for j in range(cols_b):
                s = 0.0
                for k in range(cols_a):
                    s += a[i][k] * b[k][j]
                result[i][j] = s
        return result

    @staticmethod
    def add(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            raise ValueError("Размеры матриц не совпадают")
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    @staticmethod
    def subtract(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            raise ValueError("Размеры матриц не совпадают")
        return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    @staticmethod
    def transpose(a: List[List[float]]) -> List[List[float]]:
        if not a:
            return []
        return [[a[j][i] for j in range(len(a))] for i in range(len(a[0]))]

    @staticmethod
    def scalar_multiply(scalar: float, a: List[List[float]]) -> List[List[float]]:
        return [[scalar * a[i][j] for j in range(len(a[0]))] for i in range(len(a))]


class NeuralNetwork:
    """Многослойный перцептрон с нуля"""

    def __init__(self, layer_sizes: List[int], learning_rate: float = 0.001):
        self.layer_sizes = layer_sizes
        self.learning_rate = learning_rate

        # Инициализация весов и смещений (Xavier)
        self.weights = []
        self.biases = []

        for i in range(len(layer_sizes) - 1):
            fan_in = layer_sizes[i]
            fan_out = layer_sizes[i + 1]
            limit = math.sqrt(6.0 / (fan_in + fan_out))

            w = [[random.uniform(-limit, limit) for _ in range(fan_in)] for _ in range(fan_out)]
            b = [[0.0] for _ in range(fan_out)]

            self.weights.append(w)
            self.biases.append(b)

        self.activations = []
        self.z_values = []

    def _relu(self, x: float) -> float:
        return max(0.0, x)

    def _relu_derivative(self, x: float) -> float:
        return 1.0 if x > 0 else 0.0

    def _linear(self, x: float) -> float:
        return x

    def _linear_derivative(self, x: float) -> float:
        return 1.0

    def forward(self, x: List[List[float]]) -> List[List[float]]:
        self.activations = [x]
        self.z_values = []

        current = x

        for i, (w, b) in enumerate(zip(self.weights[:-1], self.biases[:-1])):
            z = Matrix.multiply(w, current)
            z = Matrix.add(z, b)
            self.z_values.append(z)
            a = [[self._relu(z[j][0])] for j in range(len(z))]
            self.activations.append(a)
            current = a

        w_out, b_out = self.weights[-1], self.biases[-1]
        z_out = Matrix.multiply(w_out, current)
        z_out = Matrix.add(z_out, b_out)
        self.z_values.append(z_out)
        a_out = [[self._linear(z_out[j][0])] for j in range(len(z_out))]
        self.activations.append(a_out)

        return a_out

    def backward(self, y_true: List[List[float]], y_pred: List[List[float]]):
        output_dim = len(y_pred)
        delta = [[2.0 * (y_pred[i][0] - y_true[i][0])] for i in range(output_dim)]

        dW = [None] * len(self.weights)
        db = [None] * len(self.biases)

        for i in reversed(range(len(self.weights))):
            db[i] = delta

            a_prev = self.activations[i]
            dW_i = []
            for d in delta:
                row = [d[0] * a_prev[j][0] for j in range(len(a_prev))]
                dW_i.append(row)
            dW[i] = dW_i

            if i > 0:
                w_T = Matrix.transpose(self.weights[i])
                delta_next = Matrix.multiply(w_T, delta)
                z_prev = self.z_values[i - 1]
                for k in range(len(delta_next)):
                    delta_next[k][0] *= self._relu_derivative(z_prev[k][0])
                delta = delta_next

        # Обновление весов
        for i in range(len(self.weights)):
            for j in range(len(self.weights[i])):
                for k in range(len(self.weights[i][j])):
                    self.weights[i][j][k] -= self.learning_rate * dW[i][j][k]
            for j in range(len(self.biases[i])):
                self.biases[i][j][0] -= self.learning_rate * db[i][j][0]

    def predict(self, x: List[List[float]]) -> List[List[float]]:
        current = x
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = Matrix.multiply(w, current)
            z = Matrix.add(z, b)
            if i == len(self.weights) - 1:
                current = [[self._linear(z[j][0])] for j in range(len(z))]
            else:
                current = [[self._relu(z[j][0])] for j in range(len(z))]
        return current

    def get_weights(self):
        return self.weights, self.biases

    def set_weights(self, weights, biases):
        self.weights = weights
        self.biases = biases


class ReplayBuffer:
    """Буфер воспроизведения опыта"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (list(state), action, reward, list(next_state), done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int):
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)
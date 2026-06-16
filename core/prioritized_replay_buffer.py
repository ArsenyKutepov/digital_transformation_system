import random
import numpy as np


class SumTree:
    """Дерево сумм для эффективного приоритетного сэмплирования"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.size = 0
        self.tree = np.zeros(2 * capacity - 1)
        self.data = [None] * capacity
        self.write = 0

    def _propagate(self, idx: int, change: float):
        """Обновление дерева снизу вверх"""
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx: int, s: float) -> int:
        """Поиск индекса листа по кумулятивной сумме"""
        left = 2 * idx + 1
        right = left + 1

        if left >= len(self.tree):
            return idx

        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])

    def total(self) -> float:
        """Общая сумма приоритетов"""
        return self.tree[0]

    def add(self, priority: float, data):
        """Добавление элемента с приоритетом"""
        idx = self.write + self.capacity - 1
        self.data[self.write] = data
        self.update(idx, priority)
        self.write += 1
        if self.write >= self.capacity:
            self.write = 0
        if self.size < self.capacity:
            self.size += 1

    def update(self, idx: int, priority: float):
        """Обновление приоритета"""
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)

    def get(self, s: float) -> tuple:
        """Получение элемента по кумулятивной сумме"""
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return idx, self.tree[idx], self.data[data_idx]


class PrioritizedReplayBuffer:
    """Буфер воспроизведения с приоритетной выборкой (PER)"""

    def __init__(self, capacity: int, alpha: float = 0.6, beta: float = 0.4):
        """
        capacity: максимальный размер буфера
        alpha: степень использования приоритетов (0 - равномерная, 1 - полная приоритизация)
        beta: степень коррекции смещения (увеличивается со временем)
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = 0.001
        self.tree = SumTree(capacity)
        self.epsilon = 0.01

    def _get_priority(self, error: float) -> float:
        """Расчёт приоритета на основе ошибки TD"""
        return (abs(error) + self.epsilon) ** self.alpha

    def push(self, state, action, reward, next_state, done, td_error: float = None):
        """Добавление перехода в буфер"""
        if td_error is None:
            priority = 1.0
        else:
            priority = self._get_priority(td_error)

        data = (list(state), action, reward, list(next_state), done)
        self.tree.add(priority, data)

    def sample(self, batch_size: int) -> list:
        """Выборка батча с приоритетами"""
        batch = []
        segment = self.tree.total() / batch_size

        for i in range(batch_size):
            a = segment * i
            b = segment * (i + 1)
            s = random.uniform(a, b)
            idx, priority, data = self.tree.get(s)

            # Вес для коррекции смещения
            prob = priority / self.tree.total()
            weight = (prob * self.capacity) ** (-self.beta)

            batch.append({
                'data': data,
                'idx': idx,
                'weight': weight,
                'td_error': (priority ** (1 / self.alpha) - self.epsilon) if self.alpha > 0 else 0
            })

        # Увеличиваем beta
        self.beta = min(1.0, self.beta + self.beta_increment)

        return batch

    def update_priorities(self, indices: list, td_errors: list):
        """Обновление приоритетов на основе новых TD-ошибок"""
        for idx, td_error in zip(indices, td_errors):
            priority = self._get_priority(td_error)
            self.tree.update(idx, priority)

    def __len__(self) -> int:
        return self.tree.size
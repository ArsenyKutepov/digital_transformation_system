import math
from config import ALPHA, BETA, GAMMA, DELTA, KAPPA, LAMBDA, ORGANIZATION_TYPES


class DynamicsModel:
    """Модель динамики организационной инерции и когнитивной нагрузки"""

    def __init__(self, organization_type: str = "average"):
        params = ORGANIZATION_TYPES.get(organization_type, ORGANIZATION_TYPES['average'])

        self.alpha = params['alpha']
        self.beta = params['beta']
        self.gamma = params['gamma']
        self.delta = params['delta']
        self.kappa = params['kappa']
        self.lambda_ = params['lambda']
        self.initial_inertia = params['initial_inertia']
        self.initial_cognitive_load = params['initial_cognitive_load']

    def update_inertia(self, current_inertia: float, tempo: float, inertia_shock: float) -> float:
        """
        Обновление организационной инерции
        dI/dt = -alpha * I + beta * tempo + shock
        """
        dt = 1.0
        dI = -self.alpha * current_inertia + self.beta * tempo + inertia_shock
        new_inertia = current_inertia + dI * dt
        return max(0.0, min(1.0, new_inertia))

    def update_cognitive_load(self, current_load: float, cognitive_demand: float, inertia: float) -> float:
        """
        Обновление когнитивной нагрузки
        dC/dt = -gamma * C + demand - delta * (1 - I)
        """
        dt = 1.0
        accelerated_learning = self.delta * (1.0 - inertia)
        dC = -self.gamma * current_load + cognitive_demand - accelerated_learning
        new_load = current_load + dC * dt
        return max(0.0, min(1.0, new_load))

    def efficiency_modifier(self, inertia: float, cognitive_load: float) -> float:
        """Модификатор эффективности действий"""
        inert_factor = math.exp(-self.kappa * inertia)
        cognit_factor = math.exp(-self.lambda_ * cognitive_load)
        return inert_factor * cognit_factor
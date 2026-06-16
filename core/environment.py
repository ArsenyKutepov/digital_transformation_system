import random
import math
from typing import List, Dict, Tuple
from config import MAX_STEPS_PER_EPISODE, W_Z, W_R, W_I, W_C, W_RISK, KAPPA, LAMBDA
from .fuzzy_logic import DigitalMaturityFuzzyModel
from .dynamics import DynamicsModel
from database.models import Action


class DigitalTransformationEnvironment:
    """Среда MDP для цифровой трансформации"""

    def __init__(self, initial_maturity_scores: Dict[str, int] = None,
                 initial_resources: float = 0.5,
                 organization_type: str = "average"):

        self.fuzzy_model = DigitalMaturityFuzzyModel()
        self.dynamics = DynamicsModel(organization_type)

        self.indicator_codes = [
            '1.1', '1.2', '1.3', '2.1', '2.2', '2.3', '3.1', '3.2', '3.3',
            '4.1', '4.2', '4.3', '5.1', '5.2', '5.3', '6.1', '6.2',
            '7.1', '7.2', '7.3', '8.1', '8.2', '8.3', '9.1', '9.2'
        ]

        if initial_maturity_scores:
            self.maturity_scores = initial_maturity_scores.copy()
        else:
            self.maturity_scores = {code: random.randint(0, 2) for code in self.indicator_codes}

        self.resources = initial_resources
        self.inertia = self.dynamics.initial_inertia
        self.cognitive_load = self.dynamics.initial_cognitive_load
        self.current_step = 0
        self.max_steps = MAX_STEPS_PER_EPISODE

        self.actions = Action.get_all()
        if not self.actions:
            Action.initialize_default_actions()
            self.actions = Action.get_all()

    def _get_state_vector(self) -> List[float]:
        state = []
        for code in self.indicator_codes:
            state.append(self.maturity_scores[code] / 3.0)
        state.append(self.resources)
        state.append(self.inertia)
        state.append(self.cognitive_load)
        return state

    def _compute_aggregated_maturity(self) -> float:
        result = self.fuzzy_model.evaluate(self.maturity_scores)
        return result['final_score'] / 100.0

    def _compute_reward(self, action: Dict, effective_growth: float) -> float:
        reward = W_Z * effective_growth
        reward -= W_R * action.get('cost', 0.1)
        reward -= W_I * self.inertia
        reward -= W_C * self.cognitive_load
        reward -= W_RISK * action.get('risk', 0.1)
        return reward

    def step(self, action_idx: int) -> Tuple[List[float], float, bool, Dict]:
        action = self.actions[action_idx]

        efficiency = math.exp(-KAPPA * self.inertia) * math.exp(-LAMBDA * self.cognitive_load)
        effective_growth = action.get('base_growth', 0.1) * efficiency

        affected_count = min(3, len(self.indicator_codes))
        affected_indicators = random.sample(self.indicator_codes, affected_count)
        for code in affected_indicators:
            current_val = self.maturity_scores[code]
            increment = effective_growth * random.uniform(0.5, 1.5)
            new_val = min(3.0, current_val + increment)
            self.maturity_scores[code] = new_val

        self.resources -= action.get('cost', 0.1)
        if self.resources < 0:
            self.resources = 0

        tempo = 1.0
        self.inertia = self.dynamics.update_inertia(
            self.inertia, tempo, action.get('inertia_shock', 0.15)
        )
        self.cognitive_load = self.dynamics.update_cognitive_load(
            self.cognitive_load, action.get('cognitive_load', 0.15), self.inertia
        )

        reward = self._compute_reward(action, effective_growth)

        self.current_step += 1
        done = (self.current_step >= self.max_steps) or (self.resources <= 0.05)

        info = {
            'action_name': action.get('name', f'Action_{action_idx}'),
            'effective_growth': effective_growth,
            'maturity': self._compute_aggregated_maturity(),
            'resources': self.resources,
            'inertia': self.inertia,
            'cognitive_load': self.cognitive_load
        }

        return self._get_state_vector(), reward, done, info

    def reset(self) -> List[float]:
        self.maturity_scores = {code: random.randint(0, 2) for code in self.indicator_codes}
        self.resources = random.uniform(0.3, 0.8)
        self.inertia = self.dynamics.initial_inertia
        self.cognitive_load = self.dynamics.initial_cognitive_load
        self.current_step = 0
        return self._get_state_vector()

    def get_state_dim(self) -> int:
        return len(self._get_state_vector())

    def get_action_dim(self) -> int:
        return len(self.actions)

    def get_actions(self):
        return self.actions
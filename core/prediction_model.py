import json
import numpy as np
from datetime import datetime, timedelta
from database.connection import DatabaseConnection


class PredictionModel:
    """Модель прогнозирования цифровой зрелости"""

    def __init__(self):
        self.db = DatabaseConnection()

    def predict_future_scores(self, org_id: int, horizons_months: list = None) -> dict:
        if horizons_months is None:
            horizons_months = [3, 6, 12]

        assessments = self.db.query("SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date", (org_id,))

        if len(assessments) < 2:
            return self._get_default_prediction(org_id, horizons_months)

        dates = []
        scores = []
        for a in assessments:
            date_obj = datetime.strptime(a['assessment_date'], '%Y-%m-%d %H:%M:%S')
            dates.append(date_obj)
            scores.append(a['final_score'])

        base_date = dates[0]
        x_days = [(d - base_date).days for d in dates]

        # Простая линейная регрессия (без numpy при ошибках)
        try:
            import numpy as np
            coeffs = np.polyfit(x_days, scores, 1)
            slope = coeffs[0]
            intercept = coeffs[1]
        except:
            # Если numpy не работает, используем простую аппроксимацию
            if len(x_days) > 1:
                slope = (scores[-1] - scores[0]) / (x_days[-1] - x_days[0]) if x_days[-1] != x_days[0] else 0
            else:
                slope = 0
            intercept = scores[0] - slope * x_days[0]

        last_score = scores[-1]
        last_date = dates[-1]

        predictions = []
        for months in horizons_months:
            days_ahead = months * 30
            linear_pred = intercept + slope * (x_days[-1] + days_ahead)
            linear_pred = max(0, min(100, linear_pred))

            # Простой прогноз с затуханием роста
            exp_growth_rate = 0.02
            if len(scores) > 1:
                exp_growth_rate = max(0.005,
                                      min(0.1, (scores[-1] - scores[-2]) / scores[-2] if scores[-2] > 0 else 0.02))
            exp_pred = last_score * (1 + exp_growth_rate * months)
            exp_pred = max(0, min(100, exp_pred))

            final_pred = (linear_pred + exp_pred) / 2
            std_dev = np.std(scores) if 'np' in dir() else 5
            confidence_lower = max(0, final_pred - 1.96 * std_dev)
            confidence_upper = min(100, final_pred + 1.96 * std_dev)

            predictions.append({
                'horizon_months': months,
                'predicted_score': round(final_pred, 1),
                'confidence_lower': round(confidence_lower, 1),
                'confidence_upper': round(confidence_upper, 1),
                'target_date': (last_date + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            })

            self.db.execute(
                "INSERT INTO predictions (org_id, horizon_months, predicted_score, confidence_lower, confidence_upper, model_version) VALUES (?, ?, ?, ?, ?, ?)",
                (org_id, months, final_pred, confidence_lower, confidence_upper, '1.0'))

        return {'org_id': org_id, 'current_score': last_score, 'predictions': predictions,
                'trend': 'increasing' if slope > 0 else 'decreasing', 'slope': round(slope, 2)}

    def _get_default_prediction(self, org_id: int, horizons_months: list) -> dict:
        """Прогноз по умолчанию при недостатке данных"""
        assessment = self.db.query_one(
            "SELECT final_score FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )
        current_score = assessment['final_score'] if assessment else 50

        predictions = []
        for months in horizons_months:
            predicted = min(100, current_score + months * 2)
            predictions.append({
                'horizon_months': months,
                'predicted_score': round(predicted, 1),
                'confidence_lower': round(predicted - 10, 1),
                'confidence_upper': round(min(100, predicted + 10), 1),
                'target_date': (datetime.now() + timedelta(days=months * 30)).strftime('%Y-%m-%d')
            })

        return {
            'org_id': org_id,
            'current_score': current_score,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'predictions': predictions,
            'trend': 'unknown',
            'slope': 0
        }

    def _get_settings(self):
        settings = self.db.query("SELECT setting_key, setting_value FROM system_settings")
        return {s['setting_key']: s['setting_value'] for s in settings}
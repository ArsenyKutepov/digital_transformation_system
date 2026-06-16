import json
from database.connection import DatabaseConnection


class RiskHeatmap:
    """Тепловая карта рисков по блокам и факторам"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_risk_heatmap_data(self, org_id: int) -> dict:
        """Получение данных для тепловой карты рисков"""
        # Получаем последнюю оценку
        assessment = self.db.query_one(
            "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )

        if not assessment:
            return {}

        # Получаем детали оценки
        details = self.db.query(
            "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
            (assessment['id'],)
        )

        # Группируем по блокам
        block_map = {
            '1.1': 1, '1.2': 1, '1.3': 1,
            '2.1': 2, '2.2': 2, '2.3': 2,
            '3.1': 3, '3.2': 3, '3.3': 3,
            '4.1': 4, '4.2': 4, '4.3': 4,
            '5.1': 5, '5.2': 5, '5.3': 5,
            '6.1': 6, '6.2': 6,
            '7.1': 7, '7.2': 7, '7.3': 7,
            '8.1': 8, '8.2': 8, '8.3': 8,
            '9.1': 9, '9.2': 9
        }

        block_names = {
            1: 'Личностный', 2: 'Компетенции', 3: 'Культура',
            4: 'Процессы', 5: 'Продукты', 6: 'Модели',
            7: 'Данные', 8: 'Инфраструктура', 9: 'Глобальная'
        }

        # Собираем значения по блокам
        block_values = {i: [] for i in range(1, 10)}
        for d in details:
            block_id = block_map.get(d['indicator_code'], 1)
            block_values[block_id].append(d['value'])

        # Вычисляем риск для каждого блока (0-3, где 0 - низкий риск, 3 - высокий)
        block_risks = {}
        for block_id in range(1, 10):
            if block_values[block_id]:
                avg = sum(block_values[block_id]) / len(block_values[block_id])
                # Чем ниже оценка, тем выше риск
                risk = 3 - avg
                block_risks[block_id] = {
                    'name': block_names[block_id],
                    'value': round(avg, 1),
                    'risk': round(risk, 1),
                    'risk_level': self._get_risk_level(risk),
                    'risk_color': self._get_risk_color(risk)
                }
            else:
                block_risks[block_id] = {
                    'name': block_names[block_id],
                    'value': 0,
                    'risk': 3.0,
                    'risk_level': 'high',
                    'risk_color': '#EF4444'
                }

        # Риски по факторам
        factors_risk = {
            'technical': {
                'value': assessment['technical_factor'],
                'risk': 100 - assessment['technical_factor'],
                'risk_level': self._get_risk_level((100 - assessment['technical_factor']) / 100)
            },
            'cognitive': {
                'value': assessment['cognitive_factor'],
                'risk': 100 - assessment['cognitive_factor'],
                'risk_level': self._get_risk_level((100 - assessment['cognitive_factor']) / 100)
            },
            'personal': {
                'value': assessment['personal_factor'],
                'risk': 100 - assessment['personal_factor'],
                'risk_level': self._get_risk_level((100 - assessment['personal_factor']) / 100)
            }
        }

        return {
            'org_id': org_id,
            'final_score': assessment['final_score'],
            'blocks': block_risks,
            'factors': factors_risk,
            'overall_risk': 100 - assessment['final_score'],
            'overall_risk_level': self._get_risk_level((100 - assessment['final_score']) / 100)
        }

    def _get_risk_level(self, risk: float) -> str:
        """Определение уровня риска"""
        if risk <= 1.0:
            return 'low'
        elif risk <= 2.0:
            return 'medium'
        else:
            return 'high'

    def _get_risk_color(self, risk: float) -> str:
        """Определение цвета риска"""
        if risk <= 1.0:
            return '#10B981'  # зелёный
        elif risk <= 2.0:
            return '#F59E0B'  # жёлтый
        else:
            return '#EF4444'  # красный

    def generate_heatmap_html(self, org_id: int) -> str:
        """Генерация HTML тепловой карты рисков"""
        data = self.get_risk_heatmap_data(org_id)

        if not data:
            return '<p>Нет данных для отображения тепловой карты</p>'

        blocks_html = ''
        for block_id in range(1, 10):
            block = data['blocks'].get(block_id, {})
            risk_color = block.get('risk_color', '#E2E8F0')
            risk_level = block.get('risk_level', 'unknown')
            risk_text = 'Низкий' if risk_level == 'low' else 'Средний' if risk_level == 'medium' else 'Высокий'

            blocks_html += f'''
            <div style="text-align: center;">
                <div style="width: 80px; height: 80px; background: {risk_color}; border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto;">
                    <span style="font-size: 20px; font-weight: bold; color: white;">{block.get('value', 0):.1f}</span>
                    <span style="font-size: 10px; color: white;">из 3</span>
                </div>
                <div style="margin-top: 8px; font-size: 12px; font-weight: 500;">{block.get('name', '')}</div>
                <div style="font-size: 10px; color: {risk_color};">Риск: {risk_text}</div>
            </div>
            '''

        factors_html = ''
        for factor, fdata in data['factors'].items():
            factor_names = {'technical': 'Технический', 'cognitive': 'Когнитивный', 'personal': 'Личностный'}
            risk_color = self._get_risk_color(fdata['risk'] / 100)

            factors_html += f'''
            <div style="text-align: center;">
                <div style="width: 100px; padding: 12px; background: {risk_color}; border-radius: 12px;">
                    <div style="font-size: 24px; font-weight: bold; color: white;">{fdata['value']:.0f}</div>
                    <div style="font-size: 11px; color: white;">{factor_names.get(factor, factor)}</div>
                </div>
            </div>
            '''

        overall_risk_color = self._get_risk_color(data['overall_risk'] / 100)

        html = f'''
        <div class="risk-heatmap">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="display: inline-block; width: 120px; padding: 15px; background: {overall_risk_color}; border-radius: 16px;">
                    <div style="font-size: 28px; font-weight: bold; color: white;">{data['overall_risk']:.0f}</div>
                    <div style="font-size: 12px; color: white;">Общий риск %</div>
                </div>
            </div>

            <div style="margin-bottom: 25px;">
                <h3 style="margin-bottom: 15px; font-size: 16px;">Факторы риска</h3>
                <div style="display: flex; justify-content: space-around; gap: 15px;">
                    {factors_html}
                </div>
            </div>

            <h3 style="margin-bottom: 15px; font-size: 16px;">Риски по блокам</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                {blocks_html}
            </div>

            <div style="margin-top: 20px; padding: 12px; background: #F1F5F9; border-radius: 12px;">
                <div style="display: flex; justify-content: center; gap: 20px; font-size: 12px;">
                    <div><span style="display: inline-block; width: 12px; height: 12px; background: #10B981; border-radius: 2px; margin-right: 5px;"></span> Низкий риск</div>
                    <div><span style="display: inline-block; width: 12px; height: 12px; background: #F59E0B; border-radius: 2px; margin-right: 5px;"></span> Средний риск</div>
                    <div><span style="display: inline-block; width: 12px; height: 12px; background: #EF4444; border-radius: 2px; margin-right: 5px;"></span> Высокий риск</div>
                </div>
            </div>
        </div>
        '''

        return html
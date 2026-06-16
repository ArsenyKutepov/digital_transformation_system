"""
Модель оценки цифровой зрелости на основе нечёткой логики
Реализация по правилам из НИЛ-27 (минимизация картами Карно)
"""

from typing import Dict, List, Tuple


class DigitalMaturityModel:
    """Модель цифровой зрелости с логическими правилами из НИЛ-27"""

    def __init__(self):
        # Маппинг кодов показателей к ключам xij
        self.indicator_keys = {
            '1.1': 'x11', '1.2': 'x12', '1.3': 'x13',
            '2.1': 'x21', '2.2': 'x22', '2.3': 'x23',
            '3.1': 'x31', '3.2': 'x32', '3.3': 'x33',
            '4.1': 'x41', '4.2': 'x42', '4.3': 'x43',
            '5.1': 'x51', '5.2': 'x52', '5.3': 'x53',
            '6.1': 'x61', '6.2': 'x62',
            '7.1': 'x71', '7.2': 'x72', '7.3': 'x73',
            '8.1': 'x81', '8.2': 'x82', '8.3': 'x83',
            '9.1': 'x91', '9.2': 'x92'
        }

        # Обратный маппинг
        self.reverse_keys = {v: k for k, v in self.indicator_keys.items()}

    def compute_block_y1(self, x11, x12, x13) -> int:
        """Блок 1: Личностный фактор"""
        if (x12 == 0 and (x11 == 0 or x13 == 0)) or (x13 == 0 and (x11 == 0 or x11 == 2)):
            return 0
        elif (x12 == 0 and (x11 == 2 or x13 == 2)) or (x11 == 1 and x13 == 1) or \
                (x12 == 1 and (x11 == 1 or x13 == 1)) or ((x12 == 2 or x12 == 3) and (x11 == 0 or x13 == 0)):
            return 1
        elif (x12 == 0 and x13 == 3) or (x11 == 2 and (x12 == 2 or x13 == 2 or (x12 == 3 and x13 == 1))) or \
                (x12 == 2 and x13 == 2) or (x11 == 1 and ((x12 == 3 and x13 == 2) or (x12 == 2 and x13 == 3))):
            return 2
        elif (x12 == 3 and (x11 == 3 or x13 == 3)) or (x11 == 3 and x13 == 3):
            return 3
        else:
            return 0

    def compute_block_y2(self, x21, x22, x23) -> int:
        """Блок 2: Компетенции"""
        if x22 == 0 and (x21 == 0 or x21 == 1):
            return 0
        elif x21 == 2 and x22 == 0 or x22 == 1 and x23 == 1 or x21 == 1 and (x22 == 1 or x22 == 2 or x23 == 1):
            return 1
        elif x22 == 1 and ((x21 != 1 and x23 == 2) or x23 == 3) or \
                x21 == 1 and x22 == 3 and (x23 == 2 or x23 == 3) or \
                x22 == 2 and (x21 == 2 or x23 == 2 or (x21 == 3 and x23 == 1)) or \
                x22 == 3 and (x21 == 2 or (x21 == 3 and x23 == 1)):
            return 2
        elif x21 == 3 and (x22 == 3 and (x23 == 2 or x23 == 3) or x22 == 2 and x23 == 3):
            return 3
        else:
            return 0

    def compute_block_y3(self, x31, x32, x33) -> int:
        """Блок 3: Организационная культура"""
        if x32 == 0 and (x31 == 0 or x33 == 0) or x31 == 0 and x32 == 1 and x33 == 0:
            return 0
        elif x31 == 1 and (x32 != 0 or (x32 == 0 and x33 != 0)) or \
                x31 == 2 and x32 == 0 or \
                x31 == 0 and x32 == 3 or \
                (x32 != 0 and x33 == 1):
            return 1
        elif x31 == 2 and x32 != 0 or \
                x31 == 3 and x32 == 0 or \
                x32 == 1 and (x33 == 2 or x33 == 3) or \
                x32 == 2 and x33 == 2:
            return 2
        elif x31 == 3 and (x32 == 3 or (x32 == 2 and x33 == 3)) or \
                x32 == 3 and x33 == 3:
            return 3
        else:
            return 0

    def compute_block_y4(self, x41, x42, x43) -> int:
        """Блок 4: Процессы"""
        if x42 == 0 and (x41 == 0 or x43 == 0):
            return 0
        elif (x42 != 0 and x43 == 0) or \
                x43 == 1 and ((x41 != 0 and x42 != 2) or x41 == 1):
            return 1
        elif x41 == 1 and x43 == 3 or \
                x42 == 2 and ((x41 != 1 and x43 == 1) or x41 == 2 and x43 == 3) or \
                x43 == 2:
            return 2
        elif x43 == 3 and (x41 == 2 and x42 == 3 or x41 == 3):
            return 3
        else:
            return 0

    def compute_block_y5(self, x51, x52, x53) -> int:
        """Блок 5: Продукты"""
        if x52 == 0 and x53 != 3:
            return 0
        elif x51 == 1 and (x52 != 0 or x53 == 3):
            return 1
        elif x51 == 2 and x53 == 2 or \
                x52 == 2 and (x51 == 2 or x51 == 3):
            return 2
        elif x52 == 3 and (x51 == 3 or (x51 == 2 and x53 == 3)):
            return 3
        else:
            return 0

    def compute_block_y6(self, x61, x62) -> int:
        """Блок 6: Модели"""
        if x62 == 0:
            return 0
        elif x62 == 1 or (x62 == 2 and x61 == 0):
            return 1
        elif (x62 == 3 and x61 != 3) or (x62 == 2 and x61 != 0):
            return 2
        elif x62 == 3 and x61 == 3:
            return 3
        else:
            return 0

    def compute_block_y7(self, x71, x72, x73) -> int:
        """Блок 7: Данные"""
        if x71 == 0 or x72 == 0:
            return 0
        elif x72 == 1 and x73 != 0 or \
                x72 == 2 and x73 == 1:
            return 1
        elif x72 == 2 and (x73 == 2 or x73 == 3) or \
                x72 == 3 and (x71 == 2 or x73 == 2):
            return 2
        elif x71 == 3 and x72 == 3 and x73 == 3:
            return 3
        else:
            return 0

    def compute_block_y8(self, x81, x82, x83) -> int:
        """Блок 8: Инфраструктура и инструменты"""
        if x82 == 0 and (x83 == 0 or x83 == 1) or x81 == 0 and x83 == 0:
            return 0
        elif x81 == 1 and (x82 == 1 or (x82 == 2 and x83 == 1)) or \
                x82 == 1 and (x83 == 1 or (x81 != 2 and x83 == 2)) or \
                (x81 != 0 and x82 != 0 and x83 == 0) or \
                x82 == 0 and x83 == 2:
            return 1
        elif x81 == 1 and x82 == 3 or \
                x81 == 2 and (x83 == 2 or (x82 == 2 and x83 != 0)) or \
                (x81 != 1 and x82 == 1 and x83 == 3) or \
                x82 == 3 and x83 == 1 or \
                x82 == 2 and (x83 == 2 or (x81 == 1 and x83 == 3) or (x81 == 3 and x83 == 1)):
            return 2
        elif x82 == 3 and ((x81 != 1 and x83 == 3) or (x81 == 3 and x83 != 1)) or \
                x81 == 3 and x82 == 2 and x83 == 3:
            return 3
        else:
            return 0

    def compute_block_y9(self, x91, x92) -> int:
        """Блок 9: Глобальная цифровая среда"""
        if x91 == 0 and x92 == 0:
            return 0
        elif x91 == 1:
            return 1
        elif x91 == 2 or (x91 == 3 and x92 != 3):
            return 2
        elif x91 == 3 and x92 == 3:
            return 3
        else:
            return 0

    def compute_intermediate_y38(self, y3, y8) -> int:
        """Промежуточный агрегатор y38"""
        if y3 == 0 or y8 == 0:
            return 0
        elif y8 == 1:
            return 1
        elif (y8 == 3 and y3 != 3) or y8 == 2:
            return 2
        elif y3 == 3 and y8 == 3:
            return 3
        else:
            return 0

    def compute_intermediate_y47(self, y4, y7) -> int:
        """Промежуточный агрегатор y47"""
        if y4 == 0 and y7 == 1 or y7 == 0:
            return 0
        elif (y4 != 0 and y7 == 1) or y7 == 2 and (y4 == 0 or y4 == 1):
            return 1
        elif (y4 != 3 and y7 == 3) or y4 == 2 and y7 != 1:
            return 2
        elif y4 == 3:
            return 3
        else:
            return 0

    def compute_intermediate_y56(self, y5, y6) -> int:
        """Промежуточный агрегатор y56"""
        if y5 == 0 and y6 == 1 or y6 == 0:
            return 0
        elif (y5 != 0 and y6 == 1) or y6 == 2 and (y5 == 0 or y5 == 1):
            return 1
        elif (y5 != 3 and y6 == 3) or y5 == 2 and y6 != 1:
            return 2
        elif y5 == 3:
            return 3
        else:
            return 0

    def compute_intermediate_y29(self, y2, y9) -> int:
        """Промежуточный агрегатор y29"""
        if y2 == 0:
            return 0
        elif y2 == 1 or (y2 == 2 and y9 == 0):
            return 1
        elif (y2 == 2 and y9 != 0) or (y2 == 3 and y9 == 1):
            return 2
        elif y2 == 3 and (y9 == 2 or y9 == 3):
            return 3
        else:
            return 0

    def compute_factor_z1(self, y38, y47) -> int:
        """Фактор Z1 (технико-технологический)"""
        if y38 == 0 or y47 == 0:
            return 0
        elif y38 == 1 and (y47 == 1 or y47 == 2):
            return 1
        elif y38 == 2 or (y38 == 1 and y47 == 3):
            return 2
        elif y38 == 3:
            return 3
        else:
            return 0

    def compute_factor_z2(self, y29, y56) -> int:
        """Фактор Z2 (когнитивный)"""
        if y29 == 0:
            return 0
        elif y29 == 1 or (y56 == 0 and y29 == 2):
            return 1
        elif (y56 != 0 and y29 == 2) or (y56 == 1 and y29 == 3):
            return 2
        elif y29 == 3 and (y56 == 2 or y56 == 3):
            return 3
        else:
            return 0

    def compute_dm_level(self, z1, z2, y1) -> int:
        """Интегральный уровень цифровой зрелости"""
        if z2 == 0 and (z1 == 0 or z1 == 1) or z2 == 0 and y1 == 0 or z1 == 0 and z2 == 1 and y1 != 3:
            return 0
        elif z1 == 0 and y1 == 3 or z1 == 1 and z2 == 1 or \
                z1 == 2 and (z2 == 0 and y1 != 0 or (z2 != 0 and y1 == 0)) or \
                z2 == 2 and y1 == 0:
            return 1
        elif y1 != 0 and (z1 != 0 and z2 == 2 or z1 == 2 and z2 == 1):
            return 2
        elif z2 == 3:
            return 3
        else:
            return 0

    def compute_dm_score(self, dm_level: int) -> int:
        """Преобразование уровня DM в баллы (0-100)"""
        # Шкала из НИЛ-27: 0->15, 1->30, 2->50, 3->85
        mapping = {0: 15, 1: 30, 2: 50, 3: 85}
        return mapping.get(dm_level, 0)

    def evaluate(self, indicator_scores: Dict[str, int]) -> Dict:
        """
        Основной метод оценки цифровой зрелости

        Args:
            indicator_scores: {код_показателя: значение 0-3}

        Returns:
            dict с результатами
        """
        # Преобразование из кодов формата '1.1' в 'x11'
        indicators = {}
        for code, value in indicator_scores.items():
            if code in self.indicator_keys:
                indicators[self.indicator_keys[code]] = value
            else:
                # Если уже в формате x11
                indicators[code] = value

        # Вычисление блоков
        y1 = self.compute_block_y1(
            indicators.get('x11', 0), indicators.get('x12', 0), indicators.get('x13', 0)
        )
        y2 = self.compute_block_y2(
            indicators.get('x21', 0), indicators.get('x22', 0), indicators.get('x23', 0)
        )
        y3 = self.compute_block_y3(
            indicators.get('x31', 0), indicators.get('x32', 0), indicators.get('x33', 0)
        )
        y4 = self.compute_block_y4(
            indicators.get('x41', 0), indicators.get('x42', 0), indicators.get('x43', 0)
        )
        y5 = self.compute_block_y5(
            indicators.get('x51', 0), indicators.get('x52', 0), indicators.get('x53', 0)
        )
        y6 = self.compute_block_y6(
            indicators.get('x61', 0), indicators.get('x62', 0)
        )
        y7 = self.compute_block_y7(
            indicators.get('x71', 0), indicators.get('x72', 0), indicators.get('x73', 0)
        )
        y8 = self.compute_block_y8(
            indicators.get('x81', 0), indicators.get('x82', 0), indicators.get('x83', 0)
        )
        y9 = self.compute_block_y9(
            indicators.get('x91', 0), indicators.get('x92', 0)
        )

        # Промежуточные агрегаторы
        y38 = self.compute_intermediate_y38(y3, y8)
        y47 = self.compute_intermediate_y47(y4, y7)
        y56 = self.compute_intermediate_y56(y5, y6)
        y29 = self.compute_intermediate_y29(y2, y9)

        # Факторы
        z1 = self.compute_factor_z1(y38, y47)  # Технико-технологический
        z2 = self.compute_factor_z2(y29, y56)  # Когнитивный
        # y1 уже является личностным фактором (не переименован для совместимости)

        # Интегральный уровень и балл
        dm_level = self.compute_dm_level(z1, z2, y1)
        dm_score = self.compute_dm_score(dm_level)

        # Преобразование уровней факторов в проценты для отображения
        def level_to_percent(level):
            mapping = {0: 15, 1: 35, 2: 65, 3: 90}
            return mapping.get(level, 0)

        return {
            'final_score': float(dm_score),
            'dm_level': dm_level,
            'technical_factor': float(level_to_percent(z1)),
            'cognitive_factor': float(level_to_percent(z2)),
            'personal_factor': float(level_to_percent(y1)),
            'blocks': {
                'block_1': y1, 'block_2': y2, 'block_3': y3, 'block_4': y4,
                'block_5': y5, 'block_6': y6, 'block_7': y7, 'block_8': y8, 'block_9': y9
            },
            'factors_raw': {'z1': z1, 'z2': z2, 'y1': y1},
            'blocks_raw': {'y1': y1, 'y2': y2, 'y3': y3, 'y4': y4, 'y5': y5,
                           'y6': y6, 'y7': y7, 'y8': y8, 'y9': y9}
        }


# Для обратной совместимости с существующим кодом
DigitalMaturityFuzzyModel = DigitalMaturityModel
MamdaniFuzzySystem = DigitalMaturityModel  # Алиас для совместимости

# Тест модели
if __name__ == "__main__":
    model = DigitalMaturityModel()

    # Тест 1: Все показатели на уровне 2 (средний уровень)
    test_scores = {}
    for i in range(1, 10):
        for j in range(1, 4):
            if i == 6 and j > 2:
                continue
            if i == 9 and j > 2:
                continue
            test_scores[f'{i}.{j}'] = 2

    # Добавляем недостающие
    test_scores['6.1'] = 2
    test_scores['6.2'] = 2
    test_scores['9.1'] = 2
    test_scores['9.2'] = 2

    result = model.evaluate(test_scores)

    print("=" * 60)
    print("ТЕСТ МОДЕЛИ ЦИФРОВОЙ ЗРЕЛОСТИ (ПО НИЛ-27)")
    print("=" * 60)
    print(f"Все показатели = 2 (из 3)")
    print("-" * 60)
    print(f"ИТОГОВЫЙ БАЛЛ: {result['final_score']:.0f}")
    print(f"Уровень DM: {result['dm_level']} (0-3)")
    print(f"Технико-технологический фактор: {result['technical_factor']:.0f}%")
    print(f"Когнитивный фактор: {result['cognitive_factor']:.0f}%")
    print(f"Личностный фактор: {result['personal_factor']:.0f}%")
    print("-" * 60)
    print("Оценки блоков (0-3):")
    for block, val in result['blocks_raw'].items():
        print(f"  {block}: {val}")

    # Тест 2: Все показатели на максимуме
    test_scores_max = {k: 3 for k in test_scores.keys()}
    result_max = model.evaluate(test_scores_max)
    print("\n" + "=" * 60)
    print("Все показатели = 3 (максимум)")
    print(f"ИТОГОВЫЙ БАЛЛ: {result_max['final_score']:.0f}")
    print(f"Уровень DM: {result_max['dm_level']}")

    # Тест 3: Все показатели на минимуме
    test_scores_min = {k: 0 for k in test_scores.keys()}
    result_min = model.evaluate(test_scores_min)
    print("\n" + "=" * 60)
    print("Все показатели = 0 (минимум)")
    print(f"ИТОГОВЫЙ БАЛЛ: {result_min['final_score']:.0f}")
    print(f"Уровень DM: {result_min['dm_level']}")
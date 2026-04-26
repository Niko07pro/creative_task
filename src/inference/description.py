"""SIMILIS auto_description template — фиксированный шаблон сборки описания.

Используется как в обучении (для оценки точности шаблонной сборки на val),
так и в инференсе (Задание 18).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldPrediction:
    value: Optional[str]
    confidence: float = 1.0


# Пороги уверенности (стартовые)
THRESHOLDS = {
    "type":     0.6,
    "material": 0.6,
    "part":     0.5,
    "fragm":    0.5,
}

TYPE_GENDER = {
    "Тарелка": "f", "Изразец": "m", "Блюдце": "n",
    "Крышка": "f", "Миска": "f", "Плитка": "f", "Игрушка": "f",
}

TYPE_GEN = {
    "Тарелка": "Тарелки", "Изразец": "Изразца", "Блюдце": "Блюдца",
    "Крышка": "Крышки", "Миска": "Миски", "Плитка": "Плитки", "Игрушка": "Игрушки",
}

MATERIAL_ADJ = {
    "Керамика": {"f": "керамической", "m": "керамического", "n": "керамического"},
    "Фаянс":    {"f": "фаянсовой",    "m": "фаянсового",    "n": "фаянсового"},
    "Фарфор":   {"f": "фарфоровой",   "m": "фарфорового",   "n": "фарфорового"},
    "Стекло":   {"f": "стеклянной",   "m": "стеклянного",   "n": "стеклянного"},
    "Глина":    {"f": "глиняной",     "m": "глиняного",     "n": "глиняного"},
    "Прочее":   {"f": "",             "m": "",              "n": ""},
}

PART_TEXT = {
    "общий_фрагмент":  "фр-т",
    "профиль":         "профиль фр-т",
    "донце":           "донце фр-т",
    "венчик":          "венчик фр-т",
    "целый_предмет":   "целый",
    "крышка":          "крышка фр-т",
    "придонная_часть": "придонная часть фр-т",
    "ручка":           "ручка фр-т",
    "другое":          "фр-т",
}


def build_auto_description(
    type_pred: FieldPrediction,
    material_pred: FieldPrediction,
    part_pred: FieldPrediction,
    fragm_pred: FieldPrediction,
    thresholds=THRESHOLDS,
) -> str:
    """Собирает auto_description из 4 предсказанных полей."""
    parts = []

    # 1. TYPE_GEN
    if type_pred.value is None or type_pred.value not in TYPE_GEN:
        type_str = "Предмет"
    else:
        type_str = TYPE_GEN[type_pred.value]
    if type_pred.confidence < thresholds["type"]:
        type_str += " (?)"
    parts.append(type_str)

    # 2. MATERIAL_ADJ
    gender = TYPE_GENDER.get(type_pred.value, "f")
    if (material_pred.value is not None
            and material_pred.confidence >= thresholds["material"]
            and material_pred.value in MATERIAL_ADJ):
        adj = MATERIAL_ADJ[material_pred.value][gender]
        if adj:
            parts.append(adj)

    # 3. PART/INTEGRITY
    fragm_low_conf = fragm_pred.confidence < thresholds["fragm"]
    is_whole = (fragm_pred.value == "Целый" and not fragm_low_conf)

    if is_whole:
        parts.append("целый")
    else:
        if part_pred.value is None or part_pred.confidence < thresholds["part"]:
            parts.append("фр-т")
        else:
            parts.append(PART_TEXT.get(part_pred.value, "фр-т"))

    return " ".join(parts)
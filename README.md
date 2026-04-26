# SIMILIS Baseline

Проект для творческого задания **SIMILIS** — формализованное описание археологических артефактов по изображению. По фотографии артефакта модель предсказывает несколько ключевых полей и собирает `auto_description` по фиксированному шаблону.

> **Статус:** Часть 1 (подготовка данных, EDA, split, preprocessing) завершена. Часть 2 (обучение, инференс, ablation) — в работе.

---

## Подход

Берём **4 поля**, которые надёжно извлекаются из визуала:

| Поле | Источник | Кол-во классов | Тип цели |
|---|---|---|---|
| `name_norm` (тип предмета) | колонка `name` в CSV, после нормализации | 7 | single-label |
| `material_norm` (материал) | колонка `material`, после группировки длинного хвоста | 6 | single-label |
| `fragm` (целостность) | колонка `fragm` | 2 | single-label |
| `part_norm` (часть) | извлекается из `description` через regex + словарь | 9 | single-label |

Поля, которые **сознательно НЕ предсказываются** (нет надёжного визуального сигнала): функция, технология, датировка, культурная принадлежность, тонкие типологические подтипы.

### Шаблон auto_description

Зафиксирован **до обучения** (см. `src/inference/description.py`):
```{TYPE_GEN} {MATERIAL_ADJ} {PART_OR_INTEGRITY}```
Примеры:
- `Тарелки фаянсовой профиль фр-т`
- `Блюдца фарфорового целый`
- `Изразца керамического венчик фр-т`

При низкой уверенности модели:
- по типу → добавляется `(?)`
- по материалу → поле пропускается
- по части → fallback на `фр-т`
- по целостности → считается фрагментом (доминирующий класс)

---

## Данные

- **Открытый сабсет**: 1389 строк CSV ↔ 1388 уникальных изображений (1 дубль `code=46858`)
- **Скрытый сабсет**: ~100 изображений — используется только для финального blind inference
- **Покрытие связи csv ↔ файлы**: 100% после исправления mojibake и NFC-нормализации
- **`group_key = code`** (инвентарный номер) — гарантирует, что разные ракурсы одного предмета не разорвутся между train/val/test
- **Маски** (бинарные силуэты на чёрном фоне) — обнаружено 28 шт., исключены из train/val/test

### Splits (group-aware, стратифицированы по `name_norm`)

| split | размер | доля |
|---|---|---|
| `train_inner` | 971 | 71.3% |
| `val_inner` | 195 | 14.3% |
| `test_open` | 195 | 14.3% |
| **итого рабочих** | **1361** | (после исключения 28 масок) |

Файлы: `splits/train_inner.csv`, `splits/val_inner.csv`, `splits/test_open.csv`

---

## Ключевые находки из EDA

### Технические сюрпризы в данных

1. **Mojibake в именах файлов** (UTF-8 → CP866 при упаковке архива на macOS). Починено скриптом `src/fix_filenames.py` (1387 файлов переименовано).
2. **NFC vs NFD нормализация Unicode**: имена файлов с `й` хранились в NFD (`и` + комбинируемая бреве), CSV — в NFC. Без `unicodedata.normalize("NFC", ...)` 248 файлов не матчились.
3. **Один потерянный файл** (`46858_orig.jpg`) с цифровым кодом — восстановлен вручную.
4. **Очень крупные изображения**: median 4671×3654 px, max 184 МП. Требуется `Image.MAX_IMAGE_PIXELS = None`.

### Аномалии корпуса

- **28 бинарных масок** (силуэты на чёрном фоне) — отдельная модальность, **shortcut-риск** (модель могла бы выучить «чёрный фон → Тарелка/Блюдце»). Помечены флагом `is_mask` и исключены из обучения.
- **Масштабная линейка + подпись инвентарного кода** на ~всех нормальных карточках — потенциальный shortcut, не устранён preprocessing'ом, останется фактором для error analysis.
- **Длинный хвост по материалам**: 21 raw-класс, 92% корпуса в топ-3. Свёрнуты в 6 групп.

### Распределения

- Топ-5 классов `name`: Тарелка 480, Изразец 361, Блюдце 216, Крышка 177, Миска 113
- Дисбаланс `fragm`: 90:10 (Фрагмент / Целый) → потребуются `class_weight` или weighted sampler
- 14 различных «сайтов» (раскопов) по префиксу инвентарного кода
- Aspect ratio: median 1.32, диапазон 0.26–4.95 → `longest_side resize + pad`, не CenterCrop
- Foreground ratio: median 0.31 — объект занимает ~треть кадра, две трети фона

---

## Preprocessing и аугментации

**Базовый трансформ (train + val):**
1. Открыть с `MAX_IMAGE_PIXELS = None`
2. Convert RGB
3. `ResizeLongestSideAndPad(224, fill=white)` — сохранение пропорций + pad белым (сливается с фоном)
4. `Normalize(mean=ImageNet, std=ImageNet)`

**Train-аугментации (только train):**
- `RandomHorizontalFlip(p=0.5)` — лево/право артефакта семантически симметрично
- `RandomRotation(degrees=10, fill=white)` — лёгкое вращение
- `ColorJitter(brightness=0.1, contrast=0.1)` — компенсация экспозиции, без hue/saturation

**Что сознательно НЕ делаем и почему:**

| Аугментация | Причина отказа |
|---|---|
| CenterCrop / RandomResizedCrop | Объект занимает ~30% кадра, agressive crop вырежет его. Multi-view карточки потеряют ракурсы. |
| Mosaic / CutMix между разными артефактами | Смешает разные предметы — модель будет учить ложные комбинации |
| Полная инверсия | В корпусе уже есть бинарные маски с инвертированными цветами |
| Resize в квадрат без pad | Aspect ratio 0.26–4.95 — растянет узкие предметы |
| Hue/Saturation jitter, сильный blur | Цвет покрытия и тонкий орнамент — целевые признаки |

---

## Структура репозитория

```
similis-baseline/
├── README.md
├── requirements.txt
├── data/                          # не коммитится (.gitignore)
│   ├── raw/                       # csv + dataset/ (изображения)
│   ├── interim/                   # items_with_images.csv, image_sizes.csv, ...
│   └── processed/
├── splits/
│   ├── train_inner.csv
│   ├── val_inner.csv
│   └── test_open.csv
├── artifacts/
│   ├── checkpoints/               # будет — best.pt / last.pt
│   ├── preds/                     # будет — итоговый CSV после инференса
│   ├── reports/
│   └── figures/                   # графики из EDA, sanity-checks
├── notebooks/
│   └── 01_eda.ipynb               # вся Часть 1: задания 1-10
└── src/
    ├── fix_filenames.py           # починка mojibake
    └── inference/
        └── description.py         # шаблон auto_description (зафиксирован до обучения)
```

---

## Запуск

### Установка

```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

```

### Подготовка данных

1. Положить `selected_by_name_iimk_subset_public.csv` в `data/raw/`
2. Распаковать архив с изображениями в `data/raw/dataset/`
3. Если на Windows — почистить mojibake в именах:
```bash
   python src/fix_filenames.py
```

### Запуск ноутбука

```bash
python -m ipykernel install --user --name similis --display-name "Python (similis)"
jupyter notebook
```

Открыть `notebooks/01_eda.ipynb`, выбрать kernel **Python (similis)**, выполнить все ячейки.

---

## Стек

- Python 3.12
- PyTorch 2.11
- torchvision, scikit-learn, pandas, Pillow, matplotlib, tqdm

---


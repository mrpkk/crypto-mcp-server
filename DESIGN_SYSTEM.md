# DESIGN SYSTEM — ChainSight v2

> Философия: **quiet confidence** — precision, clarity, technical elegance.
> Запрещено: AI-gradient стартап, неоновый cyberpunk, glassmorphism everywhere.
> Реализация: `web/tokens.css` + `web/styles.css` (тёмная тема по умолчанию, светлая — переключатель).

## Принципы

1. **Один вопрос на экран** — Command Center отвечает: «Что происходит? Что меняется? Что рискованно?»
2. **Decision-first** — главный экран показывает максимум 3 приоритетных сигнала (сейчас: карточки пульса + movers).
3. **Data-quality всегда видим** — каждый блок данных несёт бейдж LIVE / CACHED / STALE / DEGRADED / UNAVAILABLE.
4. **Progressive disclosure** — уровень 1: одна цифра → уровень 2: метрика + изменение → уровень 3: источник и детали.
5. **Честные пустые и ошибочные состояния** — WHY + NEXT ACTION (error contract выводит `suggested_action`).
6. **Никаких выдуманных данных** — если источник недоступен, показывается UNAVAILABLE, а не плейсхолдер-цифра.

## Токены (фрагмент)

| Токен | Значение | Назначение |
|---|---|---|
| `--bg` | `#0A0E17` | фон |
| `--surface` | `#12161F` | карточки, панели |
| `--primary` | `#5B8DEF` | действия, ссылки |
| `--success` | `#34D399` | рост, LIVE |
| `--error` | `#F87171` | падение, DEGRADED |
| `--warn` | `#FBBF24` | STALE |
| `--text` / `--muted` | `#E6EAF2` / `#8B93A7` | текст |
| `--font-ui` | Inter, system stack | интерфейс |
| `--font-mono` | JetBrains Mono stack | числа и данные |

Полный список: `web/tokens.css` (цвет, data-quality, отступы, радиусы, тени, transition).

## Компоненты

| Компонент | Классы | Состояния |
|---|---|---|
| Кнопка | `.btn`, `.btn-primary`, `.btn-ghost` | hover / active / focus-visible / disabled |
| Карточка | `.card`, `.card-header`, `.card-title` | loading (skeleton) / error |
| Метрика | `.metric`, `.metric-delta.up/.down` | — |
| Бейдж качества | `.badge-live…badge-unavailable`, `.badge-demo` | 5 статусов + DEMO |
| Таблица | `.table` | пустая (текст-подсказка) |
| Skeleton | `.skeleton` | shimmer-анимация |
| Тост | `.toast`, `.toast.error/.success` | info / error / success |
| Онбординг | `.onboarding` | закрывается |
| Error-box | `.error-box` | code + message + suggested_action |

## Сетка и адаптивность

- App shell: sidebar 220px + main; ≤1100px — сетки 2×, ≤720px — мобильный (sidebar скрыт).
- Сетки: `.grid-4` (пульс), `.grid-2` (movers/yields).

## Доступность (цель WCAG 2.1 AA)

- Контраст текста на фоне ≥ 4.5:1 (палитра подобрана под это).
- `:focus-visible` — контур 2px на навигации и кнопках.
- Семантика: `aside[aria-label]`, `aria-live="polite"` для тостов, кнопки-элементы `<button>`.
- Не только цвет: статусы качества имеют текстовые метки (LIVE/CACHED/…).

## Что дальше (S7+)

- Chart/Sparkline/Heatmap компоненты под реальные данные (без декоративных графиков).
- Watchlists UI и alerts UI (когда появятся API).

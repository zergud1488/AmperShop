# AmperShop v3 MVP

Локальний маркетплейс для дропшипінгу на Flask + SQLite з красивою вітриною, адмінкою, Telegram-сповіщеннями та готовністю до домену.

## Що додано у v3
- пошук, фільтри та сортування в каталозі
- wishlist / обране для користувача
- промокоди з адмінки
- покращена головна сторінка у більш преміальному стилі
- checkout з live-перевіркою телефону та email
- autocomplete для міста / відділення під Nova Poshta та Meest
- збереження промокоду та суми знижки в замовленні
- розширені налаштування Meest в адмінці
- PWA, мобільна адаптація, кабінет користувача, Google login залишилися

## Запуск
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
python app.py
```

## Вхід в адмінку
- Email: `admin@ampershop.local`
- Пароль: `admin12345`

## Telegram
1. Додай токен бота в адмінці.
2. Додай свій `chat_id` в адмінці.
3. У товарі додай `supplier_chat_id` постачальника.
4. З акаунта власника і постачальника відкрий бота та натисни **Start**.
5. У налаштуваннях натисни **Надіслати тест у Telegram**.
6. Перевір логи Telegram у налаштуваннях.

## Google login
Заповни в `.env` або в адмінці:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Redirect URI:
- `http://127.0.0.1:5000/account/google/callback`

## Nova Poshta / Meest
### Nova Poshta
- вкажи `NOVAPOSHTA_API_KEY`
- checkout використовує API для пошуку міст і відділень

### Meest
- у v3 MVP доданий адаптер під публічні/контрактні довідники
- можна заповнити:
  - `MEEST_API_KEY`
  - `MEEST_LOGIN`
  - `MEEST_PASSWORD`
  - `MEEST_PUBLIC_API_BASE`
- якщо endpoint або авторизація відрізняються у твоєму акаунті, достатньо підправити helper-функції в `app.py`

## Домен
У налаштуваннях є поле домену та приклад конфігу Nginx.

## Примітка
SQLite автоматично мігрується при старті для нових полів і таблиць.


## Ultra Edition
Оновлена вітрина з більш преміальною головною сторінкою, покращеними картками товарів, компактнішою шапкою та професійними текстами для публічного магазину.


## Нове у CMS / імпорті

### Конструктор сторінок
В адмінці з'явився розділ **Конструктор сторінок**:
- керування головним hero-блоком
- зміна текстів кнопок і посилань
- зміна текстів футера
- зміна текстів каталогу та checkout
- зміна порядку 3 інформаційних карток на головній через поля `позиція`

### Імпорт додаткових товарів
В адмінці з'явився розділ **Імпорт товарів**. Підтримується завантаження SQLite файлів:
- `.db`
- `.sqlite`
- `.sqlite3`

Підтримувані таблиці:
- `products` / `product` / `items`
- `categories` / `category`

Бажані поля в таблиці товарів:
- `title`
- `slug`
- `short_description`
- `description`
- `specifications`
- `price`
- `old_price`
- `category_id`
- `is_top`
- `is_active`
- `stock_status`
- `supplier_chat_id`

Існуючі товари оновлюються за `slug` або `title`, нові — додаються автоматично.

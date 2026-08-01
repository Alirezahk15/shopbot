<div align="center">

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black"/>
<img src="https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white"/>

<br/><br/>

<img width="80" src="https://raw.githubusercontent.com/Alirezahk15/shopbot/main/.github/logo.png" alt="ShopBot"/>

# 🤖 ShopBot

### ربات فروشگاه تلگرام + پنل مدیریت وب حرفه‌ای

*فروشگاه آنلاین تلگرامی کامل با پنل مدیریت React و نصب تک‌دستوری*

<br/>

[![نصب سریع](https://img.shields.io/badge/نصب_سریع-یک_دستور-6366f1?style=for-the-badge)](#-نصب-سریع)
[![لایسنس](https://img.shields.io/badge/License-Commercial-f59e0b?style=for-the-badge)](#)
[![پشتیبانی](https://img.shields.io/badge/Support-30_Days-10b981?style=for-the-badge)](#-پشتیبانی)

</div>

---

## ✨ امکانات

<table>
<tr>
<td width="50%">

### 💳 پرداخت
- کارت به کارت (دستی / خودکار)
- USDT BEP20 (شبکه BSC)
- USDT TRC20 (شبکه TRON)
- TON Blockchain
- زرین‌پال (درگاه ایرانی)

### 🛍 فروشگاه
- محصولات + دسته‌بندی + موجودی
- بنر سفارشی برای هر محصول
- قیمت‌گذاری به دلار
- سفارش‌گیری خودکار ۲۴/۷

</td>
<td width="50%">

### 👑 مدیریت کاربران
- سیستم سطح کاربر (برنز / نقره / طلا)
- VIP با تخفیف خودکار
- سیستم رفرال و درآمد معرف
- مسدودسازی کاربر

### 🎟 بازاریابی
- کد تخفیف با محدودیت زمان/تعداد
- پیام مناسبتی خودکار
- پخش پیام به همه کاربران
- دعوت‌نامه با بنر سفارشی

</td>
</tr>
<tr>
<td>

### 🛡 گارانتی
- کد گارانتی یکتا برای هر سفارش
- پیگیری وضعیت گارانتی
- پنل مدیریت گارانتی

### 🔒 امنیت
- احراز هویت دو مرحله‌ای (TOTP)
- قفل گروه / کانال
- کپچا ضدربات
- محدودیت آنتی‌اسپم

</td>
<td>

### 📊 پنل مدیریت
- داشبورد با نمودار فروش
- مدیریت کامل از طریق وب
- ۲۰+ صفحه تخصصی
- تم‌های رنگی + فونت + RTL/LTR
- پشتیبانی از ادمین‌های متعدد

### 📢 اطلاع‌رسانی
- گزارش خودکار به گروه تلگرام
- بکاپ خودکار دیتابیس
- لاگ کامل رویدادها

</td>
</tr>
</table>

---

## 🚀 نصب سریع

> **پیش‌نیاز:** سرور Ubuntu 20.04 / 22.04 / 24.04 با دسترسی root

```bash
sudo bash <(curl -fsSL https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
```

> **🔒 اگر ریپو Private است (خطای `404`):** دستور بالا فقط برای ریپوی Public کار می‌کند. دو راه‌حل:
>
> **۱)** ریپو را موقتاً Public کنید (Settings → Danger Zone → Change visibility) و بعد از نصب دوباره Private کنید.
>
> **۲)** با Personal Access Token نصب کنید (ریپو Private می‌ماند):
>
> ```bash
> export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
> sudo -E bash <(curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
>   https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
> ```
>
> اسکریپت `install.sh` به‌صورت خودکار از همین توکن برای دانلود پروژه استفاده می‌کند.

این دستور به‌صورت خودکار:
1. پروژه را دانلود می‌کند
2. یک **Wizard نصب تحت وب** روی پورت `8080` راه‌اندازی می‌کند
3. آدرس را نمایش می‌دهد

سپس آدرس نمایش‌داده‌شده را در مرورگر باز کنید و نصب را تکمیل کنید.

---

## 🧙 Wizard نصب تحت وب

بعد از اجرای دستور بالا، wizard در مرورگر باز کنید و مراحل را طی کنید:

| مرحله | توضیح |
|-------|-------|
| 1 — خوش‌آمدید | معرفی امکانات |
| 2 — توکن ربات | اعتبارسنجی زنده با تلگرام |
| 3 — ادمین | آیدی عددی تلگرام |
| 4 — پنل | دامنه + رمز + SSL رایگان |
| 5 — پرداخت | انتخاب روش‌های فعال |
| 6 — کلیدهای API | BscScan، زرین‌پال و... |
| 7 — مرور | تأیید نهایی |
| 8 — نصب | لاگ زنده + progress bar |
| 9 — پایان | لینک پنل + رمز ورود |

---

## 🔧 نصب دستی

اگر ترجیح می‌دهید بدون wizard نصب کنید:

```bash
# ۱. clone پروژه
git clone https://github.com/Alirezahk15/shopbot.git /opt/shopbot
cd /opt/shopbot

# ۲. اجرای اسکریپت نصب سنتی
sudo bash install.sh
```

---

## 📁 ساختار پروژه

```
shopbot/
├── main.py              ← ربات تلگرام (Python)
├── database.py          ← لایه دیتابیس SQLite
├── config.py            ← تنظیمات پروژه
├── lang.py              ← ترجمه فارسی / انگلیسی
├── api/
│   ├── main.py          ← FastAPI — پنل مدیریت
│   ├── auth.py          ← JWT + bcrypt + TOTP
│   └── routers/         ← 22 روتر تخصصی
├── panel/
│   └── src/             ← React 18 + Vite + Tailwind
├── setup/
│   └── wizard.py        ← Wizard نصب تحت وب
├── quick-install.sh     ← نصب تک‌دستوری
├── install.sh           ← راه‌اندازی wizard
├── update.sh            ← آپدیت پروژه
└── uninstall.sh         ← حذف کامل
```

---

## 🛠 تکنولوژی‌ها

<div align="center">

| بخش | تکنولوژی |
|-----|----------|
| ربات | Python 3.10+ · python-telegram-bot v20 |
| API | FastAPI · uvicorn · Pydantic v2 |
| دیتابیس | SQLite (WAL mode) |
| پنل | React 18 · Vite · TailwindCSS |
| احراز هویت | JWT · bcrypt · TOTP (2FA) |
| وب‌سرور | Nginx · systemd |
| نصب | Python http.server (بدون dependency) |

</div>

---

## ⚙️ دستورات مدیریت سرور

```bash
# وضعیت سرویس‌ها
systemctl status shopbot shopbot-panel

# لاگ زنده ربات
journalctl -u shopbot -f

# لاگ زنده پنل
journalctl -u shopbot-panel -f

# ری‌استارت
systemctl restart shopbot shopbot-panel

# آپدیت به آخرین نسخه
cd /opt/shopbot && sudo bash update.sh
```

---

## 📸 پیش‌نمایش

> پنل مدیریت با طراحی دارک مینیمال، دو زبانه (فارسی/انگلیسی) و تم‌های رنگی متنوع.

| داشبورد | محصولات | تنظیمات |
|---------|---------|---------|
| ![dashboard](https://via.placeholder.com/280x160/141720/6366f1?text=Dashboard) | ![products](https://via.placeholder.com/280x160/141720/10b981?text=Products) | ![settings](https://via.placeholder.com/280x160/141720/f59e0b?text=Settings) |

---

## 📞 پشتیبانی

- ✅ **۳۰ روز** پشتیبانی رایگان پس از خرید
- 📱 تلگرام: [@Alirezahk15](https://t.me/Alirezahk15)
- 🐛 گزارش باگ: [GitHub Issues](https://github.com/Alirezahk15/shopbot/issues)

---

<div align="center">

ساخته‌شده با ❤️ برای فروشندگان ایرانی

</div>
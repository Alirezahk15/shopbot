# 🤖 ShopBot — ربات فروشگاه تلگرام

پنل مدیریت حرفه‌ای + ربات تلگرام برای فروشگاه آنلاین

---

## ✨ امکانات

| بخش | ویژگی‌ها |
|-----|---------|
| 💳 پرداخت | کارت به کارت، USDT BEP20، USDT TRC20، TON، زرین‌پال |
| 🛍 فروشگاه | محصولات، دسته‌بندی، موجودی، بنر |
| 👑 VIP | سیستم سطح کاربر، تخفیف VIP، پیام سفارشی |
| 🎟 تخفیف | کد تخفیف، تخفیف معرف |
| 🛡 گارانتی | سیستم گارانتی با کد یکتا |
| 📊 گزارش | داشبورد، فروش، پرداخت‌ها، کاربران |
| 📢 پیام‌رسانی | پخش پیام به همه کاربران، فیلتر |
| 🔒 امنیت | قفل گروه/کانال، کپچا، ضداسپم |
| 🎨 پنل مدیریت | React + FastAPI، تم‌های رنگی، دو زبانه |

---

## 🚀 نصب روی سرور لینوکس

### پیش‌نیازها
- سرور Ubuntu 20.04 / 22.04 / 24.04
- دسترسی root
- دامنه یا IP ثابت
- توکن ربات از [@BotFather](https://t.me/BotFather)

### مراحل نصب

```bash
# ۱. انتقال فایل‌ها به سرور
scp -r shopbot/ root@SERVER_IP:/root/

# ۲. وارد شدن به سرور
ssh root@SERVER_IP

# ۳. رفتن به پوشه پروژه
cd /root/shopbot

# ۴. اجرای نصب‌کننده
sudo bash install.sh
```

اسکریپت به‌صورت خودکار:
- Python 3، Node.js 20، Nginx نصب می‌کند
- از شما توکن ربات و تنظیمات می‌پرسد
- پنل React را Build می‌کند
- سرویس‌های systemd می‌سازد
- Nginx را پیکربندی می‌کند
- فایروال را تنظیم می‌کند

---

## 🔄 آپدیت

```bash
# کپی فایل‌های جدید به سرور
scp -r shopbot/ root@SERVER_IP:/root/shopbot-new/

# اجرای آپدیت
ssh root@SERVER_IP "cd /root/shopbot-new && sudo bash update.sh"
```

---

## 🗑 حذف

```bash
sudo bash /opt/shopbot/uninstall.sh
```

---

## 📁 ساختار پروژه

```
shopbot/
├── main.py              ← ربات تلگرام
├── database.py          ← لایه دیتابیس SQLite
├── config.py            ← تنظیمات ثابت
├── lang.py              ← ترجمه فارسی/انگلیسی
├── api/
│   ├── main.py          ← FastAPI (پنل مدیریت)
│   ├── auth.py          ← احراز هویت JWT + TOTP
│   └── routers/         ← روترهای API (22 فایل)
├── panel/
│   └── src/             ← React frontend
├── install.sh           ← نصب خودکار
├── update.sh            ← آپدیت
└── uninstall.sh         ← حذف
```

---

## ⚙️ تنظیمات پس از نصب

### ورود به پنل
```
آدرس:   https://your-domain.com
رمز:    (در پایان نصب نمایش داده می‌شود)
```

### دستورات مدیریت سرور
```bash
# وضعیت سرویس‌ها
systemctl status shopbot shopbot-panel

# لاگ زنده ربات
journalctl -u shopbot -f

# لاگ زنده پنل
journalctl -u shopbot-panel -f

# ری‌استارت همه
systemctl restart shopbot shopbot-panel
```

---

## 🛠 تکنولوژی‌ها

- **Backend:** Python 3.10+, python-telegram-bot v20, FastAPI
- **Database:** SQLite (WAL mode)
- **Frontend:** React 18, Vite, TailwindCSS
- **Server:** Nginx, uvicorn, systemd
- **Auth:** JWT, bcrypt, TOTP (2FA)

---

## 📞 پشتیبانی

پس از خرید، ۳۰ روز پشتیبانی رایگان ارائه می‌شود.
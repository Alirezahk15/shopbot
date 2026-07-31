import re

T = {
 "pay_usdt_trc20":    {"fa": "💎 USDT (شبکه TRC20)", "en": "💎 USDT (TRC20)"},
 "pay_ton":           {"fa": "💠 تون (TON)", "en": "💠 TON"},
 "pay_stars":         {"fa": "⭐ استارز تلگرام", "en": "⭐ Telegram Stars"},
 "pay_zarinpal":      {"fa": "🇮🇷 درگاه زرین‌پال", "en": "🇮🇷 Zarinpal gateway"},
 "usdt_trc20_guide":  {"fa": "💎 <b>واریز USDT (TRC20)</b>\n\nمبلغ دلخواه (حداقل ${m}) را به آدرس زیر بفرستید:\n<code>{w}</code>\n\nسپس روی «ارسال هش» بزنید و هش تراکنش را بفرستید.",
                       "en": "💎 <b>USDT deposit (TRC20)</b>\n\nSend any amount (min ${m}) to:\n<code>{w}</code>\n\nThen press Send TX and send the transaction hash."},
 "ton_guide":         {"fa": "💠 <b>واریز TON</b>\n\n۱. مبلغ دلخواه را به آدرس زیر بفرستید:\n<code>{w}</code>\n\n۲. حتماً این کد را در بخش Comment/Memo تراکنش بنویسید:\n<code>{memo}</code>\n\n۳. بعد از ارسال، روی «بررسی پرداخت» بزنید.",
                       "en": "💠 <b>TON deposit</b>\n\n1. Send any amount to:\n<code>{w}</code>\n\n2. You MUST put this code in the Comment/Memo:\n<code>{memo}</code>\n\n3. Then press Check payment."},
 "ton_check":         {"fa": "🔍 بررسی پرداخت", "en": "🔍 Check payment"},
 "stars_ask_amount":  {"fa": "⭐ مبلغ شارژ را به دلار بفرستید (هر ۱ دلار = {s} استار):", "en": "⭐ Send amount in USD (1 USD = {s} Stars):"},
 "stars_invoice_title": {"fa": "شارژ حساب", "en": "Balance top-up"},
 "stars_invoice_desc":  {"fa": "شارژ ${a:.2f} با استارز تلگرام", "en": "Top up ${a:.2f} with Telegram Stars"},
 "zp_ask_amount":     {"fa": "🇮🇷 مبلغ شارژ را به دلار بفرستید:", "en": "🇮🇷 Send top-up amount in USD:"},
 "zp_pay_link":       {"fa": "💳 پرداخت <b>${a:.2f}</b> ({t:,} تومان)\n\nروی دکمه زیر بزنید و پرداخت را کامل کنید. بعد از پرداخت، موجودی خودکار شارژ می‌شود.",
                       "en": "💳 Pay <b>${a:.2f}</b> ({t:,} Toman)\n\nTap the button below to complete payment. Your balance updates automatically."},
 "zp_pay_btn":        {"fa": "💳 پرداخت آنلاین", "en": "💳 Pay online"},
 "zp_error":          {"fa": "❌ خطا در ساخت لینک پرداخت: {e}", "en": "❌ Payment link error: {e}"},
 "captcha_q":         {"fa": "🤖 برای اطمینان از ربات نبودن، پاسخ را بفرستید:\n\n<b>{a} + {b} = ?</b>", "en": "🤖 Prove you are human:\n\n<b>{a} + {b} = ?</b>"},
 "captcha_ok":        {"fa": "✅ تایید شد! دوباره /start بزنید.", "en": "✅ Verified! Send /start again."},
 "captcha_bad":       {"fa": "❌ اشتباه است، دوباره تلاش کنید.", "en": "❌ Wrong, try again."},
 "card_expired":      {"fa": "⏳ پرداخت کارت‌به‌کارت شما به دلیل عدم تایید در مهلت مقرر منقضی شد. در صورت پرداخت، با پشتیبانی تماس بگیرید.", "en": "⏳ Your card payment expired (not approved in time). Contact support if you already paid."},
 "ref_signup_bonus":  {"fa": "🎁 پاداش عضویت زیرمجموعه: <b>${a:.2f}</b> به حساب شما اضافه شد!", "en": "🎁 Referral signup bonus: <b>${a:.2f}</b> added!"},
 "level_lbl":         {"fa": "🏅 سطح", "en": "🏅 Level"},
 "level_bronze":      {"fa": "🥉 برنزی", "en": "🥉 Bronze"},
 "level_silver":      {"fa": "🥈 نقره‌ای", "en": "🥈 Silver"},
 "level_gold":        {"fa": "🥇 طلایی", "en": "🥇 Gold"},
 "btn_reftop":        {"fa": "🏆 برترین معرف‌ها", "en": "🏆 Top referrers"},
 "reftop_title":      {"fa": "🏆 <b>برترین معرف‌ها</b>", "en": "🏆 <b>Top referrers</b>"},
 "reftop_empty":      {"fa": "هنوز کسی پورسانت نگرفته است.", "en": "No referral earnings yet."},
 # ── زبان و خوش‌آمد ──
 "choose_lang":       {"fa": "🌐 لطفاً زبان خود را انتخاب کنید:\n\n🌐 Please select your language:",
                       "en": "🌐 Please select your language:\n\n🌐 لطفاً زبان خود را انتخاب کنید:"},
 "lang_changed":      {"fa": "✅ زبان به فارسی تغییر کرد.", "en": "✅ Language changed to English."},
 "welcome":           {"fa": "🎉 به <b>فروشگاه اشتراک هوش مصنوعی</b> خوش آمدید!\n\n🛍 خرید اشتراک ChatGPT، Claude، Midjourney و...\n⚡️ تحویل خودکار و آنی ۲۴/۷\n💎 پرداخت با USDT و کارت به کارت\n\n👇 یکی از دکمه‌ها را انتخاب کنید:",
                       "en": "🎉 Welcome to <b>AI Subscription Store</b>!\n\n🛍 Buy ChatGPT, Claude, Midjourney subscriptions...\n⚡️ Instant automatic delivery 24/7\n💎 Pay with USDT or bank card\n\n👇 Tap a button below:"},
 # ── دکمه‌های اصلی ──
 "btn_browse":        {"fa": "🛍 مشاهده محصولات",   "en": "🛍 Browse Products"},
 "btn_orders":        {"fa": "📊 سفارش‌های من",      "en": "📊 My Orders"},
 "btn_recharge":      {"fa": "💰 شارژ حساب",         "en": "💰 Recharge"},
 "btn_profile":       {"fa": "👤 پروفایل",           "en": "👤 Profile"},
 "btn_support":       {"fa": "✍️ پشتیبانی",          "en": "✍️ Support"},
 "btn_invite":        {"fa": "🎁 دعوت دوستان",       "en": "🎁 Invite Friends"},
 "btn_lang":          {"fa": "🌐 زبان",              "en": "🌐 Language"},
 "btn_admin":         {"fa": "⚙️ پنل مدیریت",        "en": "⚙️ Admin Panel"},
 "btn_back":          {"fa": "« بازگشت",             "en": "« Back"},
 "btn_settings":      {"fa": "⚙️ تنظیمات",           "en": "⚙️ Settings"},
 "btn_tickets":       {"fa": "🎫 تیکت‌های من",       "en": "🎫 My Tickets"},
 "btn_new_ticket":    {"fa": "➕ تیکت جدید",         "en": "➕ New Ticket"},
 # ── محصولات ──
 "no_products":       {"fa": "😔 فعلاً محصولی موجود نیست.", "en": "😔 No products available yet."},
 "pick_cat":          {"fa": "🗂 <b>دسته‌بندی محصولات:</b>", "en": "🗂 <b>Product Categories:</b>"},
 "pick_prod":         {"fa": "📁 یک محصول انتخاب کنید:",    "en": "📁 Select a product:"},
 "sold":              {"fa": "🛒 فروخته شده",   "en": "🛒 Sold"},
 "price":             {"fa": "💵 قیمت",         "en": "💵 Price"},
 "stock":             {"fa": "📦 موجودی",       "en": "📦 In stock"},
 "out_stock":         {"fa": "❌ ناموجود",      "en": "❌ Out of stock"},
 "buy_now":           {"fa": "🛍 خرید (تحویل آنی ⚡️)", "en": "🛍 Buy (Instant ⚡️)"},
 "warranty_badge":    {"fa": "🛡 دارای گارانتی", "en": "🛡 Warranty Included"},
 "features_label":    {"fa": "✨ امکانات:",     "en": "✨ Features:"},
 # ── خرید ──
 "confirm_buy":       {"fa": "🧾 <b>تأیید خرید</b>",   "en": "🧾 <b>Confirm Purchase</b>"},
 "your_balance":      {"fa": "💰 موجودی شما",           "en": "💰 Your balance"},
 "apply_code":        {"fa": "🎟 اعمال کد تخفیف",      "en": "🎟 Apply Discount Code"},
 "confirm":           {"fa": "✅ تأیید و خرید",         "en": "✅ Confirm & Buy"},
 "cancel":            {"fa": "❌ انصراف",               "en": "❌ Cancel"},
 "enter_code":        {"fa": "🎟 کد تخفیف را ارسال کنید:", "en": "🎟 Send your discount code:"},
 "code_ok":           {"fa": "🎉 کد تخفیف اعمال شد!",  "en": "🎉 Discount applied!"},
 "code_bad":          {"fa": "❌ کد تخفیف نامعتبر یا منقضی است.", "en": "❌ Invalid or expired code."},
 "no_balance":        {"fa": "😕 موجودی حساب شما کافی نیست!", "en": "😕 Insufficient balance!"},
 "no_stock":          {"fa": "😔 موجودی این محصول تمام شد.", "en": "😔 This product is out of stock."},
 "buy_ok":            {"fa": "🎉 <b>خرید موفق!</b>",   "en": "🎉 <b>Purchase Successful!</b>"},
 "your_item":         {"fa": "🎁 <b>اطلاعات اشتراک شما:</b>", "en": "🎁 <b>Your subscription details:</b>"},
 "save_it":           {"fa": "⚠️ این اطلاعات را ذخیره کنید.", "en": "⚠️ Please save this information."},
 "ask_qty":           {"fa": "🔢 تعداد خرید را وارد کنید (موجودی: {s}):", "en": "🔢 Enter quantity (available: {s}):"},
 "qty_invalid":       {"fa": "❌ عدد نامعتبر یا بیشتر از موجودی است. دوباره وارد کنید:", "en": "❌ Invalid quantity or exceeds stock. Try again:"},
 # ── سفارش‌ها ──
 "no_orders":         {"fa": "📭 شما هنوز سفارشی ندارید.", "en": "📭 You have no orders yet."},
 "orders_title":      {"fa": "📊 <b>سفارش‌های اخیر:</b>", "en": "📊 <b>Recent Orders:</b>"},
 "warranty_claim_btn":{"fa": "🛡 درخواست گارانتی",        "en": "🛡 Warranty Claim"},
 "warranty_reason":   {"fa": "📝 دلیل مشکل را توضیح دهید:", "en": "📝 Describe the issue:"},
 "warranty_submitted":{"fa": "✅ درخواست گارانتی ثبت شد. به‌زودی بررسی می‌شود.", "en": "✅ Warranty claim submitted. We'll review it soon."},
 "warranty_approved_user":{"fa": "✅ درخواست گارانتی شما (سفارش #{oid}) تأیید شد.", "en": "Your warranty claim (order #{oid}) was approved."},
 "warranty_rejected_user":{"fa": "❌ درخواست گارانتی شما (سفارش #{oid}) رد شد.", "en": "Your warranty claim (order #{oid}) was rejected."},
 "warranty_resend_content":{"fa": "محتوای تعویضی شما (به دلیل تأیید گارانتی):\n\n{content}", "en": "Your replacement content (warranty approved):\n\n{content}"},
 # ── پروفایل ──
 "profile":           {"fa": "👤 <b>پروفایل شما</b>",   "en": "👤 <b>Your Profile</b>"},
 "joined":            {"fa": "📅 عضویت",                "en": "📅 Joined"},
 "referrals":         {"fa": "👥 زیرمجموعه‌ها",         "en": "👥 Referrals"},
 "total_orders":      {"fa": "🛒 کل سفارش‌ها",          "en": "🛒 Total Orders"},
 "total_spent":       {"fa": "💸 کل خرید",              "en": "💸 Total Spent"},
 "ref_earnings_lbl":  {"fa": "💰 درآمد رفرال",          "en": "💰 Referral Earnings"},
 "account_age":       {"fa": "⏳ عمر اکانت",            "en": "⏳ Account age"},
 "account_age_days":  {"fa": "{d} روز",                 "en": "{d} days"},
 # ── شارژ ──
 "recharge_title":    {"fa": "💰 <b>شارژ حساب</b>\n\nروش پرداخت را انتخاب کنید:",
                       "en": "💰 <b>Recharge Balance</b>\n\nChoose a payment method:"},
 "pay_usdt":          {"fa": "💎 پرداخت USDT (BEP20)",  "en": "💎 USDT Payment (BEP20)"},
 "pay_card":          {"fa": "💳 کارت به کارت (ریالی)", "en": "💳 Bank Card (IRR)"},
 "card_only_fa":      {"fa": "⚠️ کارت به کارت فقط برای کاربران ایرانی (زبان فارسی) است.",
                       "en": "⚠️ Card payment is only available for Iranian users (Persian language)."},
 "usdt_guide":        {"fa": "💎 <b>پرداخت با USDT — شبکه BEP20 (BSC)</b>\n\n1️⃣ مبلغ را به آدرس زیر واریز کنید:\n<code>{w}</code>\n\n⚠️ فقط شبکه <b>BEP20</b> | حداقل: <b>${m}</b>\n\n2️⃣ سپس هش تراکنش (TXID) را ارسال کنید.\n✨ تأیید کاملاً خودکار است!",
                       "en": "💎 <b>USDT Payment — BEP20 (BSC)</b>\n\n1️⃣ Send funds to:\n<code>{w}</code>\n\n⚠️ Only <b>BEP20</b> network | Min: <b>${m}</b>\n\n2️⃣ Then send the transaction hash (TXID).\n✨ Verification is fully automatic!"},
 "send_tx":           {"fa": "📤 ارسال هش تراکنش",     "en": "📤 Send TX Hash"},
 "ask_tx":            {"fa": "📤 هش تراکنش (TXID) را ارسال کنید:", "en": "📤 Send your transaction hash (TXID):"},
 "checking":          {"fa": "⏳ در حال بررسی تراکنش...", "en": "⏳ Verifying transaction..."},
 "tx_ok":             {"fa": "🎉 <b>پرداخت تأیید شد!</b>", "en": "🎉 <b>Payment Confirmed!</b>"},
 "tx_used":           {"fa": "❌ این هش قبلاً استفاده شده!", "en": "❌ This hash was already used!"},
 "tx_bad_format":     {"fa": "❌ فرمت هش نامعتبر است.", "en": "❌ Invalid hash format."},
 "usd_rate":          {"fa": "💱 نرخ دلار: <b>{r:,} تومان</b>", "en": "💱 USD Rate: <b>{r:,} Toman</b>"},
 "card_guide":        {"fa": "💳 <b>پرداخت کارت به کارت</b>\n\n💳 شماره کارت:\n<code>{c}</code>\n👤 به نام: {h}\n{rate_line}\n\n1️⃣ ابتدا مبلغ موردنظر (به دلار) را ارسال کنید:",
                       "en": "💳 <b>Card Payment (Iran)</b>\n\n💳 Card:\n<code>{c}</code>\n👤 Holder: {h}\n{rate_line}\n\n1️⃣ First, send the amount in USD:"},
 "card_rate_live":    {"fa": "💱 نرخ لحظه‌ای: هر دلار = <b>{r:,} تومان</b>",
                       "en": "💱 Live rate: $1 = <b>{r:,} Toman</b>"},
 "card_send_photo":   {"fa": "✅ مبلغ: <b>${a}</b> = <b>{t:,} تومان</b>\n\n2️⃣ پس از واریز، <b>عکس رسید</b> را همینجا ارسال کنید. 📸",
                       "en": "✅ Amount: <b>${a}</b> = <b>{t:,} Toman</b>\n\n2️⃣ After payment, send the <b>receipt photo</b> here. 📸"},
 "card_pending":      {"fa": "⏳ رسید شما ارسال شد و در انتظار تأیید است.\n🔔 پس از تأیید، حساب شما شارژ می‌شود.",
                       "en": "⏳ Receipt submitted. Waiting for approval.\n🔔 Your balance will be added after approval."},
 "card_auto_approved":{"fa": "🎉 پرداخت شما به‌صورت خودکار تأیید شد! حساب شارژ شد. 💰",
                       "en": "🎉 Payment auto-approved! Balance added. 💰"},
 "card_approved":     {"fa": "🎉 پرداخت شما تأیید شد! حساب شارژ شد. 💰", "en": "🎉 Payment approved! Balance added. 💰"},
 "card_rejected":     {"fa": "❌ پرداخت شما رد شد. با پشتیبانی تماس بگیرید.", "en": "❌ Payment rejected. Contact support."},
 # ── رفرال ──
 "invite_text":       {"fa": "🎁 <b>دعوت دوستان</b>\n\n🔗 لی��ک اختصاصی شما:\n{link}\n\n💸 با هر واریز زیرمجموعه، <b>{p}%</b> پورسانت می‌گیرید!\n👥 زیرمجموعه‌ها: <b>{c}</b>\n💰 درآمد رفرال: <b>${e:.2f}</b>\n\n⚠️ کاربر جدید باید حداقل {d} روزه از تلگرام باشد.",
                       "en": "🎁 <b>Invite Friends</b>\n\n🔗 Your link:\n{link}\n\n💸 Earn <b>{p}%</b> of every referral deposit!\n👥 Referrals: <b>{c}</b>\n💰 Earnings: <b>${e:.2f}</b>\n\n⚠️ New user must have Telegram account older than {d} days."},
 "ref_bonus":         {"fa": "🎉 پورسانت رفرال: <b>${a:.2f}</b> به حساب شما اضافه شد!", "en": "🎉 Referral bonus: <b>${a:.2f}</b> added to your balance!"},
 "ref_too_new":       {"fa": "⚠️ این کاربر به تازگی تلگرام را نصب کرده و شرط {d} روز را ندارد.",
                       "en": "⚠️ This user's Telegram account is too new (requires {d}+ days)."},
 # ── پشتیبانی ──
 "support_text":      {"fa": "✍️ <b>پشتیبانی</b>\n\n📞 ارتباط مستقیم: {s}\n\n🎫 یا یک تیکت ارسال کنید:",
                       "en": "✍️ <b>Support</b>\n\n📞 Direct contact: {s}\n\n🎫 Or open a ticket:"},
 "ticket_subject":    {"fa": "📝 موضوع تیکت را بنویسید:", "en": "📝 Enter ticket subject:"},
 "ticket_message":    {"fa": "✍️ پیام تیکت را بنویسید:", "en": "✍️ Write your ticket message:"},
 "ticket_sent":       {"fa": "✅ تیکت #{id} ثبت شد. به‌زودی پاسخ داده می‌شود.", "en": "✅ Ticket #{id} submitted. We'll reply soon."},
 "no_tickets":        {"fa": "📭 تیکتی ندارید.", "en": "📭 No tickets found."},
 "tickets_list":      {"fa": "🎫 <b>تیکت‌های شما:</b>", "en": "🎫 <b>Your Tickets:</b>"},
 "ticket_status_open":    {"fa": "🟡 باز",      "en": "🟡 Open"},
 "ticket_status_answered":{"fa": "🟢 پاسخ داده شده", "en": "🟢 Answered"},
 "ticket_status_closed":  {"fa": "⚪️ بسته شده", "en": "⚪️ Closed"},
 "ticket_detail":     {"fa": "🎫 <b>تیکت #{id}</b>\n📌 موضوع: {subject}\n📊 وضعیت: {status}\n\n📝 پیام:\n{message}\n\n{reply_section}",
                       "en": "🎫 <b>Ticket #{id}</b>\n📌 Subject: {subject}\n📊 Status: {status}\n\n📝 Message:\n{message}\n\n{reply_section}"},
 "ticket_reply_section": {"fa": "💬 پاسخ ادمین:\n{reply}", "en": "💬 Admin reply:\n{reply}"},
 # ── اطلاع‌رسانی ──
 "new_product":       {"fa": "🔥 <b>محصول جدید اضافه شد!</b>\n\n📦 {name}\n💵 ${price}\n\n👇 برای خرید وارد ربات شوید!",
                       "en": "🔥 <b>New Product Added!</b>\n\n📦 {name}\n💵 ${price}\n\n👇 Open the bot to purchase!"},
 "blocked":           {"fa": "⛔️ شما مسدود شده‌اید.", "en": "⛔️ You are blocked."},
 "registration_locked_msg": {"fa": "🔒 عضویت کاربران جدید موقتاً بسته شده است. لطفاً بعداً دوباره تلاش کنید.",
                       "en": "🔒 New user registration is temporarily closed. Please try again later."},
 "maintenance_default": {"fa": "🛠 ربات موقتاً در حال تعمیر و به‌روزرسانی است. لطفاً کمی بعد دوباره تلاش کنید.",
                       "en": "🛠 The bot is temporarily under maintenance. Please try again shortly."},
 "daily_limit_reached": {"fa": "⛔️ شما به سقف خرید روزانه ({n} خرید) رسیده‌اید. فردا دوباره تلاش کنید.",
                       "en": "⛔️ You've reached the daily purchase limit ({n} purchases). Try again tomorrow."},
 # ── کیبورد پایین ──
 "kb_start":          {"fa": "🏠 منوی اصلی",   "en": "🏠 Main Menu"},
 "kb_products":       {"fa": "🛍 محصولات",     "en": "🛍 Products"},
 "kb_support":        {"fa": "✍️ پشتیبانی",    "en": "✍️ Support"},
 "kb_lang":           {"fa": "🌐 زبان",        "en": "🌐 Language"},

 # ══════════════════════════════════════════
 # ── پنل ادمین ──
 # ══════════════════════════════════════════
 "adm_panel":         {"fa": "⚙️ <b>پنل مدیریت</b>", "en": "⚙️ <b>Admin Panel</b>"},
 "adm_users_lbl":     {"fa": "👥 کاربران: <b>{u}</b> (مسدود: {b})", "en": "👥 Users: <b>{u}</b> (blocked: {b})"},
 "adm_orders_lbl":    {"fa": "🛒 سفارش‌ها: <b>{o}</b> | امروز: <b>{t}</b>", "en": "🛒 Orders: <b>{o}</b> | Today: <b>{t}</b>"},
 "adm_revenue_lbl":   {"fa": "💵 درآمد کل: <b>${r:.2f}</b> | امروز: <b>${tr:.2f}</b>", "en": "💵 Total Revenue: <b>${r:.2f}</b> | Today: <b>${tr:.2f}</b>"},
 "adm_deposits_lbl":  {"fa": "💰 واریزها: <b>${d:.2f}</b>", "en": "💰 Deposits: <b>${d:.2f}</b>"},
 "adm_tickets_lbl":   {"fa": "🎫 تیکت‌های باز: <b>{n}</b>", "en": "🎫 Open Tickets: <b>{n}</b>"},
 "adm_cards_lbl":     {"fa": "💳 پرداخت‌های ��ر انتظار: <b>{n}</b>", "en": "💳 Pending Payments: <b>{n}</b>"},
 "adm_warranty_lbl":  {"fa": "🛡 گارانتی‌های در انتظار: <b>{n}</b>", "en": "🛡 Pending Warranty: <b>{n}</b>"},
 # دکمه‌های پنل ادمین
 "adm_btn_products":  {"fa": "📦 مدیریت محصولات", "en": "📦 Products"},
 "adm_btn_users":     {"fa": "👥 مدیریت کاربران", "en": "👥 Users"},
 "adm_btn_codes":     {"fa": "🎟 کدهای تخفیف",   "en": "🎟 Discount Codes"},
 "adm_btn_cards":     {"fa": "💳 پرداخت‌های کارتی","en": "💳 Card Payments"},
 "adm_btn_tickets":   {"fa": "🎫 تیکت‌ها",        "en": "🎫 Tickets"},
 "adm_btn_warranty":  {"fa": "🛡 گارانتی‌ها",     "en": "🛡 Warranties"},
 "adm_btn_lock":      {"fa": "🔒 قفل گروه/کانال", "en": "🔒 Lock Group/Channel"},
 "adm_btn_admins":    {"fa": "👮 مدیریت ادمین‌ها", "en": "👮 Admins"},
 "adm_btn_payment":   {"fa": "💰 متدهای پرداخت",  "en": "💰 Payment Methods"},
 "adm_btn_apis":      {"fa": "🔌 API ها",          "en": "🔌 APIs"},
 "adm_btn_settings":  {"fa": "⚙️ تنظیمات",         "en": "⚙️ Settings"},
 "adm_btn_broadcast": {"fa": "📢 پیام همگانی",     "en": "📢 Broadcast"},
 # مدیریت محصولات
 "adm_products_title":{"fa": "📦 <b>مدیریت محصولات</b>", "en": "📦 <b>Product Management</b>"},
 "adm_btn_addcat":    {"fa": "➕ دسته جدید",       "en": "➕ New Category"},
 "adm_btn_delcat":    {"fa": "🗑 حذف دسته",        "en": "🗑 Delete Category"},
 "adm_btn_addprod":   {"fa": "➕ محصول جدید",      "en": "➕ New Product"},
 "adm_btn_delprod":   {"fa": "🗑 حذف محصول",       "en": "🗑 Delete Product"},
 "adm_btn_addstock":  {"fa": "📦 افزودن موجودی",   "en": "📦 Add Stock"},
 "adm_btn_price":     {"fa": "💲 تغییر قیمت",      "en": "💲 Change Price"},
 "adm_btn_editprod":  {"fa": "✏️ ویرایش محصول",    "en": "✏️ Edit Product"},
 "adm_btn_banner":    {"fa": "🖼 بنر محصول",        "en": "🖼 Product Banner"},
 "adm_btn_toggle":    {"fa": "🔄 فعال/غیرفعال",    "en": "🔄 Toggle Active"},
 "adm_btn_prodstats": {"fa": "📊 آمار محصولات",    "en": "📊 Product Stats"},
 "adm_ask_cat_name":  {"fa": "➕ نام دسته را ارسال کنید:", "en": "➕ Send the category name:"},
 "adm_ask_delcat":    {"fa": "حذف کدام دسته؟",    "en": "Which category to delete?"},
 "adm_cat_deleted":   {"fa": "✅ دسته حذف شد.",    "en": "✅ Category deleted."},
 "adm_cat_added":     {"fa": "✅ دسته ساخته شد.",  "en": "✅ Category created."},
 "adm_no_cats":       {"fa": "❌ دسته‌ای وجود ندارد.", "en": "❌ No categories found."},
 "adm_no_prods":      {"fa": "❌ محصولی وجود ندارد.", "en": "❌ No products found."},
 "adm_ask_which_cat": {"fa": "در کدام دسته؟",     "en": "Which category?"},
 "adm_ask_which_prod":{"fa": "انتخاب محصول:",     "en": "Select product:"},
 "adm_prod_deleted":  {"fa": "✅ محصول حذف شد.",   "en": "✅ Product deleted."},
 "adm_prod_toggled_on": {"fa": "✅ محصول فعال شد.", "en": "✅ Product activated."},
 "adm_prod_toggled_off":{"fa": "✅ محصول غیرفعال شد.", "en": "✅ Product deactivated."},
 "adm_prod_edited":   {"fa": "✅ محصول ویرایش شد.", "en": "✅ Product updated."},
 "adm_banner_set":    {"fa": "✅ بنر محصول تنظیم شد.", "en": "✅ Product banner set."},
 "adm_stock_added":   {"fa": "✅ {n} آیتم اضافه شد.", "en": "✅ {n} items added."},
 "adm_price_updated": {"fa": "✅ قیمت به‌روز شد.", "en": "✅ Price updated."},
 # افزودن محصول مرحله به مرحله
 "adm_addprod_step1": {"fa": "➕ <b>افزودن محصول — مرحله ۱/۵</b>\n\n📝 نام محصول را ارسال کنید:",
                       "en": "➕ <b>Add Product — Step 1/5</b>\n\n📝 Send the product name:"},
 "adm_addprod_step2": {"fa": "➕ <b>افزودن محصول — مرحله ۲/۵</b>\n\n💵 قیمت محصول را به دلار وارد کنید:\nمثال: <code>9.99</code>",
                       "en": "➕ <b>Add Product — Step 2/5</b>\n\n💵 Enter the price in USD:\nExample: <code>9.99</code>"},
 "adm_addprod_step3": {"fa": "➕ <b>افزودن محصول — مرحله ۳/۵</b>\n\n📝 توضیحات محصول را وارد کنید:",
                       "en": "➕ <b>Add Product — Step 3/5</b>\n\n📝 Enter the product description:"},
 "adm_addprod_step4": {"fa": "➕ <b>افزودن محصول — مرحله ۴/۵</b>\n\n✨ امکانات محصول را وارد کنید (هر امکان در یک خط):\nیا <code>-</code> بفرستید تا رد شود.",
                       "en": "➕ <b>Add Product — Step 4/5</b>\n\n✨ Enter product features (one per line):\nOr send <code>-</code> to skip."},
 "adm_addprod_step5": {"fa": "➕ <b>افزودن محصول — مرحله ۵/۵</b>\n\n🛡 آیا این محصول گارانتی دارد؟",
                       "en": "➕ <b>Add Product — Step 5/5</b>\n\n🛡 Does this product have a warranty?"},
 "adm_warranty_yes":  {"fa": "✅ بله، گارانتی دارد", "en": "✅ Yes, has warranty"},
 "adm_warranty_no":   {"fa": "❌ خیر",              "en": "❌ No"},
 "adm_prod_added":    {"fa": "✅ <b>محصول اضافه شد!</b>\n\n🆔 ID: <code>{pid}</code>\n📦 نام: {name}\n💵 قیمت: ${price}\n🛡 گارانتی: {warranty}\n\n📢 در حال اطلاع‌رسانی...",
                       "en": "✅ <b>Product added!</b>\n\n🆔 ID: <code>{pid}</code>\n📦 Name: {name}\n💵 Price: ${price}\n🛡 Warranty: {warranty}\n\n📢 Broadcasting..."},
 "adm_warranty_has":  {"fa": "دارد", "en": "Yes"},
 "adm_warranty_none": {"fa": "ندارد", "en": "No"},
 "adm_btn_addstock_now": {"fa": "📦 افزودن موجودی", "en": "📦 Add Stock"},
 "adm_ask_stock":     {"fa": "📦 اکانت‌ها را ارسال کنید (هر خط یک اکانت):", "en": "📦 Send accounts (one per line):"},
 "adm_ask_price":     {"fa": "💲 قیمت جدید (دلار):", "en": "💲 New price (USD):"},
 "adm_ask_banner":    {"fa": "🖼 لینک تصویر بنر را ارسال کنید (یا عکس بفرستید):", "en": "🖼 Send banner image URL (or send a photo):"},
 "adm_ask_editprod":  {"fa": "✏️ ویرایش محصول: <b>{name}</b>\n\nاطلاعات جدید را ارسال کنید:\n<code>نام\nقیمت\nتوضیحات\nامکانات (اختیاری)</code>",
                       "en": "✏️ Edit product: <b>{name}</b>\n\nSend new info:\n<code>Name\nPrice\nDescription\nFeatures (optional)</code>"},
 "adm_prodstats_title":{"fa": "📊 <b>آمار محصولات:</b>", "en": "📊 <b>Product Stats:</b>"},
 "adm_prodstats_row": {"fa": "📦 <b>{name}</b>\n   💵 ${price} | 📦 موجودی: {stock} | 🛒 فروش: {sold}\n   {status}\n\n",
                       "en": "📦 <b>{name}</b>\n   💵 ${price} | 📦 Stock: {stock} | 🛒 Sold: {sold}\n   {status}\n\n"},
 "adm_active":        {"fa": "✅ فعال", "en": "✅ Active"},
 "adm_inactive":      {"fa": "❌ غیرفعال", "en": "❌ Inactive"},
 # مدیریت کاربران
 "adm_users_title":   {"fa": "👥 <b>مدیریت کاربران</b>\n\nکل: {total} | مسدود: {blocked}",
                       "en": "👥 <b>User Management</b>\n\nTotal: {total} | Blocked: {blocked}"},
 "adm_btn_userinfo":  {"fa": "🔍 جستجوی کاربر",    "en": "🔍 Search User"},
 "adm_btn_addbal":    {"fa": "💰 شارژ کاربر",       "en": "💰 Add Balance"},
 "adm_btn_block":     {"fa": "🚫 مسدود/رفع مسدودی", "en": "🚫 Block/Unblock"},
 "adm_btn_usernote":  {"fa": "📝 یادداشت کاربر",    "en": "📝 User Note"},
 "adm_btn_userlist":  {"fa": "📋 لیست کاربران",     "en": "📋 User List"},
 "adm_btn_userstats": {"fa": "📊 آمار کاربر",       "en": "📊 User Stats"},
 "adm_btn_vip":       {"fa": "👑 مدیریت VIP",        "en": "👑 Manage VIP"},
 "adm_ask_vip":       {"fa": "👑 آیدی کاربر را ارسال کنید (وضعیت VIP برعکس می‌شود):", "en": "👑 Send user ID to toggle VIP status:"},
 "adm_vip_added":     {"fa": "✅ کاربر VIP شد.", "en": "✅ User is now VIP."},
 "adm_vip_removed":   {"fa": "✅ وضعیت VIP کاربر حذف شد.", "en": "✅ User is no longer VIP."},
 "adm_ask_userinfo":  {"fa": "🔍 آیدی عددی یا یوزرنیم کاربر را ارسال کنید:", "en": "🔍 Send user ID or username:"},
 "adm_ask_addbal":    {"fa": "💰 فرمت: <code>آیدی مبلغ</code>\nمثال: <code>123456789 10</code>", "en": "💰 Format: <code>user_id amount</code>\nExample: <code>123456789 10</code>"},
 "adm_ask_block":     {"fa": "🚫 آیدی کاربر را ارسال کنید (وضعیت مسدودی برعکس می‌شود):", "en": "🚫 Send user ID to toggle block status:"},
 "adm_ask_usernote_id":{"fa": "📝 آیدی کاربر را ارسال کنید:", "en": "📝 Send user ID:"},
 "adm_ask_usernote_text":{"fa": "📝 یادداشت فعلی: {note}\n\nیادداشت جدید را ارسال کنید:", "en": "📝 Current note: {note}\n\nSend new note:"},
 "adm_ask_userstats": {"fa": "📊 آیدی کاربر را ارسال کنید:", "en": "📊 Send user ID:"},
 "adm_user_not_found":{"fa": "❌ کاربر یافت نشد.", "en": "❌ User not found."},
 "adm_bal_added":     {"fa": "✅ ${amount} به کاربر {uid} شارژ شد.", "en": "✅ ${amount} added to user {uid}."},
 "adm_bal_notify":    {"fa": "💰 +${amount} به حساب شما اضافه شد! 🎉", "en": "💰 +${amount} added to your balance! 🎉"},
 "adm_blocked":       {"fa": "✅ کاربر مسدود شد.", "en": "✅ User blocked."},
 "adm_unblocked":     {"fa": "✅ کاربر رفع مسدودی شد.", "en": "✅ User unblocked."},
 "adm_note_saved":    {"fa": "✅ یادداشت ذخیره شد.", "en": "✅ Note saved."},
 "adm_userlist_title":{"fa": "📋 <b>آخرین کاربران:</b>", "en": "📋 <b>Recent Users:</b>"},
 "adm_userinfo_text": {"fa": "👤 <code>{uid}</code> | @{username}\n💰 موجودی: ${balance:.2f}\n💸 کل خرید: ${spent:.2f}\n🛒 سفارش‌ها: {orders}\n👥 رفرال‌ها: {refs}\n💰 درآمد رفرال: ${ref_earn:.2f}\n⏳ سن اکانت: ~{age} روز\n🚫 مسدود: {blocked}\n📝 یادداشت: {note}\n📅 عضویت: {joined}",
                       "en": "👤 <code>{uid}</code> | @{username}\n💰 Balance: ${balance:.2f}\n💸 Total Spent: ${spent:.2f}\n🛒 Orders: {orders}\n👥 Referrals: {refs}\n💰 Ref Earnings: ${ref_earn:.2f}\n⏳ Account Age: ~{age} days\n🚫 Blocked: {blocked}\n📝 Note: {note}\n📅 Joined: {joined}"},
 "adm_yes":           {"fa": "بله", "en": "Yes"},
 "adm_no":            {"fa": "خیر", "en": "No"},
 "adm_userstats_text":{"fa": "📊 <b>آمار کاربر {uid}</b>\n\n💰 موجودی: ${balance:.2f}\n💸 کل خرید: ${spent:.2f}\n🛒 کل سفارش‌ها: {orders}\n👥 رفرال‌ها: {refs}\n💰 درآمد رفرال: ${ref_earn:.2f}\n⏳ سن اکانت: ~{age} روز",
                       "en": "📊 <b>User Stats {uid}</b>\n\n💰 Balance: ${balance:.2f}\n💸 Total Spent: ${spent:.2f}\n🛒 Total Orders: {orders}\n👥 Referrals: {refs}\n💰 Ref Earnings: ${ref_earn:.2f}\n⏳ Account Age: ~{age} days"},
 "adm_last_orders":   {"fa": "🛒 آخرین سفارش‌ها:", "en": "🛒 Recent orders:"},
 "adm_invalid_id":    {"fa": "❌ آیدی نامعتبر! دوباره وارد کنید:", "en": "❌ Invalid ID! Try again:"},
 "adm_invalid_format":{"fa": "❌ فرمت نادرست! دوباره وارد کنید:", "en": "❌ Invalid format! Try again:"},
 "adm_invalid_price": {"fa": "❌ قیمت نامعتبر! یک عدد مثبت وارد کنید:", "en": "❌ Invalid price! Enter a positive number:"},
 "adm_invalid_number":{"fa": "❌ عدد نامعتبر! دوباره وارد کنید:", "en": "❌ Invalid number! Try again:"},
 # کدهای تخفیف
 "adm_codes_title":   {"fa": "🎟 <b>کدهای تخفیف:</b>", "en": "🎟 <b>Discount Codes:</b>"},
 "adm_codes_empty":   {"fa": "خالی", "en": "Empty"},
 "adm_btn_addcode":   {"fa": "➕ کد جدید", "en": "➕ New Code"},
 "adm_ask_addcode":   {"fa": "🎟 فرمت: <code>کد درصد تعداد‌استفاده</code>\nمثال: <code>OFF20 20 50</code>", "en": "🎟 Format: <code>CODE percent max_uses</code>\nExample: <code>OFF20 20 50</code>"},
 "adm_code_added":    {"fa": "✅ کد <code>{code}</code> ساخته شد.", "en": "✅ Code <code>{code}</code> created."},
 "adm_code_deleted":  {"fa": "✅ کد حذف شد.", "en": "✅ Code deleted."},
 # پرداخت‌های کارتی
 "adm_cards_title":   {"fa": "💳 <b>پرداخت‌های در انتظار ({n}):</b>", "en": "💳 <b>Pending Payments ({n}):</b>"},
 "adm_no_cards":      {"fa": "✅ پرداخت در انتظاری وجود ندارد.", "en": "✅ No pending payments."},
 # تیکت‌ها
 "adm_tickets_title": {"fa": "🎫 <b>تیکت‌های باز ({n}):</b>", "en": "🎫 <b>Open Tickets ({n}):</b>"},
 "adm_no_tickets":    {"fa": "✅ تیکت باز وجود ندارد.", "en": "✅ No open tickets."},
 "adm_ticket_detail": {"fa": "🎫 <b>تیکت #{id}</b>\n👤 @{username} | <code>{uid}</code>\n📌 موضوع: {subject}\n📊 وضعیت: {status}\n\n📝 پیام:\n{message}\n\n{reply}",
                       "en": "🎫 <b>Ticket #{id}</b>\n👤 @{username} | <code>{uid}</code>\n📌 Subject: {subject}\n📊 Status: {status}\n\n📝 Message:\n{message}\n\n{reply}"},
 "adm_ticket_prev_reply":{"fa": "💬 پاسخ قبلی:\n{reply}", "en": "💬 Previous reply:\n{reply}"},
 "adm_btn_reply":     {"fa": "💬 پاسخ دادن",  "en": "💬 Reply"},
 "adm_btn_close_ticket":{"fa": "✅ بستن تیکت","en": "✅ Close Ticket"},
 "adm_ask_ticket_reply":{"fa": "💬 پاسخ به تیکت #{id} را ارسال کنید:", "en": "💬 Send reply for ticket #{id}:"},
 "adm_ticket_replied":{"fa": "✅ پاسخ به تیکت #{id} ارسال شد.", "en": "✅ Reply sent for ticket #{id}."},
 "adm_ticket_closed": {"fa": "✅ تیکت بسته شد.", "en": "✅ Ticket closed."},
 "adm_ticket_not_found":{"fa": "❌ تیکت یافت نشد.", "en": "❌ Ticket not found."},
 "adm_ticket_reply_notify":{"fa": "💬 <b>پاسخ تیکت #{id}</b>\n\n{reply}", "en": "💬 <b>Ticket #{id} Reply</b>\n\n{reply}"},
 # گارانتی‌ها
 "adm_warranty_title":{"fa": "🛡 <b>درخواست‌های گارانتی ({n}):</b>", "en": "🛡 <b>Warranty Claims ({n}):</b>"},
 "adm_no_warranty":   {"fa": "✅ درخواست گارانتی در انتظاری وجود ندارد.", "en": "✅ No pending warranty claims."},
 # قفل گروه/کانال
 "adm_lock_title":    {"fa": "🔒 <b>مدیریت قفل گروه/ک��نال</b>\n\n📢 کانال‌های قفل‌شده: {ch}\n👥 گروه‌های قفل‌شده: {gr}",
                       "en": "🔒 <b>Lock Management</b>\n\n📢 Locked Channels: {ch}\n👥 Locked Groups: {gr}"},
 "adm_locked_channels":{"fa": "📢 کانال‌ها:", "en": "📢 Channels:"},
 "adm_locked_groups": {"fa": "👥 گروه‌ها:",  "en": "👥 Groups:"},
 "adm_btn_lock_ch":   {"fa": "🔒 قفل کانال",      "en": "🔒 Lock Channel"},
 "adm_btn_unlock_ch": {"fa": "🔓 رفع قفل کانال",  "en": "🔓 Unlock Channel"},
 "adm_btn_lock_gr":   {"fa": "🔒 قفل گروه",       "en": "🔒 Lock Group"},
 "adm_btn_unlock_gr": {"fa": "🔓 رفع قفل گروه",   "en": "🔓 Unlock Group"},
 "adm_ask_lock_ch":   {"fa": "📢 آیدی کانال را ارسال کنید:\nمثال: <code>-1001234567890 نام کانال</code>",
                       "en": "📢 Send channel ID:\nExample: <code>-1001234567890 Channel Name</code>"},
 "adm_ask_lock_gr":   {"fa": "👥 آیدی گروه را ارسال کنید:\nمثال: <code>-1001234567890 نام گروه</code>",
                       "en": "👥 Send group ID:\nExample: <code>-1001234567890 Group Name</code>"},
 "adm_ch_locked":     {"fa": "✅ کانال <b>{title}</b> قفل شد.", "en": "✅ Channel <b>{title}</b> locked."},
 "adm_gr_locked":     {"fa": "✅ گروه <b>{title}</b> قفل شد.", "en": "✅ Group <b>{title}</b> locked."},
 "adm_ch_unlocked":   {"fa": "✅ قفل کانال برداشته شد.", "en": "✅ Channel unlocked."},
 "adm_gr_unlocked":   {"fa": "✅ قفل گروه برداشته شد.", "en": "✅ Group unlocked."},
 "adm_no_locked_ch":  {"fa": "❌ کانال قفل‌شده‌ای وجود ندارد.", "en": "❌ No locked channels."},
 "adm_no_locked_gr":  {"fa": "❌ گروه قفل‌شده‌ای وجود ندارد.", "en": "❌ No locked groups."},
 "adm_ask_unlock_ch": {"fa": "رفع قفل کدام کانال؟", "en": "Which channel to unlock?"},
 "adm_ask_unlock_gr": {"fa": "رفع قفل کدام گروه؟",  "en": "Which group to unlock?"},
 # مدیریت ادمین‌ها
 "adm_admins_title":  {"fa": "👮 <b>مدیریت ادمین‌ها</b>", "en": "👮 <b>Admin Management</b>"},
 "adm_no_admins":     {"fa": "ادمینی وجود ندارد.", "en": "No admins found."},
 "adm_super":         {"fa": "⭐️ سوپر", "en": "⭐️ Super"},
 "adm_regular":       {"fa": "👮 ادمین", "en": "👮 Admin"},
 "adm_perm_lbl":      {"fa": "دسترسی", "en": "Perms"},
 "adm_btn_addadmin":  {"fa": "➕ افزودن ادمین",   "en": "➕ Add Admin"},
 "adm_btn_deladmin":  {"fa": "🗑 حذف ادمین",      "en": "🗑 Remove Admin"},
 "adm_btn_editadmin": {"fa": "✏️ ویرایش دسترسی", "en": "✏️ Edit Permissions"},
 "adm_ask_addadmin":  {"fa": "➕ اطلاعات ادمین جدید:\n<code>آیدی دسترسی‌ها</code>\n\nدسترسی‌ها: <code>all</code> یا ترکیبی از:\n<code>products,users,tickets,payments,settings</code>\n\nمثال: <code>123456789 products,users</code>",
                       "en": "➕ New admin info:\n<code>user_id permissions</code>\n\nPermissions: <code>all</code> or combination of:\n<code>products,users,tickets,payments,settings</code>\n\nExample: <code>123456789 products,users</code>"},
 "adm_ask_editadmin": {"fa": "✏️ ویرایش دسترسی ادمین:\n<code>آیدی دسترسی‌های_جدید</code>\n\nمثال: <code>123456789 products,tickets</code>",
                       "en": "✏️ Edit admin permissions:\n<code>user_id new_permissions</code>\n\nExample: <code>123456789 products,tickets</code>"},
 "adm_ask_deladmin":  {"fa": "حذف کدام ادمین؟", "en": "Which admin to remove?"},
 "adm_admin_added":   {"fa": "✅ ادمین <code>{uid}</code> با دسترسی <code>{perms}</code> اضافه شد.", "en": "✅ Admin <code>{uid}</code> added with permissions <code>{perms}</code>."},
 "adm_admin_deleted": {"fa": "✅ ادمین حذف شد.", "en": "✅ Admin removed."},
 "adm_admin_updated": {"fa": "✅ دسترسی‌های ادمین {uid} به‌روز شد.", "en": "✅ Admin {uid} permissions updated."},
 "adm_cant_del_main": {"fa": "❌ نمی‌توان ادمین اصلی را حذف کرد.", "en": "❌ Cannot remove the main admin."},
 # متدهای پرداخت
 "adm_payment_title": {"fa": "💰 <b>متدهای پرداخت</b>", "en": "💰 <b>Payment Methods</b>"},
 "adm_no_methods":    {"fa": "متدی وجود ندارد.", "en": "No methods found."},
 "adm_btn_addmethod": {"fa": "➕ افزودن متد",      "en": "➕ Add Method"},
 "adm_btn_delmethod": {"fa": "🗑 حذف متد",         "en": "🗑 Delete Method"},
 "adm_btn_togglemethod":{"fa": "🔄 فعال/غیرفعال", "en": "🔄 Toggle Active"},
 "adm_btn_setcard":   {"fa": "💳 تغییر شماره کارت","en": "💳 Change Card Number"},
 "adm_btn_setwallet": {"fa": "💎 تغییر آدرس ولت",  "en": "💎 Change Wallet Address"},
 "adm_ask_addmethod": {"fa": "➕ فرمت: <code>نام توضیحات</code>\nمثال: <code>crypto USDT TRC20</code>", "en": "➕ Format: <code>name details</code>\nExample: <code>crypto USDT TRC20</code>"},
 "adm_ask_delmethod": {"fa": "حذف کدام متد؟", "en": "Which method to delete?"},
 "adm_ask_togglemethod":{"fa": "انتخاب متد:", "en": "Select method:"},
 "adm_method_added":  {"fa": "✅ متد پرداخت <code>{name}</code> اضافه شد.", "en": "✅ Payment method <code>{name}</code> added."},
 "adm_method_deleted":{"fa": "✅ متد حذف شد.", "en": "✅ Method deleted."},
 "adm_method_toggled":{"fa": "✅ وضعیت تغییر کرد.", "en": "✅ Status changed."},
 "adm_ask_setcard":   {"fa": "💳 شماره کارت فعلی: <code>{card}</code>\n👤 نام صاحب کارت: {holder}\n\nفرمت جدید:\n<code>شماره-کارت نام-صاحب-کارت</code>\nمثال: <code>6037-1234-5678-9012 علی احمدی</code>",
                       "en": "💳 Current card: <code>{card}</code>\n👤 Holder: {holder}\n\nNew format:\n<code>card-number holder-name</code>\nExample: <code>6037-1234-5678-9012 Ali Ahmadi</code>"},
 "adm_card_updated":  {"fa": "✅ شماره کارت به‌روز شد:\n<code>{card}</code>\n👤 {holder}", "en": "✅ Card updated:\n<code>{card}</code>\n👤 {holder}"},
 "adm_ask_setwallet": {"fa": "💎 آدرس ولت فعلی:\n<code>{wallet}</code>\n\nآدرس جدید را ارسال کنید:", "en": "💎 Current wallet:\n<code>{wallet}</code>\n\nSend new address:"},
 "adm_wallet_updated":{"fa": "✅ آدرس ولت به‌روز شد:\n<code>{wallet}</code>", "en": "✅ Wallet updated:\n<code>{wallet}</code>"},
 "adm_invalid_wallet":{"fa": "❌ آدرس ولت نامعتبر! باید با 0x شروع شود و ۴۲ کاراکتر باشد. دوباره وارد کنید:", "en": "❌ Invalid wallet address! Must start with 0x and be 42 chars. Try again:"},
 # API ها
 "adm_apis_title":    {"fa": "🔌 <b>مدیریت API ها</b>", "en": "🔌 <b>API Management</b>"},
 "adm_no_apis":       {"fa": "API ای تنظیم نشده است.", "en": "No APIs configured."},
 "adm_ext_apis":      {"fa": "API های خارجی موجود در config:", "en": "External APIs in config:"},
 "adm_btn_addapi":    {"fa": "➕ افزودن API", "en": "➕ Add API"},
 "adm_btn_delapi":    {"fa": "🗑 حذف API",   "en": "🗑 Delete API"},
 "adm_btn_testapi":   {"fa": "🔌 تست API",   "en": "🔌 Test API"},
 "adm_ask_addapi":    {"fa": "➕ اطلاعات API:\n<code>نام URL کلید</code>\nمثال: <code>myapi https://api.example.com abc123</code>",
                       "en": "➕ API info:\n<code>name URL key</code>\nExample: <code>myapi https://api.example.com abc123</code>"},
 "adm_ask_delapi":    {"fa": "حذف کدام API؟", "en": "Which API to delete?"},
 "adm_api_added":     {"fa": "✅ API <code>{name}</code> اضافه شد.", "en": "✅ API <code>{name}</code> added."},
 "adm_api_deleted":   {"fa": "✅ API حذف شد.", "en": "✅ API deleted."},
 "adm_testapi_result":{"fa": "🔌 <b>تست API ها</b>\n\n💱 نرخ دلار: {rate:,} تومان\n✅ API نرخ دلار کار می‌کند.", "en": "🔌 <b>API Test</b>\n\n💱 USD Rate: {rate:,} Toman\n✅ USD rate API is working."},
 # تنظیمات
 "adm_settings_title":{"fa": "⚙️ <b>تنظیمات قابلیت‌ها</b>", "en": "⚙️ <b>Feature Settings</b>"},
 "adm_feature_toggled_on": {"fa": "✅ قابلیت فعال شد.", "en": "✅ Feature enabled."},
 "adm_feature_toggled_off":{"fa": "✅ قابلیت غیرفعال شد.", "en": "✅ Feature disabled."},
 "adm_features": {
     "fa": {
         "referral": "سیستم رفرال",
         "card_iranian_only": "کارت فقط ایرانی",
         "automatic_card_confirm": "تأیید خودکار کارت",
         "usd_rate": "نرخ دلار آنلاین",
         "tickets": "سیستم تیکت",
         "warranty": "سیستم گارانتی",
         "lock_groups": "قفل گروه",
         "lock_channels": "قفل کانال",
         "multi_admin": "چند ادمین",
         "maintenance_mode": "حالت تعمیر و نگهداری",
         "registration_locked": "قفل عضویت کاربران جدید",
         "daily_purchase_limit": "محدودیت خرید روزانه",
         "vip_mode": "حالت VIP",
     },
     "en": {
         "referral": "Referral System",
         "card_iranian_only": "Card Iranian Only",
         "automatic_card_confirm": "Auto Card Confirm",
         "usd_rate": "Live USD Rate",
         "tickets": "Ticket System",
         "warranty": "Warranty System",
         "lock_groups": "Lock Groups",
         "lock_channels": "Lock Channels",
         "multi_admin": "Multi Admin",
         "maintenance_mode": "Maintenance Mode",
         "registration_locked": "Registration Locked",
         "daily_purchase_limit": "Daily Purchase Limit",
         "vip_mode": "VIP Mode",
     }
 },
 # پیام همگانی
 "adm_ask_broadcast": {"fa": "📢 پیام همگانی را ارسال کنید:", "en": "📢 Send the broadcast message:"},
 "adm_broadcast_done":{"fa": "✅ به {n} کاربر ارسال شد.", "en": "✅ Sent to {n} users."},
}

# ═══════════ ایموجی پرمیوم (Premium / Custom Emoji) ═══════════
# Syntax usable in message texts AND button labels:  [emoji:ID:X]
#   ID = numeric custom_emoji_id of the premium emoji
#   X  = normal fallback emoji (shown in buttons and to non-premium users)
_PREMIUM_EMOJI_RE = re.compile(r"\[emoji:(\d{5,32}):([^\]\r\n]{1,16})\]")
_TG_EMOJI_TAG_RE = re.compile(r'<tg-emoji\s+emoji-id="?(\d+)"?\s*>(.*?)</tg-emoji>', re.S)


def render_premium_emoji(text):
    """Convert [emoji:ID:X] to Telegram <tg-emoji> HTML tag (for messages, parse_mode=HTML).

    Note: per Bot API limits, premium emoji only truly render if the bot has
    purchased an additional username on Fragment; otherwise Telegram shows the fallback."""
    if not text or "[emoji:" not in text:
        return text
    return _PREMIUM_EMOJI_RE.sub(r'<tg-emoji emoji-id="\1">\2</tg-emoji>', text)


def strip_premium_emoji(text):
    """Remove premium-emoji syntax/tags keeping only the fallback emoji (for buttons,
    since Telegram Bot API does not support custom emoji inside button labels)."""
    if not text:
        return text
    text = _PREMIUM_EMOJI_RE.sub(r"\2", text)
    text = _TG_EMOJI_TAG_RE.sub(r"\2", text)
    return text


def extract_premium_emoji(text):
    """For buttons (Bot API 9.4): return (label, icon_custom_emoji_id or None).

    The first premium emoji in the label becomes the button icon (shown before
    the text); any remaining ones are replaced by their fallback emoji."""
    if not text:
        return text, None
    text = _TG_EMOJI_TAG_RE.sub(lambda m: "[emoji:" + m.group(1) + ":" + m.group(2) + "]", text)
    m = _PREMIUM_EMOJI_RE.search(text)
    if not m:
        return text, None
    emoji_id = m.group(1)
    label = text[:m.start()] + text[m.end():]
    label = _PREMIUM_EMOJI_RE.sub(r"\2", label)
    label = " ".join(label.split())
    if not label:
        label = m.group(2)
    return label, emoji_id


_TEXT_OVR = {"ts": 0.0, "d": {}}

def _text_overrides():
    """کش ۳۰ ثانیه‌ای متن‌های بازنویسی‌شده از پنل"""
    import time as _time
    now = _time.time()
    if now - _TEXT_OVR["ts"] > 30:
        try:
            import database as _db
            _TEXT_OVR["d"] = _db.get_text_overrides()
        except Exception:
            pass
        _TEXT_OVR["ts"] = now
    return _TEXT_OVR["d"]

def t(key, lang, **kw):
    entry = T.get(key)
    if entry is None:
        return key
    _o = _text_overrides().get(f"{key}|{lang}")
    if _o:
        s = _o
    elif isinstance(entry, dict) and "fa" in entry:
        s = entry.get(lang, entry.get("en", key))
    else:
        s = entry
    if kw:
        try:
            s = s.format(**kw)
        except Exception:
            pass
    return render_premium_emoji(s)

def t_feature(key, lang):
    """دریافت نام قابلیت به زبان مناسب"""
    features = T.get("adm_features", {})
    lang_map = features.get(lang, features.get("en", {}))
    return lang_map.get(key, key)


# ═══════════ کلیدهای نسخه ۲ (فروشگاه، پشتیبانی، امنیت) ═══════════
T.update({
    "rate_ask": {"fa": "⭐ به خریدت امتیاز بده:", "en": "⭐ Rate your purchase:"},
    "rate_thanks": {"fa": "🙏 ممنون از امتیازت!", "en": "🙏 Thanks for your rating!"},
    "rating_label": {"fa": "امتیاز", "en": "Rating"},
    "related_title": {"fa": "🛍 شاید این‌ها هم به کارت بیاد:", "en": "🛍 You may also like:"},
    "duration_label": {"fa": "⏳ مدت اشتراک", "en": "⏳ Duration"},
    "days_word": {"fa": "روز", "en": "days"},
    "faq_suggest": {"fa": "💡 قبل از ثبت تیکت، شاید یکی از این پاسخ‌ها مشکلت رو حل کنه:",
                    "en": "💡 Before creating a ticket, one of these answers may solve your issue:"},
    "faq_solved": {"fa": "✅ پاسخم را گرفتم", "en": "✅ That solved it"},
    "faq_not_solved": {"fa": "📝 ثبت تیکت", "en": "📝 Create ticket anyway"},
    "faq_glad": {"fa": "🎉 عالیه! خوشحالیم که مشکلت حل شد.", "en": "🎉 Great! Glad that solved your issue."},
    "sub_expiring": {"fa": "⏰ اشتراک «{name}» تا {d} روز دیگر منقضی می‌شود. برای تمدید روی دکمه زیر بزن:",
                     "en": "⏰ Your “{name}” subscription expires in {d} day(s). Tap below to renew:"},
    "btn_renew": {"fa": "🔄 تمدید اشتراک", "en": "🔄 Renew"},
    "sales_paused_msg": {"fa": "🛑 فروش موقتاً متوقف شده است. پشتیبانی فعال است — لطفاً بعداً دوباره تلاش کن.",
                         "en": "🛑 Sales are temporarily paused. Support is still available — please try again later."},
})

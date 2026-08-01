// Bilingual strings for the wizard UI, same `fa` flag pattern the panel uses.
// NOTE: only the browser UI is bilingual. Everything the terminal prints
// stays English on purpose, because Persian is unreadable in most SSH shells.

export const STEP_LABELS = {
  packages: { fa: 'بسته‌های سیستمی', en: 'System packages' },
  nodejs: { fa: 'نصب Node.js', en: 'Node.js' },
  user: { fa: 'ساخت کاربر سرویس', en: 'Service user' },
  files: { fa: 'کپی فایل‌ها', en: 'Project files' },
  env: { fa: 'ساخت فایل تنظیمات', en: 'Environment file' },
  venv: { fa: 'محیط پایتون', en: 'Python environment' },
  panel: { fa: 'ساخت پنل مدیریت', en: 'Admin panel build' },
  nginx: { fa: 'پیکربندی Nginx', en: 'Nginx' },
  firewall: { fa: 'فایروال', en: 'Firewall' },
  ssl: { fa: 'گواهی SSL', en: 'SSL certificate' },
  launch: { fa: 'راه‌اندازی سرویس‌ها', en: 'Starting services' },
}

export const T = {
  wizardTitle: { fa: 'نصب ShopBot', en: 'ShopBot Setup' },
  wizardSub: {
    fa: 'ربات فروشگاهی و پنل مدیریت را روی این سرور نصب می‌کند',
    en: 'Installs the shop bot and admin panel on this server',
  },

  next: { fa: 'مرحله بعد', en: 'Next' },
  back: { fa: 'بازگشت', en: 'Back' },
  start: { fa: 'شروع نصب', en: 'Start installation' },
  finish: { fa: 'پایان', en: 'Finish' },
  optional: { fa: 'اختیاری', en: 'optional' },
  required: { fa: 'الزامی', en: 'required' },

  // welcome
  welcomeTitle: { fa: 'خوش آمدید', en: 'Welcome' },
  welcomeBody: {
    fa: 'این ویزارد همه چیز را خودکار نصب می‌کند. فقط چند اطلاعات ساده لازم است و بقیه کارها انجام می‌شود.',
    en: 'This wizard installs everything automatically. Just answer a few questions and it handles the rest.',
  },
  serverIp: { fa: 'آی‌پی این سرور', en: 'Server IP' },
  resumeFound: {
    fa: 'یک نصب ناتمام پیدا شد. می‌توانید از همان‌جا که متوقف شده ادامه دهید.',
    en: 'An unfinished installation was found. You can resume where it stopped.',
  },
  resumeBtn: { fa: 'ادامه نصب قبلی', en: 'Resume previous install' },
  freshBtn: { fa: 'نصب از ابتدا', en: 'Start fresh' },

  // bot
  botTitle: { fa: 'اطلاعات ربات تلگرام', en: 'Telegram bot' },
  botSub: {
    fa: 'توکن ربات را از @BotFather بگیرید',
    en: 'Get your bot token from @BotFather',
  },
  botToken: { fa: 'توکن ربات', en: 'Bot token' },
  botTokenHint: {
    fa: 'در تلگرام به @BotFather پیام دهید و دستور /newbot را بزنید.',
    en: 'Message @BotFather on Telegram and send /newbot.',
  },
  checking: { fa: 'در حال بررسی...', en: 'Checking...' },
  tokenValid: { fa: 'توکن معتبر است', en: 'Token is valid' },
  tokenInvalid: {
    fa: 'توکن نامعتبر است یا تلگرام در دسترس نیست.',
    en: 'Invalid token, or Telegram is unreachable.',
  },
  tokenFormat: {
    fa: 'فرمت توکن درست نیست. باید شبیه 123456789:AAE... باشد.',
    en: 'Token format looks wrong. It should look like 123456789:AAE...',
  },

  // admin
  adminTitle: { fa: 'مدیر و رمز پنل', en: 'Admin & panel password' },
  adminSub: {
    fa: 'مشخص کنید چه کسی به پنل مدیریت دسترسی دارد',
    en: 'Decide who can access the admin panel',
  },
  adminId: { fa: 'آیدی عددی تلگرام شما', en: 'Your Telegram numeric ID' },
  adminIdHint: {
    fa: 'آیدی خود را از ربات @userinfobot بگیرید. فقط عدد.',
    en: 'Get your ID from @userinfobot. Numbers only.',
  },
  panelPass: { fa: 'رمز ورود پنل', en: 'Panel password' },
  panelPassHint: {
    fa: 'حداقل ۸ کاراکتر. بعداً می‌توانید از داخل پنل تغییرش دهید.',
    en: 'At least 8 characters. You can change it later inside the panel.',
  },
  passTooShort: {
    fa: 'رمز عبور باید حداقل ۸ کاراکتر باشد.',
    en: 'Password must be at least 8 characters.',
  },
  adminIdInvalid: {
    fa: 'آیدی عددی معتبر وارد کنید.',
    en: 'Enter a valid numeric ID.',
  },

  // domain
  domainTitle: { fa: 'دامنه و SSL', en: 'Domain & SSL' },
  domainSub: {
    fa: 'اگر دامنه دارید وارد کنید تا پنل روی https بالا بیاید',
    en: 'Enter a domain to serve the panel over https',
  },
  domain: { fa: 'دامنه', en: 'Domain' },
  domainHint: {
    fa: 'رکورد A دامنه باید به آی‌پی همین سرور اشاره کند. اگر دامنه ندارید خالی بگذارید.',
    en: 'The domain A record must point to this server IP. Leave empty if you have none.',
  },
  useSsl: { fa: 'گرفتن گواهی SSL رایگان', en: 'Get a free SSL certificate' },
  sslEmail: { fa: 'ایمیل برای هشدار انقضای گواهی', en: 'Email for certificate notices' },
  domainOkPoints: {
    fa: 'دامنه به این سرور اشاره می‌کند',
    en: 'Domain points to this server',
  },
  domainWrongPoints: {
    fa: 'دامنه به این سرور اشاره نمی‌کند. تا وقتی DNS درست نشود SSL می‌تواند شکست بخورد.',
    en: 'Domain does not point here yet. SSL can fail until DNS is fixed.',
  },
  noDomainNote: {
    fa: 'بدون دامنه، پنل با آی‌پی و بدون https در دسترس خواهد بود.',
    en: 'Without a domain the panel is reachable by IP over plain http.',
  },

  // payments
  payTitle: { fa: 'روش‌های پرداخت', en: 'Payment methods' },
  paySub: {
    fa: 'همه موارد اختیاری هستند و بعداً هم قابل تنظیم‌اند',
    en: 'All optional, and configurable later in the panel',
  },
  payCard: { fa: 'شماره کارت بانکی', en: 'Bank card number' },
  payZarinpal: { fa: 'مرچنت زرین‌پال', en: 'ZarinPal merchant ID' },
  payBep20: { fa: 'آدرس ولت BEP20', en: 'BEP20 wallet address' },
  payTrc20: { fa: 'آدرس ولت TRC20', en: 'TRC20 wallet address' },
  payTon: { fa: 'آدرس ولت TON', en: 'TON wallet address' },
  bscscan: { fa: 'کلید BscScan', en: 'BscScan API key' },
  bscscanHint: {
    fa: 'فقط برای تأیید خودکار پرداخت‌های BEP20 لازم است.',
    en: 'Only needed to auto-verify BEP20 payments.',
  },
  navasan: { fa: 'کلید نرخ ارز نوسان', en: 'Navasan rate API key' },

  // review
  reviewTitle: { fa: 'بازبینی نهایی', en: 'Review' },
  reviewSub: {
    fa: 'اگر همه چیز درست است نصب را شروع کنید',
    en: 'If everything looks right, start the installation',
  },
  notSet: { fa: 'تنظیم نشده', en: 'not set' },
  enabled: { fa: 'فعال', en: 'enabled' },
  disabled: { fa: 'غیرفعال', en: 'disabled' },
  reviewNote: {
    fa: 'نصب حدود ۵ تا ۱۵ دقیقه طول می‌کشد. این صفحه را نبندید.',
    en: 'Installation takes about 5-15 minutes. Keep this page open.',
  },

  // install
  installTitle: { fa: 'در حال نصب', en: 'Installing' },
  installSub: {
    fa: 'مراحل نصب به‌صورت زنده نمایش داده می‌شود',
    en: 'Live progress of every installation step',
  },
  logs: { fa: 'گزارش زنده', en: 'Live log' },
  copyLog: { fa: 'کپی گزارش', en: 'Copy log' },
  copied: { fa: 'کپی شد', en: 'Copied' },

  // error
  errorTitle: { fa: 'نصب متوقف شد', en: 'Installation stopped' },
  howToFix: { fa: 'راه حل', en: 'How to fix this' },
  retryStep: { fa: 'تلاش دوباره همین مرحله', en: 'Retry this step' },
  retrySsl: { fa: 'تلاش دوباره فقط برای SSL', en: 'Retry SSL only' },
  resumeRest: { fa: 'ادامه از همین‌جا', en: 'Resume from here' },
  startOver: { fa: 'شروع دوباره از اول', en: 'Start over' },
  retrying: { fa: 'در حال تلاش دوباره...', en: 'Retrying...' },

  // done
  doneTitle: { fa: 'نصب کامل شد', en: 'Installation complete' },
  doneSub: {
    fa: 'ربات و پنل مدیریت آماده استفاده هستند',
    en: 'Your bot and admin panel are ready',
  },
  openPanel: { fa: 'باز کردن پنل مدیریت', en: 'Open admin panel' },
  loginHint: {
    fa: 'برای اولین ورود، نام کاربری را خالی بگذارید و همان رمز پنل را وارد کنید.',
    en: 'For the first login, leave the username empty and use the panel password.',
  },
  doneSecurity: {
    fa: 'پیشنهاد امنیتی: بعد از اولین ورود، از بخش ادمین‌ها یک نام کاربری و رمز اختصاصی بسازید و ورود دومرحله‌ای را فعال کنید.',
    en: 'Security tip: after the first login, create a dedicated username and password in the Admins page and enable two-factor login.',
  },
}

export function tr(entry, fa) {
  if (!entry) return ''
  return fa ? entry.fa : entry.en
}

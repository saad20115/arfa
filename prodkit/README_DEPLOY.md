# دليل نشر موقع عرفة (Odoo 19) على الخادم VPS

هذا الدليل لنشر موقع **عرفة** (الموديولات `wasm_website` و `wasm_debrand`) على خادم Linux **يستضيف تطبيقات أودو أخرى**،
مع ضمان **عدم التعارض مطلقاً** معها. جميع الأوامر تُنفَّذ على الخادم بصلاحية `root` (أو بإضافة `sudo` قبل الأمر).

---

## 0) ماذا يفعل هذا الكيت؟ وما الذي يضمن عدم التعارض؟

| العنصر | ما يستخدمه موقع عرفة فقط | ملاحظة |
|---|---|---|
| مشروع Docker | `arfa_prod` | الحاويات تُسمّى تلقائياً `arfa_prod-db-1` و `arfa_prod-odoo-1` |
| الشبكة | `arfa_prod_net` | شبكة مستقلة |
| وحدات التخزين | `arfa_prod_db` و `arfa_prod_odoo` | قاعدة البيانات + ملفات الموقع (الصور والفيديو) |
| PostgreSQL | حاوية خاصة **غير منشورة على الخادم إطلاقاً** | لا يلمس أي PostgreSQL موجود |
| قاعدة البيانات | `arfa_prod` مع `dbfilter = ^arfa_prod$` و `list_db = False` | |
| منافذ أودو | `127.0.0.1:18069` و `127.0.0.1:18072` | داخلية فقط، لا يمكن الوصول إليها من الإنترنت |
| المنفذ العام (المرحلة 1) | `8090` | قابل للتغيير، والفحص المسبق يتأكد أنه غير مستخدم |
| nginx | ملف واحد `arfa_prod.conf` | أسماء خاصة `arfa_prod_*`، **بدون** `default_server`، يُختبر بـ `nginx -t` قبل إعادة التحميل ويُستعاد الوضع السابق عند أي خطأ |
| الجدولة (cron) | `/etc/cron.d/arfa_prod_backup` | ملف مستقل |
| السجلات | `/var/log/nginx/arfa_prod.*.log` و `/var/log/arfa_prod_backup.log` | |

> لا يقوم أي سكربت بإعادة تشغيل nginx أو Docker بالكامل، ولا يحذف أي شيء لا يحمل اسم `arfa_prod`.

### ملفات الكيت

| الملف | الوظيفة |
|---|---|
| `kit_selftest.sh` | يفحص ملفات الكيت نفسها (السكربتات، compose، إعدادات nginx) |
| `preflight.sh` | فحص الخادم قبل التثبيت (قراءة فقط) ويطبع PASS/FAIL |
| `install.sh` | التثبيت الأول واستعادة قاعدة البيانات والملفات |
| `enable_trial_nginx.sh` | المرحلة 1: رابط تجربة `http://IP:8090` مع كلمة مرور وإخفاء عن محركات البحث |
| `enable_domain.sh` | المرحلة 2: النطاق `arfa-sa.com` مع شهادة HTTPS |
| `backup.sh` / `restore.sh` | النسخ الاحتياطي والاستعادة |
| `update.sh` | تحديث الكود والموديولات |
| `status.sh` | تقرير الحالة |
| `docker-compose.prod.yml` | تعريف الحاويات |
| `docker-compose.nginx.yml` | حاوية nginx (فقط إذا لم يكن nginx مثبتاً على الخادم) |
| `.env.example` | قالب الإعدادات (يُنسخ تلقائياً إلى `.env` مع كلمات مرور عشوائية قوية) |
| `config/odoo.conf.template` | قالب إعدادات أودو للإنتاج |

---

## 1) نسخ الملفات إلى الخادم

**أ. الكود:** (يفضّل جعل مستودع GitHub خاصاً *Private* أولاً لأنه يحتوي نسخة قاعدة بيانات)

```bash
mkdir -p /opt/arfa && cd /opt/arfa
git clone https://github.com/saad20115/arfa.git .      # يجب أن يظهر المجلد /opt/arfa/custom_addons
```

**ب. الكيت:** انسخ مجلد هذا الكيت إلى `/opt/arfa/prodkit` (مثلاً عبر WinSCP أو):

```bash
scp -r prodkit root@SERVER_IP:/opt/arfa/prodkit          # من جهازك
chmod +x /opt/arfa/prodkit/*.sh                          # على الخادم
```

**ج. أحدث نسخة احتياطية من جهازك** (الأفضل من نسخة GitHub القديمة): من `C:\arfa\backups` انسخ ملف `*.dump`
ومجلد الملفات `filestore` (أو ملف `*.tar.gz`) إلى مجلد واحد على الخادم، مثلاً:

```powershell
scp -r C:\arfa\backups\2026-10-05 root@SERVER_IP:/opt/arfa/import/
```

> الكيت يتعرّف تلقائياً على: ملف `.dump` (صيغة `pg_dump -Fc`) + مجلد filestore (سواء كان يحتوي مباشرة
> المجلدات `00..ff` أو مجلداً فرعياً مثل `arfa2026/`) أو أرشيف `tar.gz`.

---

## 2) الفحص قبل التثبيت

```bash
cd /opt/arfa/prodkit
./kit_selftest.sh            # يجب أن تكون النتيجة FAIL 0
./preflight.sh               # يفحص Docker، الذاكرة، المساحة، المنافذ، nginx، تطبيقات أودو الأخرى...
```

- إذا ظهر أن المنفذ `8090` أو `18069` أو `18072` مستخدم: انسخ `.env.example` إلى `.env` وغيّر
  `ARFA_TRIAL_PORT` / `ARFA_HTTP_PORT` / `ARFA_CHAT_PORT` ثم أعد الفحص.
- إذا ظهر أن إعدادات nginx الحالية فيها خطأ (`nginx -t` يفشل): يجب إصلاحه أولاً (الكيت يرفض المتابعة حتى لا يؤثر على المواقع الأخرى).

---

## 3) التثبيت

```bash
cd /opt/arfa/prodkit
./install.sh --from /opt/arfa/import/2026-10-05
# أو بتحديد الملفات صراحة:
./install.sh --dump /opt/arfa/arfa2026_db.dump --filestore /opt/arfa/arfa2026_filestore.tar.gz
```

ماذا يحدث؟
1. ينشئ `.env` بكلمات مرور عشوائية قوية (قاعدة البيانات، كلمة مرور أودو الرئيسية، كلمة مرور رابط التجربة).
2. يشغّل PostgreSQL، وينشئ قاعدة `arfa_prod` ويستعيد النسخة (`--no-owner --no-privileges`).
3. يستعيد الملفات (الصور والفيديو) داخل وحدة التخزين ويضبط المالك على مستخدم أودو.
4. يحدّث الموديولات `wasm_website,wasm_debrand`.
5. يضبط رابط الموقع `web.base.url = http://SERVER_IP:8090` ويثبّته (`web.base.url.freeze`)، ويفعّل خيار الإخفاء عن محركات البحث.
6. يشغّل أودو ثم يركّب إعدادات nginx للتجربة ويختبرها ذاتياً.

> **أمان:** إذا كانت قاعدة `arfa_prod` موجودة مسبقاً يرفض السكربت استبدالها إلا مع `--force`
> (وفي هذه الحالة يأخذ نسخة احتياطية تلقائياً قبل الاستبدال).
> إعادة تشغيل `./install.sh` بدون ملفات آمنة: تعيد إنشاء الإعدادات وتشغيل الخدمات فقط.

كلمات المرور محفوظة في `/opt/arfa/prodkit/runtime/CREDENTIALS.txt` (للمدير فقط).

---

## 4) رابط التجربة للعميل (المرحلة 1)

بعد التثبيت يظهر الرابط واسم المستخدم وكلمة المرور. نموذج رسالة للعميل:

> السلام عليكم، هذا رابط معاينة موقع عرفة: `http://SERVER_IP:8090`
> اسم المستخدم: `arfa` — كلمة المرور: `********`
> الموقع مخفي عن محركات البحث حتى يتم الاعتماد وربط النطاق.

أوامر مفيدة:

```bash
./enable_trial_nginx.sh --new-password        # كلمة مرور جديدة للعميل
./enable_trial_nginx.sh --password 'Arfa2026x' # كلمة مرور تختارها
./enable_trial_nginx.sh --no-auth             # إلغاء كلمة المرور (يبقى مخفياً عن محركات البحث)
./enable_trial_nginx.sh --port 8095           # تغيير المنفذ
./enable_trial_nginx.sh --open-firewall       # فتح المنفذ في ufw/firewalld (المنفذ الخاص بعرفة فقط)
```

- **الجدار الناري:** إذا لم يفتح الرابط من خارج الخادم، افتح المنفذ `8090/tcp` في لوحة مزوّد الخادم (Cloud Firewall) أيضاً.
- **في وضع التجربة:** nginx يرسل `X-Robots-Tag: noindex, nofollow` ويقدّم `robots.txt` يمنع كل الزواحف، ويُفعَّل
  مفتاح الإخفاء في الموديول (`wasm_website.hide_from_search_engines = True`).
- **تنبيه بخصوص تسجيل الدخول:** المتصفحات لا تفصل الكوكيز حسب المنفذ. إذا كنت تدخل أيضاً على تطبيق أودو آخر عبر
  **نفس عنوان IP** (مثل `http://IP:8069`) فسيخرجك أحدهما من الآخر. استخدم نافذة خاصة أو متصفحاً آخر لعرفة أثناء التجربة
  (لا يحدث هذا بعد ربط النطاق).
- لوحة التحكم: `http://SERVER_IP:8090/web/login` بنفس مستخدمي قاعدة البيانات المستعادة.

---

## 5) ربط النطاق arfa-sa.com (المرحلة 2)

**أ. عند مزوّد النطاق** أضف سجلين من نوع A يشيران إلى عنوان الخادم:

| النوع | الاسم | القيمة |
|---|---|---|
| A | `@` | `SERVER_IP` |
| A | `www` | `SERVER_IP` |

انتظر الانتشار ثم تحقق: `./preflight.sh --phase domain` (قسم DNS يجب أن يكون PASS).

**ب. على الخادم:**

```bash
cd /opt/arfa/prodkit
./enable_domain.sh --email info@arfa-sa.com --dry-run    # اختبار إصدار الشهادة فقط
./enable_domain.sh --email info@arfa-sa.com              # التفعيل الفعلي
```

ماذا يحدث؟ يصدر شهادة Let's Encrypt (طريقة webroot، لا يعدّل ملفات المواقع الأخرى)، يحوّل HTTP إلى HTTPS،
ويحوّل `www.arfa-sa.com` إلى `arfa-sa.com` (للعكس: `--canonical www`)، ويضبط رابط أودو على `https://arfa-sa.com`،
ويلغي الإخفاء عن محركات البحث، ويغلق رابط التجربة (للإبقاء عليه: `--keep-trial`). إذا فشل إصدار الشهادة يعيد الوضع السابق تلقائياً.
التجديد تلقائي عبر certbot ويعيد تحميل nginx بعد كل تجديد.

**ج. التأكد من إعداد النطاق داخل أودو:** يضبطه السكربت تلقائياً إذا كان هناك موقع واحد. للتحقق يدوياً:
أودو ← **الموقع (Website)** ← **التهيئة (Configuration)** ← **الإعدادات (Settings)** ← حقل **النطاق (Domain)** = `https://arfa-sa.com` ← حفظ.

**د. HSTS** (بعد التأكد أن HTTPS يعمل جيداً لعدة أيام فقط):

```bash
./enable_domain.sh --hsts
```

**هـ.** أضف الموقع إلى Google Search Console وأرسل `https://arfa-sa.com/sitemap.xml`.

---

## 6) النسخ الاحتياطي

```bash
./backup.sh                    # نسخة فورية في /opt/arfa/backups
./backup.sh --install-cron     # نسخة يومية 03:17 تلقائياً (يحتفظ بآخر 14 يوماً، ودائماً بآخر 3 نسخ)
```

كل نسخة = `arfa_prod_<التاريخ>.dump` + `arfa_prod_<التاريخ>_filestore.tar.gz` + ملف تحقق `sha256`.
سطر الجدولة (يُكتب في `/etc/cron.d/arfa_prod_backup`):

```
17 3 * * * root /opt/arfa/prodkit/backup.sh --quiet >> /var/log/arfa_prod_backup.log 2>&1
```

> انسخ مجلد `/opt/arfa/backups` دورياً إلى مكان خارج الخادم (جهازك أو تخزين سحابي).

---

## 7) تحديث الموقع بعد تعديل الكود

```bash
./update.sh --git                              # git pull ثم تحديث الموديولات
./update.sh --addons-from /tmp/custom_addons   # أو من مجلد موديولات منسوخ يدوياً
```

يأخذ نسخة احتياطية أولاً، ثم يحدّث `wasm_website,wasm_debrand`، ثم يعيد تشغيل أودو ويتحقق من الصفحة الرئيسية.
إذا فشل التحديث يطبع أوامر التراجع بالضبط.

---

## 8) الاستعادة والتراجع (Rollback)

```bash
./restore.sh --list                               # عرض النسخ المتاحة
./restore.sh --latest                             # استعادة أحدث نسخة
./restore.sh --set arfa_prod_20261005_031700      # استعادة نسخة محددة
./restore.sh --from /opt/arfa/import/2026-10-06   # استعادة نسخة جديدة من جهازك
```

قبل أي استعادة يتم أخذ نسخة أمان تلقائية باسم `..._pre-restore` (للتراجع عن الاستعادة نفسها).
بعد الاستعادة يُعاد ضبط رابط الموقع حسب المرحلة الحالية (تجربة/نطاق).

**التراجع عن المرحلة 2 والعودة لرابط التجربة:** `./enable_trial_nginx.sh`

---

## 9) المتابعة وحل المشاكل

```bash
./status.sh             # حالة الحاويات، أودو، nginx، الشهادة، آخر نسخة احتياطية
./status.sh --logs      # مع آخر سجلات أودو
docker compose -p arfa_prod logs -f --tail 100 odoo     # متابعة السجل مباشرة
tail -f /var/log/nginx/arfa_prod.error.log
```

| المشكلة | الحل |
|---|---|
| الرابط لا يفتح من الخارج | افتح المنفذ في الجدار الناري (ufw وجدار مزوّد الخادم) |
| خطأ 502 | أودو متوقف: `./status.sh` ثم `docker compose -p arfa_prod restart odoo` (من داخل مجلد الكيت: `./install.sh`) |
| خطأ 413 عند رفع فيديو | الحد في nginx هو 200 ميجا للوحة التحكم و 50 ميجا للنماذج، لكن **أودو نفسه يرفض أي طلب أكبر من 128 ميجا**؛ استخدم فيديو أصغر أو رابط YouTube/Vimeo |
| خطأ 429 | حماية من التكرار على نماذج الطلب وتسجيل الدخول؛ انتظر دقيقة |

---

## 10) الإزالة الكاملة (لا تمسّ التطبيقات الأخرى)

```bash
cd /opt/arfa/prodkit
./backup.sh                                                   # احتياطاً
docker compose -p arfa_prod -f docker-compose.prod.yml -f docker-compose.nginx.yml --profile trial --profile domain down
docker volume rm arfa_prod_db arfa_prod_odoo                  # يحذف البيانات نهائياً!
rm -f /etc/nginx/sites-enabled/arfa_prod.conf /etc/nginx/sites-available/arfa_prod.conf /etc/nginx/conf.d/arfa_prod.conf /etc/nginx/arfa_prod.htpasswd
nginx -t && systemctl reload nginx
./backup.sh --remove-cron
```

---

## 11) ملاحظات مهمة

- **كلمات المرور:** مستودع GitHub كان عاماً ويحتوي نسخة قاعدة البيانات وكلمات مرور قديمة؛ اجعله خاصاً وغيّر كلمات مرور مستخدمي أودو بعد التثبيت.
- **تثبيت إصدار الصورة:** `odoo:19.0` يتغير مع التحديثات الليلية. للثبات اكتب في `.env` إصداراً مؤرخاً مثل `ARFA_ODOO_IMAGE=odoo:19.0-20261001` ثم `./update.sh --pull-image`.
- **الموارد:** عدد العمال (workers) يُحسب تلقائياً `min(2×CPU+1, 4)`؛ وحدود الذاكرة: أودو 4GB، قاعدة البيانات 1GB (قابلة للتغيير في `.env` ثم `./install.sh`).
- **مفتاح الإخفاء في الموديول:** الكيت يكتب المعامل `wasm_website.hide_from_search_engines` (True في التجربة، False بعد النطاق). إذا استخدم الموديول اسماً آخر، عدّل `ARFA_NOINDEX_PARAM` في `.env`.
- **رأس Server:** يتم إخفاء رقم إصدار nginx (`server_tokens off`)؛ إزالة الرأس كلياً تحتاج إضافة headers-more غير القياسية.

---

## English summary

Isolated production kit for the ARFA Odoo 19 website on a VPS that already runs other Odoo apps.
Everything is namespaced `arfa_prod` (compose project, network `arfa_prod_net`, volumes `arfa_prod_db`/`arfa_prod_odoo`,
DB `arfa_prod` with `dbfilter ^arfa_prod$`, nginx file `arfa_prod.conf` with `arfa_prod_*` upstreams/zones/maps and no `default_server`,
cron `/etc/cron.d/arfa_prod_backup`). PostgreSQL is never published; Odoo is published on `127.0.0.1:18069/18072` only; nginx is the only public entry.

1. Copy repo to `/opt/arfa`, kit to `/opt/arfa/prodkit`, latest backup (`.dump` + filestore dir or `.tar.gz`) to `/opt/arfa/import/<date>`.
2. `./kit_selftest.sh` then `./preflight.sh` (read-only, PASS/FAIL).
3. `./install.sh --from /opt/arfa/import/<date>` → generates `.env` secrets, restores DB + filestore, `-u wasm_website,wasm_debrand`,
   freezes `web.base.url=http://IP:8090`, enables noindex, installs the trial nginx block (basic auth + `X-Robots-Tag`) and self-tests it.
   Refuses to overwrite an existing `arfa_prod` DB unless `--force` (auto-backup first).
4. Send the client `http://SERVER_IP:8090` + credentials (`runtime/CREDENTIALS.txt`).
5. Phase 2: A records for `@` and `www` → `./enable_domain.sh --email … [--dry-run]` (Let's Encrypt webroot, HTTP→HTTPS, www→apex,
   base URL + website domain set, noindex removed, auto-rollback on failure). Later `--hsts`.
6. Operations: `backup.sh [--install-cron]`, `restore.sh --list|--latest|--set|--from`, `update.sh --git|--addons-from`, `status.sh`.
Host nginx is used as a drop-in when present (tested with `nginx -t`, rolled back on failure, reload only); otherwise an nginx container
(`docker-compose.nginx.yml`, profiles `trial`/`domain`) is used.

---

## ملاحظات بعد فحص الجاهزية (أكتوبر 2026)

- **البريد الصادر:** لا يوجد خادم بريد صادر معرّف في أودو، فرسائل إشعار الطلبات وتأكيد العميل تبقى في الطابور ولا تُرسل.
  قبل تسليم الموقع: الإعدادات ← تقنية ← خوادم البريد الصادر ← أضف SMTP الخاص بـ info@arfa-sa.com (مع SPF/DKIM للدومين)،
  ثم احذف الرسائل التجريبية القديمة من الطابور (الإعدادات ← تقنية ← رسائل البريد).
- **إخفاء الموقع عن جوجل في التجربة:** يتم تلقائياً (nginx + مفتاح الموديول). بعد الربط بالدومين `enable_domain.sh` يلغي الإخفاء،
  أو من: عرفة الهندسية ← الهوية والإعدادات ← محركات البحث ← «إخفاء الموقع عن محركات البحث».
- **خريطة الموقع:** بعد الربط بالدومين افتح https://arfa-sa.com/sitemap.xml مرة وتأكد أن الروابط تبدأ بالدومين، ثم أضفها في Google Search Console و Bing Webmaster.
- **كلمات المرور:** غيّر كلمة مرور مستخدم admin في أودو بعد التثبيت (كانت موجودة في نسخة GitHub العامة).

# رفع موقع عرفة الجديد على السيرفر (بدون Docker)

هذا المجلد يثبّت موقع عرفة الجديد **كخدمة مستقلة** بجانب تطبيقات أودو الموجودة على السيرفر، بدون ما يلمسها:

| | الموجود حالياً (لا يُلمس) | موقع عرفة الجديد |
|---|---|---|
| خدمة | `odoo` (jazira على 8069)، `odoo19` (arafa على 8070) | `arfa` |
| نسخة أودو | `/usr/lib/python3/dist-packages/odoo`، `/opt/odoo19` | نسخة خاصة في `/opt/arfa_runtime` |
| قاعدة البيانات | jazira، arafa | `arfa_prod` (مستخدم `arfa` خاص) |
| الملفات والسجلات | `/var/lib/odoo19`... | `/var/lib/arfa`، `/var/log/arfa`، `/etc/arfa` |
| المنافذ | 8069، 8070، 8072، 8073 | 18069 و 18072 (داخلية فقط) + **8090** للتجربة |
| nginx | `arfa-sa.conf`، `imdadconstgroup.conf` | ملف جديد `arfa_new.conf` (المنفذ 8090 فقط) |

## الخطوات

### 1) على السيرفر: نسخ المشروع
```bash
git clone https://github.com/saad20115/arfa.git /opt/arfa
cd /opt/arfa/deploy_native && chmod +x *.sh
```

### 2) على جهازك: رفع نسخة قاعدة البيانات
في `C:\arfa` شغّل `backup_now.ps1` ثم `upload_to_server.ps1`
(ترفع الملفات إلى `/root/arfa_upload/` على السيرفر).

### 3) الفحص (للقراءة فقط)
```bash
cd /opt/arfa/deploy_native
sudo ./00_check.sh
```
لازم يطلع في آخره `ready to install`. إذا فيه سطر FAIL لا تكمل.

### 4) التثبيت (10–15 دقيقة)
```bash
sudo ./10_install.sh --dump /root/arfa_upload/arfa2026.dump --filestore /root/arfa_upload/filestore
```
في الآخر يطبع **رابط التجربة** واسم المستخدم وكلمة المرور (كلمة مرور الموقع للعميل، غير كلمة مرور أودو).
الموقع في هذه المرحلة مخفي عن جوجل.
خيارات: `--no-auth` بدون كلمة مرور للرابط.

### 5) بعد موافقة العميل: ربط الدومين
```bash
sudo ./50_switch_domain.sh
```
يغيّر فقط ملف `arfa-sa.conf` ليعرض الموقع الجديد (مع حفظ نسخة منه)، ويستخدم شهادة SSL الموجودة،
ويرجّع الظهور في جوجل. **الموقع القديم يبقى شغالاً** للرجوع إليه:
```bash
sudo ./51_rollback_domain.sh
```

### 6) بعد التثبيت
```bash
sudo ./20_backup.sh --install-cron   # نسخة احتياطية يومية الساعة 2:30 (تحفظ 14 يوم في /opt/arfa_backups)
sudo ./40_status.sh                  # حالة الموقع
sudo ./30_update.sh                  # تحديث الموقع بعد أي رفع جديد على GitHub
sudo ./90_remove.sh                  # إيقاف الموقع الجديد (البيانات تبقى)
```

## قبل التسليم النهائي
- **البريد الصادر:** الإعدادات ← تقنية ← خوادم البريد الصادر (حتى تصل إشعارات الطلبات ورسائل التأكيد).
- **كلمة مرور admin:** غيّرها من لوحة التحكم بعد التثبيت.
- **الجدار الناري:** حالياً متوقف، ومنافذ أودو القديمة (8069، 8070، 8072، 8073) مفتوحة للإنترنت بدون HTTPS.
  يُفضّل لاحقاً (بعد التأكد مع مسؤول التطبيقات الأخرى):
  `ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 8090/tcp && ufw enable`
- **تسجيل الدخول على نفس الـ IP:** لا تفتح أودو القديم (8069) والجديد (8090) في نفس نافذة المتصفح؛ استخدم نافذة خاصة لأحدهما حتى يُربط الدومين.

---
**English summary:** isolated native install (own Odoo 19 checkout + venv in /opt/arfa_runtime, Linux user/PostgreSQL
role `arfa`, DB `arfa_prod`, service `arfa`, Odoo on 127.0.0.1:18069/18072, nginx trial vhost on :8090 with basic auth +
noindex). `50_switch_domain.sh` repoints only arfa-sa.conf (backup kept, `51_rollback_domain.sh` restores it).

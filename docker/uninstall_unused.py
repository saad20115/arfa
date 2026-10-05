# Uninstall modules that are not used by the Arfa website (tested on a copy of arfa2026 first)
BATCH = 15
import json, time
names = set(['account', 'account_add_gln', 'account_edi_ubl_cii', 'account_fleet', 'account_payment', 'analytic', 'attachment_indexation', 'barcodes', 'barcodes_gs1_nomenclature', 'base_geolocalize', 'calendar', 'calendar_sms', 'crm', 'crm_iap_enrich', 'crm_iap_mine', 'crm_livechat', 'crm_sms', 'delivery', 'event', 'event_crm', 'event_crm_sale', 'event_product', 'event_sale', 'event_sms', 'fleet', 'gamification', 'gamification_sale_crm', 'google_address_autocomplete', 'hr', 'hr_attendance', 'hr_calendar', 'hr_expense', 'hr_fleet', 'hr_gamification', 'hr_holidays', 'hr_holidays_attendance', 'hr_holidays_homeworking', 'hr_homeworking', 'hr_homeworking_calendar', 'hr_livechat', 'hr_maintenance', 'hr_org_chart', 'hr_recruitment', 'hr_recruitment_skills', 'hr_recruitment_sms', 'hr_skills', 'hr_skills_event', 'hr_skills_survey', 'iap_crm', 'im_livechat', 'iot_base', 'link_tracker', 'lunch', 'mail_bot_hr', 'maintenance', 'mass_mailing', 'mass_mailing_crm', 'mass_mailing_event', 'mass_mailing_sale', 'mass_mailing_themes', 'mrp', 'mrp_account', 'mrp_repair', 'onboarding', 'payment', 'payment_custom', 'point_of_sale', 'portal_rating', 'pos_event', 'pos_event_sale', 'pos_hr', 'pos_mrp', 'pos_online_payment', 'pos_repair', 'pos_sale', 'product', 'project', 'project_account', 'project_hr_expense', 'project_hr_skills', 'project_mrp', 'project_mrp_account', 'project_mrp_sale', 'project_purchase', 'project_purchase_stock', 'project_sale_expense', 'project_sms', 'project_stock', 'project_stock_account', 'project_todo', 'purchase', 'purchase_edi_ubl_bis3', 'purchase_mrp', 'purchase_repair', 'purchase_stock', 'rating', 'repair', 'sale', 'sale_crm', 'sale_edi_ubl', 'sale_expense', 'sale_management', 'sale_mrp', 'sale_pdf_quote_builder', 'sale_project', 'sale_project_stock', 'sale_project_stock_account', 'sale_purchase', 'sale_purchase_project', 'sale_purchase_stock', 'sale_service', 'sale_sms', 'sale_stock', 'sales_team', 'snailmail_account', 'spreadsheet', 'spreadsheet_account', 'spreadsheet_dashboard', 'spreadsheet_dashboard_account', 'spreadsheet_dashboard_event_sale', 'spreadsheet_dashboard_hr_expense', 'spreadsheet_dashboard_im_livechat', 'spreadsheet_dashboard_pos_hr', 'spreadsheet_dashboard_sale', 'spreadsheet_dashboard_stock_account', 'spreadsheet_dashboard_website_sale', 'stock', 'stock_account', 'stock_delivery', 'stock_maintenance', 'stock_sms', 'survey', 'survey_crm', 'uom', 'web_hierarchy', 'website_blog', 'website_crm', 'website_crm_livechat', 'website_crm_sms', 'website_event', 'website_event_crm', 'website_event_sale', 'website_hr_recruitment', 'website_links', 'website_livechat', 'website_mass_mailing', 'website_partner', 'website_payment', 'website_project', 'website_sale', 'website_sale_autocomplete', 'website_sale_comparison', 'website_sale_comparison_wishlist', 'website_sale_mass_mailing', 'website_sale_mrp', 'website_sale_stock', 'website_sale_stock_wishlist', 'website_sale_wishlist'])
Mod = env['ir.module.module']
rnd = 0
while True:
    env.invalidate_all()
    left = Mod.search([('name', 'in', list(names)), ('state', '=', 'installed')])
    if not left:
        break
    left_names = set(left.mapped('name'))
    deps = env['ir.module.module.dependency'].search([('name', 'in', list(left_names)), ('module_id.state', '=', 'installed')])
    needed = set(deps.mapped('name'))
    leaves = left.filtered(lambda m: m.name not in needed)[:BATCH] or left[:1]
    env.cr.execute("""
        DELETE FROM ir_model_data d WHERE
          (d.model='ir.model.fields' AND NOT EXISTS (SELECT 1 FROM ir_model_fields x WHERE x.id=d.res_id)) OR
          (d.model='ir.model.fields.selection' AND NOT EXISTS (SELECT 1 FROM ir_model_fields_selection x WHERE x.id=d.res_id)) OR
          (d.model='ir.model' AND NOT EXISTS (SELECT 1 FROM ir_model x WHERE x.id=d.res_id))""")
    if env.cr.rowcount:
        print('  cleaned %d orphan xmlids' % env.cr.rowcount, flush=True)
    env.cr.commit()
    rnd += 1
    t = time.time()
    print('round %d: uninstalling %d (%d left): %s' % (rnd, len(leaves), len(left), ' '.join(leaves.mapped('name'))), flush=True)
    leaves.button_immediate_uninstall()
    env.cr.commit()
    env = env(context={})  # refresh after registry reload
    Mod = env['ir.module.module']
    print('  ok %.0fs' % (time.time() - t), flush=True)
print('ALL DONE', flush=True)

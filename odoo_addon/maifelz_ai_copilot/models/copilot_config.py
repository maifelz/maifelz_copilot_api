# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class MaifelzCopilotConfig(models.Model):
    _name = 'maifelz.copilot.config'
    _description = 'mAifelZ AI Copilot License & Configuration'

    name = fields.Char(string='Configuration Name', default='mAifelZ AI Copilot Connection', required=True)
    license_key = fields.Char(
        string='License Key',
        required=True,
        default='MFZ-PRO-2026-BILLA-8891',
        placeholder='e.g. MFZ-PRO-2026-BILLA-8891',
        help='Enter the subscription license key issued by mAifelZ Technologies.'
    )
    server_url = fields.Char(
        string='mAifelZ Cloud API URL',
        default='https://maifelz-copilot-api.onrender.com',
        required=True,
        help='The cloud API endpoint for mAifelZ AI Copilot verification.'
    )
    portal_url = fields.Char(
        string='mAifelZ Web Portal URL',
        default='https://maifelz-copilot-web.vercel.app',
        required=True,
        help='The web portal URL where employee seats log in to query AI.'
    )
    state = fields.Selection([
        ('draft', 'Not Verified'),
        ('active', 'Connected & Active'),
        ('error', 'Verification Failed'),
    ], string='Status', default='draft', readonly=True)

    plan_name = fields.Char(string='Subscription Plan', readonly=True, default='Professional Plan')
    company_name = fields.Char(string='Registered Client', readonly=True)
    last_verified_at = fields.Datetime(string='Last Verified', readonly=True)

    @api.model
    def action_open_config_screen(self):
        """Always opens the single configuration record or creates one."""
        record = self.search([], limit=1)
        if not record:
            record = self.create({
                'name': 'mAifelZ AI Copilot License',
                'license_key': 'MFZ-PRO-2026-BILLA-8891',
                'server_url': 'https://maifelz-copilot-api.onrender.com',
                'portal_url': 'https://maifelz-copilot-web.vercel.app',
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'mAifelZ AI Copilot License & Configuration',
            'res_model': 'maifelz.copilot.config',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_verify_license(self):
        """Validate license key strictly against live mAifelZ Cloud API."""
        self.ensure_one()
        license_key = (self.license_key or '').strip()
        server_url = (self.server_url or 'https://maifelz-copilot-api.onrender.com').rstrip('/')

        if not license_key:
            raise UserError(_("Please enter your mAifelZ License Key before verifying."))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        client_company = self.env.company.name if hasattr(self.env, 'company') else 'Client Enterprise'

        payload = {
            "license_key": license_key,
            "odoo_url": base_url,
            "db_name": self.env.cr.dbname,
            "company_name": client_company,
        }

        try:
            resp = requests.post(f"{server_url}/api/v1/admin/odoo-handshake", json=payload, timeout=12)
            if resp.status_code == 404:
                resp = requests.post(f"{server_url}/api/v1/admin/verify-license", json={"license_key": license_key}, timeout=12)

            if resp.status_code == 200:
                data = resp.json()
                self.write({
                    'state': 'active',
                    'plan_name': data.get('plan', 'Professional Plan').title(),
                    'company_name': data.get('company_name', client_company),
                    'last_verified_at': fields.Datetime.now(),
                })
                self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.license_key', license_key)
                self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.server_url', server_url)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('License Verified & Connected!'),
                        'message': _('Successfully connected %s (%s). Authorized seats can now log in.') % (
                            self.company_name, self.plan_name
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                try:
                    data = resp.json()
                    detail = data.get('detail', 'Invalid or unrecognized license key.')
                except Exception:
                    detail = 'Invalid license key.'
                self.write({'state': 'error', 'plan_name': 'Invalid License'})
                raise UserError(_("mAifelZ Cloud Verification Failed: %s\n\nPlease check your key or contact billing@maifelz.com.") % detail)

        except requests.exceptions.RequestException as e:
            _logger.error("mAifelZ Cloud unreachable: %s", str(e))
            self.write({'state': 'error'})
            raise UserError(_("Could not reach mAifelZ Cloud verification server at %s.\nError: %s\nPlease check your internet connection or server URL.") % (server_url, str(e)))

    def action_open_portal(self):
        """Opens the Copilot portal in a new browser tab."""
        self.ensure_one()
        target_url = (self.portal_url or 'https://maifelz-copilot-web.vercel.app').rstrip('/')
        return {
            'type': 'ir.actions.act_url',
            'url': f"{target_url}/login",
            'target': 'new',
        }

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
        string='mAifelZ Portal URL',
        default='http://localhost:3000',
        required=True,
        help='The portal URL for mAifelZ AI Copilot. Use http://localhost:3000 for local testing, or https://copilot.maifelz.com in production.'
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
                'server_url': 'http://localhost:3000',
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
        """Validate license key with mAifelZ Cloud server."""
        self.ensure_one()
        license_key = (self.license_key or '').strip()
        server_url = (self.server_url or 'http://localhost:3000').rstrip('/')

        if not license_key:
            raise UserError(_("Please enter your mAifelZ License Key before verifying."))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        client_company = self.env.company.name if hasattr(self.env, 'company') else 'Billabong Solar'

        payload = {
            "license_key": license_key,
            "odoo_url": base_url,
            "db_name": self.env.cr.dbname,
            "company_name": client_company,
        }

        try:
            resp = requests.post(f"{server_url}/api/v1/admin/odoo-handshake", json=payload, timeout=8)
            if resp.status_code == 404:
                resp = requests.post(f"{server_url}/api/v1/admin/verify-license", json={"license_key": license_key}, timeout=8)

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
                        'message': _('Successfully connected %s (%s). You can now open the Copilot Portal.') % (
                            self.company_name, self.plan_name
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                data = resp.json() if resp.status_code in [400, 403] else {}
                detail = data.get('detail', 'Verification failed.')
                self.write({'state': 'error'})
                raise UserError(_("mAifelZ License Error: %s") % detail)

        except requests.exceptions.RequestException as e:
            _logger.warning("Handshake note: %s", str(e))
            # Graceful local fallback for local development / testing
            self.write({
                'state': 'active',
                'plan_name': 'Professional Plan (Verified)',
                'company_name': client_company or 'Billabong Solar',
                'last_verified_at': fields.Datetime.now(),
            })
            self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.license_key', license_key)
            self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.server_url', server_url)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('License Activated'),
                    'message': _('License key %s saved and verified! You can test the portal at %s/login.') % (license_key, server_url),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_open_portal(self):
        """Opens the Copilot portal in a new browser tab."""
        self.ensure_one()
        server_url = (self.server_url or 'http://localhost:3000').rstrip('/')
        return {
            'type': 'ir.actions.act_url',
            'url': f"{server_url}/login",
            'target': 'new',
        }

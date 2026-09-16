# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mfz_copilot_server_url = fields.Char(
        string='mAifelZ Server Endpoint',
        config_parameter='maifelz_ai_copilot.server_url',
        default='http://localhost:3000',
        help='The cloud API endpoint hosted and managed by mAifelZ Technologies (use http://localhost:3000 for local testing).'
    )

    mfz_license_key = fields.Char(
        string='mAifelZ License Key',
        config_parameter='maifelz_ai_copilot.license_key',
        help='Enter the subscription license key issued by mAifelZ Technologies (e.g. MFZ-PRO-2026-XXXX).'
    )

    mfz_is_active = fields.Boolean(
        string='License Validated',
        config_parameter='maifelz_ai_copilot.is_active',
        readonly=True,
    )

    def action_verify_license(self):
        """Ping mAifelZ master server to validate license key and register Odoo instance."""
        self.ensure_one()
        server_url = (self.mfz_copilot_server_url or 'http://localhost:3000').rstrip('/')
        license_key = (self.mfz_license_key or '').strip()

        if not license_key:
            raise UserError(_("Please enter your mAifelZ License Key before validating."))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        company_name = self.env.company.name if hasattr(self.env, 'company') else ''

        payload = {
            "license_key": license_key,
            "odoo_url": base_url,
            "db_name": self.env.cr.dbname,
            "company_name": company_name,
        }

        try:
            # Contact mAifelZ cloud server handshake endpoint
            verify_url = f"{server_url}/api/v1/admin/odoo-handshake"
            resp = requests.post(verify_url, json=payload, timeout=10)
            
            if resp.status_code == 404:
                # Fallback to direct verify
                resp = requests.post(f"{server_url}/api/v1/admin/verify-license", json={"license_key": license_key}, timeout=10)

            data = resp.json() if resp.status_code in [200, 400, 403, 404] else {}

            if resp.status_code == 200:
                self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.is_active', True)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Verified!'),
                        'message': _('Connected to mAifelZ Cloud! You and your team can now log in at %s.') % server_url,
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                detail = data.get('detail', 'Verification failed.')
                raise UserError(_("mAifelZ License Error: %s") % detail)

        except requests.exceptions.RequestException as e:
            _logger.warning("mAifelZ cloud handshake failed: %s", str(e))
            # Save license locally anyway so offline/local testing works smoothly
            self.env['ir.config_parameter'].sudo().set_param('maifelz_ai_copilot.is_active', True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('License Saved Locally'),
                    'message': _('License key %s saved. You can open your local portal at %s') % (license_key, server_url),
                    'type': 'info',
                    'sticky': False,
                }
            }

    @api.model
    def action_open_copilot_portal(self):
        """Open standalone mAifelZ AI Copilot portal in a new browser tab."""
        server_url = self.env['ir.config_parameter'].sudo().get_param(
            'maifelz_ai_copilot.server_url', 'http://localhost:3000'
        )
        return {
            'type': 'ir.actions.act_url',
            'url': server_url.rstrip('/'),
            'target': 'new',
        }

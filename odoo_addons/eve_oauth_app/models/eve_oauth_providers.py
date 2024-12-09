import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class EveAuthProviderInherit(models.Model):
    _inherit = "auth.oauth.provider"

    eve_client_secret = fields.Char(string="Client Secret")
    eve_is_eve_online = fields.Boolean(compute='_compute_eve_is_eve_online')
    eve_user_type = fields.Selection([('internal', 'Internal User'),
                                      ('portal', 'Portal User')], default="portal", string='User Type')

    def _compute_eve_is_eve_online(self):
        """Compute whether the provider is Eve Online based on the auth endpoint"""
        for rec in self:
            _logger.debug("Computing eve_is_eve_online for provider: %s", rec.name)
            if rec.auth_endpoint:
                if 'login.eveonline.com' in rec.auth_endpoint:
                    rec.eve_is_eve_online = True
                    _logger.debug("Provider %s is Eve Online: %s", rec.name, rec.auth_endpoint)
                else:
                    rec.eve_is_eve_online = False
                    _logger.debug("Provider %s is not Eve Online: %s", rec.name, rec.auth_endpoint)
            else:
                rec.eve_is_eve_online = False
                _logger.debug("Provider %s has no auth_endpoint", rec.name)
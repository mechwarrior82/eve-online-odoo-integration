from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    character_id = fields.Char('Character ID')
    character_name = fields.Char('Character Name')

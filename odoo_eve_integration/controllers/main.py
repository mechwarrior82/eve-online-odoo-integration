from odoo import http
from odoo.http import request

class EveController(http.Controller):
    @http.route('/eve/auth', type='json', auth='public', methods=['POST'])
    def eve_auth(self, **kwargs):
        # Process the received data and create or update user records
        character_id = kwargs.get('character_id')
        character_name = kwargs.get('character_name')
        email = kwargs.get('email')

        # Create or update the user in Odoo
        user = request.env['res.users'].sudo().search([('character_id', '=', character_id)], limit=1)
        if not user:
            user = request.env['res.users'].sudo().create({
                'name': character_name,
                'login': email,
                'character_id': character_id,
            })
        return {'status': 'success'}

import logging
import requests
import werkzeug
import base64
from odoo.addons.auth_signup.models.res_partner import SignupError
from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied
from odoo.tools.misc import ustr

_logger = logging.getLogger(__name__)

class EveResUsersInherit(models.Model):
    _inherit = 'res.users'

    oauth_token = fields.Char(string="Oauth Token", readonly=True)
    eve_username = fields.Char(string="Eve Username", default="No username")
    eve_email = fields.Char(string="Eve Email")
    eve_character_id = fields.Char(string="Eve Character ID")
    eve_character_image_url = fields.Char(string="Eve Character Image URL", compute='_compute_character_image', store=True)

    @api.depends('eve_character_id')
    def _compute_character_image(self):
        _logger.debug("_compute_character_image: started")
        for user in self:
            if user.eve_character_id:
                user.eve_character_image_url = f"https://images.evetech.net/characters/{user.eve_character_id}/portrait"
                _logger.debug("Computed character image URL for user %s: %s", user.id, user.eve_character_image_url)
            else:
                user.eve_character_image_url = False
                _logger.debug("No Eve character ID found for user %s", user.id)

    @api.model
    def _sync_character_image(self, user_id):
        _logger.debug("Starting _sync_character_image for user_id: %s", user_id)
        user = self.browse(user_id)
        if user.eve_character_image_url:
            try:
                _logger.debug("Fetching character image from URL: %s", user.eve_character_image_url)
                response = requests.get(user.eve_character_image_url)
                response.raise_for_status()
                user.image_1920 = base64.b64encode(response.content)
                _logger.debug("Character image synced for user %s", user_id)
            except requests.exceptions.RequestException as e:
                _logger.error("Failed to fetch character image for user %s: %s", user_id, e)
        else:
            _logger.debug("No character image URL found for user %s", user_id)

    def _get_eve_corporation(self, user):
        """Fetch the corporation details from Eve Online using the character ID"""
        headers = {'Authorization': f'Bearer {user.oauth_token}'}
        response = requests.get(f'https://esi.evetech.net/latest/characters/{user.eve_character_id}/corporationhistory/', headers=headers)
        if response.ok:
            corporation_id = response.json()[0]['corporation_id']
            corp_response = requests.get(f'https://esi.evetech.net/latest/corporations/{corporation_id}/', headers=headers)
            if corp_response.ok:
                return corp_response.json()
        return None

    @api.model
    def auth_oauth(self, provider, params):
        """ Authenticate the user with the OAuth provider """
        _logger.debug("auth_oauth called with provider: %s and params: %s", provider, params)
        
        db, login, key = super(EveResUsersInherit, self).auth_oauth(provider, params)
        user = self.search([('login', '=', login)])
        if user:
            _logger.debug("User found: %s, syncing character image and corporation", user.id)
            
            _logger.debug("User Eve Character ID before update: %s", user.eve_character_id)
            user.write({'eve_character_id': user.oauth_uid})  # Set Eve Character ID using oauth_uid
            _logger.debug("User Eve Character ID after update: %s", user.eve_character_id)
            
            # Fetch the character's corporation details
            corporation_data = self._get_eve_corporation(user)
            if corporation_data:
                corp_name = corporation_data['name']
                _logger.debug("Fetched corporation name: %s", corp_name)
                
                # Check if the corporation exists in Odoo's partners
                corp_partner = self.env['res.partner'].search([('name', '=', corp_name)], limit=1)
                if not corp_partner:
                    _logger.debug("Corporation not found in partners, creating a new partner")
                    corp_partner = self.env['res.partner'].create({'name': corp_name})
                    
                # Update the user's partner to have its parent_id set to the corporation partner
                user.partner_id.write({'parent_id': corp_partner.id})
                
                # Retrieve the list of internal companies from res.company
                internal_companies = self.env['res.company'].search([])
                internal_corp_list = [company.name for company in internal_companies]
                
                # Log the internal corporation list
                _logger.debug("Internal Corporation List: %s", internal_corp_list)
                
                # Get the internal and portal user groups
                internal_user_group = self.env.ref('base.group_user')
                portal_user_group = self.env.ref('base.group_portal')
                
                # Set user role based on corporation
                if corp_name in internal_corp_list:
                    user.write({'groups_id': [(4, internal_user_group.id), (3, portal_user_group.id)]})  # Add to internal group, remove from portal group
                    _logger.debug("User set as internal user")
                else:
                    user.write({'groups_id': [(4, portal_user_group.id), (3, internal_user_group.id)]})  # Add to portal group, remove from internal group
                    _logger.debug("User set as portal user")
                
                user._compute_character_image()  # Force recomputation here
                user._sync_character_image(user.id)
            else:
                _logger.debug("Corporation data not found for user")
        else:
            _logger.debug("User not found for login: %s", login)
        
        return (db, login, key)


    def _auth_oauth_rpc(self, endpoint, access_code):
        """ Make a request to the OAuth provider's endpoint with the access code """
        _logger.debug("OAuth2: Starting _auth_oauth_rpc with endpoint: %s and access_code: %s", endpoint, access_code)
        if self.env.context.get('eve_online'):
            provider = self.env['auth.oauth.provider'].browse(self.env.context.get('eve_provider'))
            params = {
                'grant_type': 'authorization_code',
                'client_id': provider.client_id,
                'client_secret': provider.eve_client_secret,
                'code': access_code
            }
            response = requests.post(endpoint, data=params, headers={'Accept': 'application/json'}, timeout=10)
            return self._handle_oauth_response(response)
        else:
            return self._make_oauth_request(endpoint, access_code)

    def _handle_oauth_response(self, response):
        """ Handle OAuth response and extract user data """
        if response.ok:
            response_data = response.json()
            if 'error' in response_data:
                return self._redirect_with_error(5, response_data['error'])
            auth_token = response_data['access_token']
            headers = {'Authorization': f'Bearer {auth_token}'}
            eve_user_data = requests.get('https://login.eveonline.com/oauth/verify', headers=headers).json()
            _logger.debug("Eve Character ID from OAuth response: %s", eve_user_data.get('CharacterID'))  # Log the Character ID from response
            return {
                'key': auth_token,
                'user_id': eve_user_data.get('CharacterID'),
                'username': eve_user_data.get('CharacterName'),
                'name': eve_user_data.get('CharacterName'),
                'email': None,  # Eve Online SSO does not provide email
                'login': eve_user_data.get('CharacterName')
            }
        return {'error': 'invalid_request'}

    @api.model
    def _auth_oauth_validate(self, provider, access_code):
        """ Validate the access token with the OAuth provider """
        _logger.debug("OAuth2: Starting _auth_oauth_validate with provider: %s and access_code: %s", provider, access_code)
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = self._auth_oauth_rpc(oauth_provider.validation_endpoint, access_code)
        if validation.get("error"):
            raise Exception(validation['error'])
        if oauth_provider.data_endpoint:
            data = self._auth_oauth_rpc(oauth_provider.data_endpoint, validation['access_token'])
            validation.update(data)
        if self.env.context.get('eve_online'):
            return validation
        subject = next(filter(None, [
            validation.pop(key, None)
            for key in ['sub', 'id', 'user_id']
        ]), None)
        if not subject:
            raise AccessDenied('Missing subject identity')
        validation['user_id'] = subject
        return validation

    @api.model
    def _signup_create_user(self, values):
        """ Signup a new user using the template user """
        _logger.debug("Signup: Starting _signup_create_user with values: %s", values)
        provider = self.env.ref('eve_oauth_app.eve_provider')
        if provider.id == values.get('oauth_provider_id') and provider.eve_user_type == 'internal':
            if 'partner_id' not in values:
                if self._get_signup_invitation_scope() != 'b2c':
                    raise SignupError(_('Signup is not allowed for uninvited users'))
            return self._eve_create_user_from_default_template(values)
        else:
            return super(EveResUsersInherit, self)._signup_create_user(values)

    def _eve_create_user_from_default_template(self, values):
        """ Create a user from the default template """
        _logger.debug("Signup: Starting _eve_create_user_from_default_template with values: %s", values)
        template_user = self.env.ref('base.default_user')
        if not template_user.exists():
            raise ValueError(_('Signup: invalid template user'))
        if not values.get('login'):
            raise ValueError(_('Signup: no login given for new user'))
        if not values.get('partner_id') and not values.get('name'):
            raise ValueError(_('Signup: no name or partner given for new user'))

        values['active'] = True
        try:
            with self.env.cr.savepoint():
                return template_user.with_context(no_reset_password=True).copy(values)
        except Exception as e:
            raise SignupError(ustr(e))

    @api.model
    def _generate_signup_values(self, provider, validation, params):
        """ Generate signup values from the OAuth provider's validation data """
        _logger.debug("Signup: Starting _generate_signup_values with provider: %s, validation: %s, params: %s", provider, validation, params)
        provider_obj = self.env['auth.oauth.provider'].browse(provider)
        oauth_uid = validation['user_id']
        email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        name = validation['name']
        data = {
            'name': name,
            'login': name,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': params['access_token'],
            'active': True,
        }
        if provider_obj.name in ['Eve Online', 'eve_online']:
            login = validation.get('username')
            data.update({
                'login': login,
            })
        return data

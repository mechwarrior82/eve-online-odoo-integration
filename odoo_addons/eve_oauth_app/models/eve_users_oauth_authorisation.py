import logging
import requests
import werkzeug
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
            # response = requests.get(endpoint, params=params, timeout=10)
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
            return {
                'key': auth_token,
                'user_id': eve_user_data.get('CharacterID'),
                'username': eve_user_data.get('CharacterName'),
                'name': eve_user_data.get('CharacterName'),
                'email': None,  # Eve Online SSO does not provide email
                'login': eve_user_data.get('CharacterName')
            }
        return {'error': 'invalid_request'}

    def _make_oauth_request(self, endpoint, access_code):
        """ Make OAuth request based on authorization header setting """
        if self.env['ir.config_parameter'].sudo().get_param('auth_oauth.authorization_header'):
            response = requests.get(endpoint, headers={'Authorization': 'Bearer %s' % access_code}, timeout=10)
        else:
            response = requests.get(endpoint, params={'access_token': access_code}, timeout=10)
        if response.ok:
            return response.json()
        auth_challenge = werkzeug.http.parse_www_authenticate_header(response.headers.get('WWW-Authenticate'))
        if auth_challenge.type == 'bearer' and 'error' in auth_challenge:
            return dict(auth_challenge)
        return {'error': 'invalid_request'}

    def _redirect_with_error(self, error_code, error_msg=None):
        """ Redirect to login page with an error code """
        _logger.info('OAuth2: access denied, redirect to main page. REASON: %s' % error_msg)
        r_url = "/web/login?oauth_error=%s" % error_code
        redirect = werkzeug.utils.redirect(r_url, 303)
        redirect.autocorrect_location_header = False
        return redirect

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

    # @api.model ## This is the original method
    # def auth_oauth(self, provider, params):
    #     # Advice by Google (to avoid Confused Deputy Problem)
    #     # if validation.audience != OUR_CLIENT_ID:
    #     #   abort()
    #     # else:
    #     #   continue with the process
    #     access_token = params.get('access_token')
    #     validation = self._auth_oauth_validate(provider, access_token)

    #     # retrieve and sign in user
    #     login = self._auth_oauth_signin(provider, validation, params)
    #     if not login:
    #         raise AccessDenied()
    #     # return user credentials
    #     return (self.env.cr.dbname, login, access_token)

    # @api.model ## this is the new method
    # def auth_oauth(self, provider, params):
    #     """ Authenticate the user with the OAuth provider """
    #     _logger.debug("OAuth2: Starting auth_oauth with provider: %s and params: %s", provider, params)
    #     access_code = params.get('code')
    #     validation = self._auth_oauth_validate(provider, access_code)
    #     params['access_token'] = validation['key']
    #     login = self._auth_oauth_signin(provider, validation, params)
    #     if not login:
    #         raise AccessDenied()
    #     return (self.env.cr.dbname, login, validation['key'])

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
        # access_token = validation['key']
        data = {
            'name': name,
            'login': name,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': params['access_token'], # 'oauth_access_token': access_token,
            'active': True,
        }
        if provider_obj.name in ['Eve Online', 'eve_online']:
            login = validation.get('username')
            data.update({
                'login': login,
            })
        return data

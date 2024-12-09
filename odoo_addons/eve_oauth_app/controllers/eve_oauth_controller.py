import json
import logging
import werkzeug
from odoo.addons.auth_oauth.controllers.main import OAuthLogin, OAuthController, fragment_to_query_string
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url
from werkzeug.exceptions import BadRequest
from odoo import http, api, SUPERUSER_ID, _
from odoo import registry as registry_get
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)

class EveAuthLoginHome(Home):
    """Custom login home that handles web login with OAuth providers"""

    @http.route()
    def web_login(self, *args, **kw):
        """Handle the web login route"""
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            return request.redirect(request.params.get('redirect'))
        eve_providers = self.list_providers()
        response = super(OAuthLogin, self).web_login(*args, **kw)
        if response.is_qweb:
            error = self.get_oauth_error_message(request.params.get('oauth_error'))
            response.qcontext['providers'] = eve_providers
            if error:
                response.qcontext['error'] = error
        return response

    def get_oauth_error_message(self, error_code):
        """Return error message based on OAuth error code"""
        error_messages = {
            '1': _("You are not allowed to signup on this database."),
            '2': _("Access Denied"),
            '3': _("Email Already Exist.\nPlease contact your Administrator."),
            '4': _("Validation End Point either Not present or invalid.\nPlease contact your Administrator"),
            '5': _("Eve Online Oauth Api Failed, For more information please contact Administrator"),
            '6': _("Eve Online Oauth Api Failed,\nClient ID or Client Secret Not present or has been compromised\n"
                   "For more information please contact Administrator")
        }
        return error_messages.get(error_code, None)

class EveOAuthController(OAuthController):
    """OAuth controller for handling Eve Online OAuth signin"""

    @http.route('/eve/auth_oauth/signin', type='http', auth='none')
    @fragment_to_query_string
    def eve_signin(self, **kw):
        """Handle the OAuth signin callback"""
        _logger.debug("OAuth2: Signin called with kw: %s", kw)
        eve_state = json.loads(kw['state'])
        eve_dbname = eve_state['d']
        _logger.debug("OAuth2: Using database: %s", eve_dbname)
        if not http.db_filter([eve_dbname]):
            return BadRequest()
        return self.process_signin(eve_state, kw)

    def process_signin(self, eve_state, kw):
        """Process the OAuth signin"""
        eve_provider = eve_state['p']
        eve_context = eve_state.get('c', {})
        eve_registry = registry_get(eve_state['d'])
        with eve_registry.cursor() as cr:
            try:
                _logger.debug("OAuth2: eve_provider and Context: %s  |  %s", eve_provider, eve_context)
                eve_context.update({'eve_provider': eve_provider, 'eve_online': True})
                env = api.Environment(cr, SUPERUSER_ID, eve_context)
                db, login, key = env['res.users'].sudo().auth_oauth(eve_provider, kw)
                _logger.debug("OAuth2: login: %s", login)
                cr.commit()
                return self.redirect_to_url(eve_state, db, login, key)
            except AttributeError:
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (eve_state['d'],))
                url = "/web/login?oauth_error=1"
            except AccessDenied:
                _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists,\n'
                             'without setting cookies')
                url = "/web/login?oauth_error=3"
            except Exception as e:
                _logger.exception("OAuth2: Exception during signin: %s", e)
                url = "/web/login?oauth_error=2"
        return request.redirect(url, 303)

    def redirect_to_url(self, eve_state, db, login, key):
        """Redirect to the appropriate URL after successful signin"""
        eve_action = eve_state.get('a')
        eve_menu = eve_state.get('m')
        redirect = werkzeug.urls.url_unquote_plus(eve_state['r']) if eve_state.get('r') else False
        url = '/web'
        if redirect:
            url = redirect
        elif eve_action:
            url = '/web#action=%s' % eve_action
        elif eve_menu:
            url = '/web#menu_id=%s' % eve_menu
        _logger.debug("OAuth2: Redirecting to URL: %s", url)
        pre_uid = request.session.authenticate(db, login, key)
        resp = request.redirect(_get_login_redirect_url(pre_uid, url), 303)
        resp.autocorrect_location_header = False
        if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user._is_internal():
            resp.location = '/'
        return resp

class EveOAuthLogin(OAuthLogin):
    """OAuth login handler for Eve Online"""

    def list_providers(self):
        """List available OAuth providers"""
        try:
            eve_providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception as e:
            _logger.error("Error fetching OAuth providers: %s", e)
            eve_providers = []
        for eve_provider in eve_providers:
            eve_provider['auth_link'] = self.get_auth_link(eve_provider)
        return eve_providers

    def get_auth_link(self, eve_provider):
        """Generate auth link for the provider"""
        eve_state = self.get_state(eve_provider)
        _logger.debug("OAuth2: Provider state: %s", eve_state)
        params = dict(
            response_type='code' if eve_provider.get('name') in ['Eve Online', 'eve_online'] else 'token',
            client_id=eve_provider['client_id'],
            redirect_uri=request.httprequest.url_root + 'oauth/callback', #'/eve/auth_oauth/signin',
            scope=eve_provider['scope'],
            state=json.dumps(eve_state),
        )
        return "%s?%s" % (eve_provider['auth_endpoint'], werkzeug.urls.url_encode(params))

# class EveCallbackHandler(http.Controller):
#     """OAuth callback handler"""

#     @http.route(['/oauth/callback'], auth='public', csrf=False, methods=['GET', 'POST'], type='http')
#     def get_oauth_token(self, **post):
#         """Handle the OAuth callback"""
#         _logger.debug("OAuth2: Callback received with post data: %s", post)
#         provider = self.get_provider(post)
#         eve_redirect_url = request.httprequest.url_root + "eve/auth_oauth/signin"
#         if post.get("code"):
#             client_id = provider.client_id
#             client_secret = provider.mrt_client_secret
#             _logger.debug("OAuth2: Client ID: %s, Client Secret: %s", client_id, client_secret)
#             if not client_id or not client_secret:
#                 return self.redirect_with_error(6)
#             else:
#                 # Exchange the authorization code for an access token
#                 access_code = post.get("code")
#                 access_token_response = self._auth_oauth_rpc(provider.validation_endpoint, access_code)
#                 if 'access_token' in access_token_response:
#                     # Add access_token to the post data and redirect internally
#                     post['access_token'] = access_token_response['access_token']
#                     return self.redirect_with_token(eve_redirect_url, post, provider)
#                 else:
#                     return self.redirect_with_error(5)

class EveCallbackHandler(http.Controller):
    """OAuth callback handler"""

    @http.route(['/oauth/callback'], auth='public', csrf=False, methods=['GET', 'POST'], type='http')
    def get_oauth_token(self, **post):
        """Handle the OAuth callback"""
        _logger.debug("OAuth2: Callback received with post data: %s", post)
        provider = self.get_provider(post)
        eve_redirect_url = request.httprequest.url_root + "eve/auth_oauth/signin"
        if post.get("code"):
            client_id = provider.client_id
            client_secret = provider.eve_client_secret
            _logger.debug("OAuth2: Client ID: %s, Client Secret: %s", client_id, client_secret)
            if not client_id or not client_secret:
                return self.redirect_with_error(6)
            else:
                return self.redirect_with_token(eve_redirect_url, post, provider)

    def get_provider(self, post):
        """Get OAuth provider from post data"""
        if post.get('state'):
            return request.env['auth.oauth.provider'].sudo().browse(json.loads(post.get('state')).get('p'))
        else:
            provider = request.env.ref('eve_oauth_app.eve_provider')
            provider = request.env[provider._name].sudo().browse(provider.id)
        _logger.debug("OAuth2: Provider: %s", provider)
        return provider

    def redirect_with_error(self, error_code):
        """Redirect to login page with an error code"""
        r_url = "/web/login?oauth_error=%s" % error_code
        _logger.info('OAuth2: Error occurred, redirecting to: %s', r_url)
        redirect = werkzeug.utils.redirect(r_url, 303)
        redirect.autocorrect_location_header = False
        return redirect

    def redirect_with_token(self, eve_redirect_url, post, provider):
        """Redirect with OAuth token"""
        eve_post_url = 'access_token=%s&state=%s&provider=%s' % (
            post.get("code"), post.get('state'), provider.id)
        eve_redirect_url = "%s?%s" % (eve_redirect_url, eve_post_url)
        _logger.debug("OAuth2: Redirecting to: %s", eve_redirect_url)
        return werkzeug.utils.redirect(eve_redirect_url)

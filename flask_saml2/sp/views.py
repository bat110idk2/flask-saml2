import logging

from flask import Response, make_response, redirect, request, url_for
from flask.views import MethodView, View

from flask_saml2.exceptions import CannotHandleAssertion, UserNotAuthorized

from . import sp

logger = logging.getLogger(__name__)


class SAML2ViewMixin:
    def __init__(self, *, sp: 'sp.ServiceProvider', **kwargs):
        super().__init__(**kwargs)
        self.sp = sp


class SAML2View(SAML2ViewMixin, MethodView):
    pass


class Login(SAML2View):
    """
    Log in to this SP using SAML.
    """
    def get(self):
        print('====> Login')
        handler = self.sp.get_default_idp_handler()
        print(f'handler:{handler}')
        print(f'handler.entity_id:{handler.entity_id}')
        login_next = self.sp.get_login_return_url()
        print(f'login_next:{login_next}')
        if handler:
            print(f'redirect:{url_for(".login_idp", entity_id=handler.entity_id, next=login_next)}')
            return redirect(url_for('.login_idp', entity_id=handler.entity_id, next=login_next))
        return self.sp.render_template(
            'flask_saml2_sp/choose_idp.html',
            login_next=login_next,
            handlers=self.sp.get_idp_handlers())


class LoginIdP(SAML2View):
    """
    Log in using a specific IdP.
    """
    def get(self):
        print('====> LoginIdP')
        entity_id = request.args['entity_id']
        print(f'entity_id:{entity_id}')
        handler = self.sp.get_idp_handler_by_entity_id(entity_id)
        print(f'handler:{handler}')
        login_next = self.sp.get_login_return_url()
        print(f'login_next:{login_next}')
        print('===')
        print('===')
        print('===')
        # print(f'=> make_login_request_url:{handler.make_login_request_url(login_next)}')
        return redirect(handler.make_login_request_url(login_next))


class Logout(SAML2View):
    """
    Initiates a logout with the IdP used to authenticate the currently logged
    in user.
    """
    def post(self):
        handler = self.sp.get_idp_handler_by_current_session()
        auth_data = self.sp.get_auth_data_in_session()
        relay_state = self.sp.get_logout_return_url()
        response = redirect(handler.make_logout_request_url(auth_data, relay_state))

        self.sp.logout()

        return response


class SingleLogout(SAML2View):
    """
    Logs the user out of this SP and sends them to the next logout destination.
    """
    def get(self):
        # TODO Verify this SLO request is valid, process it correctly, send the
        # user back to the IdP for further sign outs...
        return self.do_logout()

    def do_logout(self, handler):
        self.sp.logout()
        ...  # TODO


class AssertionConsumer(SAML2View):
    def post(self):
        print(f'======> AssertionConsumer')
        saml_request = request.form['SAMLResponse']
        relay_state = request.form['RelayState']

        print(f'= saml_request : {saml_request}')
        print(f'= relay_state : {relay_state}')

        for handler in self.sp.get_idp_handlers():
            try:
                response = handler.get_response_parser(saml_request)
                print(f'= response : {response}')
                auth_data = handler.get_auth_data(response)
                print(f'= auth_data : {auth_data}')
                return self.sp.login_successful(auth_data, relay_state)
            except CannotHandleAssertion:
                continue
            except UserNotAuthorized:
                return self.sp.render_template('flask_saml2_sp/user_not_authorized.html')


class Metadata(SAML2View):
    """
    Replies with the XML metadata for this Service Provider / IdP handler pair.
    """
    def get(self):
        print(f'======> Metadata')
        metadata = self.sp.render_template(
            'flask_saml2_sp/metadata.xml',
            **self.sp.get_metadata_context())

        response = make_response(metadata)
        response.headers['Content-Type'] = 'application/xml'
        return response


class CannotHandleAssertionView(SAML2ViewMixin, View):
    def dispatch_request(self, exception):
        print(f'======> CannotHandleAssertionView')
        logger.exception("Can not handle request", exc_info=exception)
        return Response(status=400)

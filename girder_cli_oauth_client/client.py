import json
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse
import webbrowser

from authlib.common.security import generate_token
from authlib.integrations.requests_client import OAuth2Session
from xdg import BaseDirectory

CODE_CHALLENGE_METHOD = 'S256'


AuthHeaders = Dict


class GirderCliOAuthClient:
    def __init__(self, oauth_url: str, client_id: str, scopes: Optional[list[str]] = None) -> None:
        self.oauth_url = oauth_url.rstrip('/')
        self.client_id = client_id
        self._scopes = [] if not scopes else scopes
        self._session = OAuth2Session(
            self.client_id, code_challenge_method=CODE_CHALLENGE_METHOD, scope=self.scope
        )

    @property
    def _data_path(self) -> Path:
        hostname = urlparse(self.oauth_url).hostname
        assert hostname
        namespace = Path('girder_cli_oauth_client') / Path(hostname) / Path(self.client_id)
        return Path(BaseDirectory.save_data_path(namespace))

    @property
    def _token_path(self) -> Path:
        return self._data_path / 'token.json'

    @property
    def scope(self) -> str:
        return ' '.join(self._scopes)

    def _load(self) -> None:
        if self._token_path.exists():
            with open(self._token_path, 'r') as infile:
                self._session.token = json.load(infile)

    def _save(self) -> None:
        if self._session.token:
            with open(self._token_path, 'w') as outfile:
                json.dump(self._session.token, outfile, indent=4)

    def _reset_session(self):
        self._session = OAuth2Session(
            self.client_id, code_challenge_method=CODE_CHALLENGE_METHOD, scope=self.scope
        )

    @property
    def auth_headers(self) -> Optional[AuthHeaders]:
        if self._session.token:
            auth_value = (
                f'{self._session.token["token_type"]} {self._session.token["access_token"]}'
            )
            return {'Authorization': auth_value}

    def _get_authorization_url(self) -> str:
        self._code_verifier = generate_token(128)

        return self._session.create_authorization_url(
            f'{self.oauth_url}/authorize',
            code_verifier=self._code_verifier,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob',
        )[0]

    def _get_oauth_token(self, code: str) -> dict:
        auth_response_kwargs = {
            'client_id': self.client_id,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'code': code,
            # PKCE
            'code_challenge_method': CODE_CHALLENGE_METHOD,
        }

        authorization_url = f'{self.oauth_url}/authorize/?{urlencode(auth_response_kwargs)}'
        return self._session.fetch_token(
            f'{self.oauth_url}/token/',
            authorization_response=authorization_url,
            code_verifier=self._code_verifier,
        )

    def maybe_restore_login(self) -> Optional[AuthHeaders]:
        self._load()
        if self._session.token:
            # TODO: look into ensure_active_token
            if self._session.token.is_expired():
                self._session.refresh_token(f'{self.oauth_url}/token/')
                self._save()

            if set(self._session.token['scope'].split()) < set(self._scopes):
                # One or more requested scopes aren't provided in the existing token. This is really
                # common when developing and modifying the scopes parameter. This invalidates
                # the cached token, so log the user out so a new login flow begins.
                # Use an inequality comparison, as sometimes the scopes returned are different from
                # the scopes requested; usually though, this is the server returning more scopes.
                self.logout()

        return self.auth_headers

    def login(self) -> AuthHeaders:
        # TODO: try catch webbrowser.Error, print the url?
        webbrowser.open(self._get_authorization_url())
        code = input('enter the code shown in your browser: ')
        self._session.token = self._get_oauth_token(code)
        self._save()
        return self.auth_headers

    def logout(self) -> None:
        if self._session.token:
            self._session.revoke_token(f'{self.oauth_url}/revoke_token/')
            self._reset_session()

            if self._token_path.exists():
                self._token_path.unlink()

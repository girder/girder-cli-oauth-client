import json
import logging
import multiprocessing
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode
import webbrowser

from authlib.common.security import generate_token
from authlib.integrations.requests_client import OAuth2Session
from xdg import BaseDirectory

from girder_cli_oauth_client.redirect_handler import _find_free_port, get_token

# Disable werkzeug "Running on..." log messages
logging.getLogger("werkzeug").setLevel(logging.WARN)

CODE_CHALLENGE_METHOD = 'S256'


AuthHeaders = Dict


class GirderCliOAuthClient:
    def __init__(
        self, oauth_url: str, client_id: str, package_name: str, scope: Optional[str] = None
    ) -> None:
        self.oauth_url = oauth_url.rstrip('/')
        self.client_id = client_id
        self.package_name = package_name
        self.scope = scope
        self._session = OAuth2Session(
            self.client_id, code_challenge_method=CODE_CHALLENGE_METHOD, scope=scope
        )

    @property
    def _data_path(self) -> Path:
        return Path(BaseDirectory.save_data_path(self.package_name))

    @property
    def _token_path(self) -> Path:
        return self._data_path / 'token.json'

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
            return {'Authorization': f'Bearer {self._session.token["access_token"]}'}

    def _get_authorization_url(self) -> str:
        self._code_verifier = generate_token(128)

        return self._session.create_authorization_url(
            f'{self.oauth_url}/authorize',
            code_verifier=self._code_verifier,
        )[0]

    def _fetch_oauth_token(self, code: str, state: str) -> None:
        auth_response_kwargs = {
            'client_id': self.client_id,
            'code': code,
            'state': state,
        }

        authorization_url = f'{self.oauth_url}/authorize/?{urlencode(auth_response_kwargs)}'
        self._session.fetch_token(
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
        return self.auth_headers

    def login(self) -> AuthHeaders:
        self._port = _find_free_port()
        # Note: setting redirect_uri directly on the session is the only easy way to make
        # sure all requests get it.
        self._session.redirect_uri = f'http://127.0.0.1:{self._port}'

        queue = multiprocessing.Queue()
        webserver = multiprocessing.Process(target=get_token, args=(queue, self._port))
        webserver.start()

        # TODO: try catch webbrowser.Error, print the url?
        auth_url = self._get_authorization_url()
        webbrowser.open(auth_url)

        resp = queue.get(block=True)

        self._fetch_oauth_token(resp['code'], resp['state'])

        self._save()

        # Note: terminating the webserver too quickly will cause the response to never be
        # rendered.
        webserver.terminate()
        return self.auth_headers

    def logout(self) -> None:
        if self._session.token:
            self._session.revoke_token(f'{self.oauth_url}/revoke_token/')
            self._reset_session()

            if self._token_path.exists():
                self._token_path.unlink()

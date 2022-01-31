# girder-cli-oauth-client

A Python library for performing OAuth login to a Girder 4 (Django) server.

## Description
This provides support for authenticating with Girder 4 servers,
using the OAuth2.0 Authorization Code Grant with PKCE flow and out-of-band redirection.

## Usage
* Install the library:
  ```bash
  pip install girder-cli-oauth-client
  ```

* Instantiate an `OauthClient` with your application-specific configuration:
  ```py
  from girder_cli_oauth_client import GirderCliOAuthClient

  oauth_client = GirderCliOAuthClient(
      'http://localhost:8000/oauth/',
      '1ohsuyWIx9fEsJhmAH2AWGNUqd8Wsd7LHyongtVy',
      ['identity'],
  )
  ```

* Call `login` when it's time to start a login flow:
  ```py
  oauth_client.login()  # open the browser to login and wait for a code
  ```

* At the start of *every* application start, unconditionally call `maybe_restore_login`, to attempt to
  restore a login state; this will no-op if no login is present.
  ```py
  oauth_client.maybe_restore_login()
  ```

* Include these headers with every API request:
  ```py
  requests.get('http://localhost:8000/api/users/me', headers=oauth_client.auth_headers)
  ```

* Call `logout` to clear any active login:
  ```py
  oauth_client.logout()
  ```

## Example app
This repository comes bundled with an [example application](example/cli.py). Run it with:
```bash
git clone https://github.com/girder/girder-cli-oauth-client.git
pip install -e '.[dev]'
cd example
python cli.py login
python cli.py me
```

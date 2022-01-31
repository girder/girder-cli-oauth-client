import click
import requests

from girder_cli_oauth_client import GirderCliOAuthClient


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj['client'] = GirderCliOAuthClient(
        'http://127.0.0.1:8000/oauth',
        'BqGiENNBN0cB0gSP5FcWUj5KHUP9NQswcHLXKvCX',
        ['identity'],
    )

    ctx.obj['auth_headers'] = ctx.obj['client'].maybe_restore_login()


@cli.command()
@click.pass_context
def login(ctx):
    if not ctx.obj['auth_headers']:
        ctx.obj['client'].login()
        click.echo('Success!')
    else:
        click.echo('Already logged in.')


@cli.command()
@click.pass_context
def me(ctx):
    if not ctx.obj['auth_headers']:
        click.echo('Not logged in, try the "login" command.')
    else:
        r = requests.get('http://127.0.0.1:8000/api/v2/users/me', headers=ctx.obj['auth_headers'])
        r.raise_for_status()
        click.echo(f'hello {r.json()["email"]}!')


if __name__ == '__main__':
    cli(obj={})

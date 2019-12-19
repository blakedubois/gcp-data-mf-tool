# coding: utf-8

import json
import datetime
import click
import logging
import csv
import sys
from pathlib import Path

from mf.config import read_config
from mf.manifest import BuildInfo, Manifest
from mf.log import LOGGER

PROJECT_OPT = 'project'
FORMAT_OPT = 'format'


def main():
    cli(auto_envvar_prefix='MF')


# noinspection PyShadowingBuiltins
@click.group()
@click.option('--format', default='json', type=click.Choice(['json', 'csv', 'text']),
              help='Output format')
@click.option('--config', default=None, help='Configuration file', type=click.Path())
@click.option('--debug', is_flag=True, help='Enable debugging', default=False)
@click.pass_context
def cli(ctx, format, config, debug):
    ctx.ensure_object(dict)

    LOGGER.setLevel(logging.INFO)
    if debug:
        LOGGER.setLevel(logging.DEBUG)

    root_dir = __current_dir()

    ctx.obj['is_debug'] = debug
    ctx.obj['root_dir'] = root_dir
    ctx.obj[PROJECT_OPT] = read_config(root_dir, mf_file=Path(config) if config else None)
    ctx.obj[FORMAT_OPT] = format


@cli.group()
def builds():
    """
    Operations with Cloud Build artifacts.
    """
    pass



@builds.command()
@click.option('--git_branch', required=True, help='Current git branch name')
@click.option('--git_commit', required=True, help='Current git checksum')
@click.option('--build_id', required=True, help='Current build id')
@click.option('-nu', '--no-upload', is_flag=True, default=False,
              help='Should this tool upload artifacts?')
@click.pass_context
def put(ctx, git_branch, git_commit, build_id, no_upload):
    """
    Scan current folder for .mf.json file that contains description of current repository.
    Based on configuration upload all found binaries into gcs and update manifest.json with information about success build.
    """

    ctx.ensure_object(dict)

    root_dir = ctx.obj['root_dir']
    project = ctx.obj[PROJECT_OPT]

    assert git_branch and len(str(git_branch)) > 0, '--git_branch have to be non empty string'
    assert git_commit and len(str(git_commit)) > 0, '--git_commit have to be non empty string'
    assert build_id and len(str(build_id)) > 0, '--build_id have to be non empty string'

    if project is None:
        click.echo(f'config file not found in {root_dir}', err=True)
        return 1

    LOGGER.debug("Current project %s", project)

    if no_upload:
        click.echo('Content wont be uploaded...')

    build_info = BuildInfo(git_branch=git_branch,
                           git_sha=git_commit,
                           build_id=build_id,
                           date=datetime.datetime.utcnow())

    actual_manifest = Manifest(project.bucket, project.repository)
    new = actual_manifest.update(build_info, project, upload=not no_upload)
    if no_upload:
        click.echo(json.dumps(new, indent=4))


@builds.command()
@click.pass_context
@click.option('--bucket', help='Root GCS bucket for all artifacts')
@click.option('--repo', help='Current repository name, a.k.a. semantic name')
@click.option('--app', help='Specific repository\'s application name. Expects that repository can '
                            'have more then one application inside.')
@click.option('--branch', help='Git branch name')
@click.option('-if', '--include-fields',
              help='Include only this fields (comma separated lost). Available: branch,app,commit,url')
def list(ctx, bucket, repo, app, branch, include_fields):
    """
    Listing for all latest build binaries (sorted by: branch, app name, time).

    [ mfutil builds latest ls ] will prints all last success built binaries for all branches.

    [ mfutil builds latest ls --branch <branch-name> ] will prints all binaries for target branch

    [ mfutil builds latest ls --branch <branch-name> --app <app-name> ] will prints all binaries for target branch and target app
    """

    ctx.ensure_object(dict)
    project = ctx.obj[PROJECT_OPT]

    if project is None and (bucket is None and repo is None):
        click.echo(f'Config file not found in [{ctx.obj["root_dir"]}] and --bucket not specifies.\n'
                   'Please specify --bucket and --repo parameters or --config file path', err=True)
        return 1

    manifest = Manifest(project.bucket, project.repository)
    binaries_list = manifest.search(branch_name=branch, app_name=app)

    if len(binaries_list) == 0:
        click.echo('no builds found...')

    if include_fields:
        keys = set(str(include_fields).split(','))
        fields_filter = lambda d: dict(filter(lambda kv: kv[0] in keys, d.items()))
    else:
        fields_filter = lambda d: d

    format_ = ctx.obj[FORMAT_OPT]
    if format_ == 'json':
        for d in binaries_list:
            click.echo(json.dumps(fields_filter(d)))

    elif format_ == 'csv':
        w = csv.DictWriter(sys.stdout,
                           fieldnames=fields_filter(binaries_list[0]).keys() if len(binaries_list) > 0 else set())
        w.writeheader()
        for d in binaries_list:
            w.writerow(fields_filter(d))

    elif format_ == 'text':
        w = csv.DictWriter(sys.stdout,
                           delimiter='\t',
                           fieldnames=fields_filter(binaries_list[0]).keys() if len(binaries_list) > 0 else set())

        for d in binaries_list:
            w.writerow(fields_filter(d))


@builds.command()
@click.pass_context
@click.option('--bucket', help='Root GCS bucket for all artifacts')
@click.option('--repo', help='Current repository name, a.k.a. semantic name')
@click.option('--app', help='Specific repository\'s application name. Expects that repository can '
                            'have more then one application inside.')
@click.option('--branch', help='Last build artifacts for branch name', required=True)
@click.argument('destination', type=click.Path(exists=True, file_okay=False))
def get(ctx, bucket, repo, app, branch, destination):
    """
    Download all found binaries.
    """

    ctx.ensure_object(dict)
    project = ctx.obj[PROJECT_OPT]

    if project is None and (bucket is None and repo is None):
        click.echo(f'Config file not found in [{ctx.obj["root_dir"]}] and --bucket not specifies.\n'
                   'Please specify --bucket and --repo parameters or --config file path', err=True)
        return 1

    manifest = Manifest(project.bucket, project.repository)
    binaries_list = manifest.search(branch_name=branch, app_name=app)

    for bin in binaries_list:
        manifest.download(bin, dest=destination)
        LOGGER.info("Downloading... %s", bin['url'])

    pass


def __current_dir() -> Path:
    cur = Path('.').absolute()
    LOGGER.debug(f'Set current project root dir ({cur})')
    return cur

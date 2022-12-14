# coding: utf-8

from requests import Request, Session
from odoo import fields, models

import logging
import warnings
from cryptography.utils import CryptographyDeprecationWarning

# Ignoring pyOpenSSL warnings
warnings.simplefilter('ignore', category=CryptographyDeprecationWarning)
_logger = logging.getLogger(__name__)


class ExternalDataCredential(models.Model):
    _name = 'external.data.credential'
    _description = "External Data Transporter"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    value = fields.Char()
    document = fields.Text()
    file = fields.Binary()
    transporter_ids = fields.Many2many(
        'external.data.transporter',
        string="Transporters",
    )


class ExternalDataTransporter(models.Model):
    _name = 'external.data.transporter'
    _description = "External Data Transporter"

    name = fields.Char(required=True)
    protocol = fields.Selection(
        selection=[
            ('local_fs', 'local filesystem'),
            ('http', "HTTP"),
            ('ftp', "FTP"),
            ('s3', "S3"),
            ('orm', "Odoo ORM"),
        ],
        required=True,
    )
    auth_method = fields.Selection(
        string="Auth method",
        selection=[
            ('sudo', "sudo"),
            ('userpass', "user/password"),
            ('tls', "TLS cert"),
            ('http_login', "HTTP web login"),
            ('http_basic', "HTTP Basic"),
            ('http_bearer', "HTTP Bearer"),
            ('http_proxy_basic', "HTTP Basic (proxy)"),
            ('http_proxy_bearer', "HTTP Bearer (proxy)"),
            ('http_header', "HTTP custom headers"),
            ('http_cookie', "HTTP custom cookies"),
        ],
    )
    credential_ids = fields.Many2many(
        'external.data.credential',
        string="Credentials",
    )
    http_request_method = fields.Selection(
        string="Method",
        selection=[
            ('GET', "GET"),
            ('POST', "POST"),
        ],
        default='GET',
    )
    content_type = fields.Selection(
        string="Content type",
        selection=[
            ('binary', "binary"),
            ('text', "text"),
        ],
        default='binary',
    )

    def fetch(self, resource_id):
        self.ensure_one()
        resource = self.env['external.data.resource'].browse(resource_id)
        if not resource.exists():
            return False

        if self.protocol == 'http':
            return self._fetch_http(resource)
        elif self.protocol == 'local_fs':
            return self._fetch_local_fs(resource)
        else:
            # TODO: raise exception
            return False

    def deliver(self, resource_id):
        pass

    def _fetch_http(self, resource):
        self.ensure_one()
        ses = Session()
        req = Request(self.http_request_method, resource.url)
        req_prepped = ses.prepare_request(req)
        res = ses.send(req_prepped)
        if res.status_code == 200:
            if self.content_type == 'binary':
                return res.content
            elif self.content_type == 'text':
                return res.text
        return False

    def _fetch_local_fs(self, resource):
        self.ensure_one()
        # TODO: check whether file or directory
        if self.content_type == 'binary':
            mode = 'rb'
        elif self.content_type == 'text':
            mode = 'r'
        try:
            reader = open(resource.url, mode)
            return reader.read()
        except Exception as e:
            _logger.error(e)

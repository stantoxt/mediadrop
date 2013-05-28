# This file is a part of MediaCore CE (http://www.mediacorecommunity.org),
# Copyright 2009-2013 MediaCore Inc., Felix Schwarz and other contributors.
# For the exact contribution history, see the git revision log.
# The source code contained in this file is licensed under the GPLv3 or
# (at your option) any later version.
# See LICENSE.txt in the main project directory, for more information.

import logging

from alembic.config import Config
from alembic.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, Table, Unicode, UnicodeText

from mediacore.model import metadata, DBSession

__all__ = ['AlembicMigrations']

migrate_to_alembic_mapping = {
    49: None,
    50: u'50258ad7a96d',
    51: u'51c050c6bca0',
    52: u'432df7befe8d',
    53: u'4d27ff5680e5',
    54: u'280565a54124',
    55: u'16ed4c91d1aa',
    56: u'30bb0d88d139',
    57: u'3b2f74a50399',
}
migrate_table = Table('migrate_version', metadata,
    Column('repository_id', Unicode(250), autoincrement=True, primary_key=True),
    Column('repository_path', UnicodeText, nullable=True),
    Column('version', Integer, nullable=True),
)

def version_table_name(conf):
    table_name = 'alembic_migrations'
    table_prefix = conf.get('db_table_prefix', None)
    if not table_prefix:
        return table_name
    # treat 'foo' and 'foo_' the same so we're not too harsh on the users
    normalized_prefix = table_prefix.rstrip('_')
    return normalized_prefix + '_' + table_name


class AlembicMigrations(object):
    def __init__(self, context=None, log=None):
        self.context = context
        self.log = log or logging.getLogger(__name__)
    
    @classmethod
    def from_config(cls, conf, **kwargs):
        context = cls.init_environment_context(conf)
        return AlembicMigrations(context=context, **kwargs)
    
    @classmethod
    def init_environment_context(cls, conf):
        alembic_cfg = Config(ini_section='main')
        alembic_cfg.set_main_option('script_location', 'mediacore:migrations')
        alembic_cfg.set_main_option('sqlalchemy.url', conf['sqlalchemy.url'])
        # TODO: add other sqlalchemy options
        alembic_cfg.set_main_option('file_template', '%%(day).3d-%%(rev)s-%%(slug)s')
        
        script = ScriptDirectory.from_config(alembic_cfg)
        def upgrade(current_db_revision, context):
            return script._upgrade_revs('head', current_db_revision)
        
        table_name = version_table_name(conf)
        return EnvironmentContext(alembic_cfg, script, fn=upgrade, version_table=table_name)
    
    def map_migrate_version(self):
        migrate_version_query = migrate_table.select(
            migrate_table.c.repository_id == u'MediaCore Migrations'
        )
        result = DBSession.execute(migrate_version_query).fetchone()
        db_migrate_version = result.version
        if db_migrate_version in migrate_to_alembic_mapping:
            return migrate_to_alembic_mapping[db_migrate_version]
        
        earliest_upgradable_version = sorted(migrate_to_alembic_mapping)[0]
        if db_migrate_version < earliest_upgradable_version:
            error_msg = ('Upgrading from such an old version of MediaCore is not '
                'supported. Your database is at version %d but upgrades are only '
                'supported from MediaCore CE 0.9.0 (DB version %d). Please upgrade '
                '0.9.0 first.')
            self.log.error(error_msg % (db_migrate_version, earliest_upgradable_version))
        else:
            self.log.error('Unknown DB version %s. Can not upgrade to alembic' % db_migrate_version)
        raise AssertionError('unsupported DB migration version.')
    
    def is_db_scheme_current(self):
        if not self.alembic_table_exists():
            return False
        self.context.configure(connection=metadata.bind.connect(), transactional_ddl=True)
        migration_context = self.context.get_context()
        db_needs_upgrade = self.head_revision() != migration_context.get_current_revision()
        return not db_needs_upgrade
    
    def head_revision(self):
        return self.context.get_head_revision()
    
    def _table_exists(self, table_name):
        engine = metadata.bind
        db_connection = engine.connect()
        exists = engine.dialect.has_table(db_connection, table_name)
        return exists
    
    def migrate_table_exists(self):
        return self._table_exists('migrate_version')
    
    def alembic_table_exists(self):
        table_name = self.context.context_opts.get('version_table')
        return self._table_exists(table_name)
    
    def run(self):
        self.log.info('Running any new migrations, if there are any')
        self.context.configure(connection=metadata.bind.connect(), transactional_ddl=True)
        with self.context:
            self.context.run_migrations()
    
    # -----------------------------------------------------------------------------
    # mostly copied from alembic 0.5.0
    # The problem in alembic.command.stamp() is that it builds a new 
    # EnvironmentContext which does not have any ability to configure the
    # version table name and MediaCore uses a custom table name.
    def stamp(self, revision):
        """'stamp' the revision table with the given revision; don't
        run any migrations."""
        script = self.context.script
        def do_stamp(rev, context):
            if context.as_sql:
                current = False
            else:
                current = context._current_rev()
            dest = script.get_revision(revision)
            if dest is not None:
                dest = dest.revision
            context._update_current_rev(current, dest)
            return []
        
        context_opts = self.context.context_opts.copy()
        context_opts.update(dict(
            script=script,
            fn=do_stamp,
        ))
        stamp_context = EnvironmentContext(self.context.config, **context_opts)
        with stamp_context:
            script.run_env()
    # --------------------------------------------------------------------------

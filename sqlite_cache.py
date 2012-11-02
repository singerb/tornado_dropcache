"""
========
sqlite_cache.py
========

Cache implementation using the Python sqlite3 bindings.

Dependencies
============

Python (tested on 2.7.1).

Classes
=======

SqliteCache (sqlite_cache.py)
    A Cache implementation that uses the sqlite3 package and bindings.

Contributing
============

If you use and like this, please let me know! Patches, pull requests, suggestions etc. are all
gratefully accepted.

License
=======

Copyright 2012 Benedict Singer

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import sqlite3
import json
import datetime

from cache import Cache

class SqliteCache(Cache):
    """A Cache implementation that uses the sqlite3 package and bindings."""

    def __init__(self, folder_name, timeout=datetime.timedelta(seconds=60), cache_file_name='cache.db'):
        """Construct an SqliteCache.

        folder_name - the Dropbox folder name this app is using; can be empty for sandbox access
        timeout - timeout of cache items; default 30 seconds
        cache_file_name - filename of the sqlite database; default 'cache.db'

        """
        super(SqliteCache, self).__init__(folder_name, timeout)

        sqlite3.register_converter("json", self._convert_json)

        self._conn = sqlite3.connect(cache_file_name, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._conn.text_factory = unicode

        self._conn.execute("CREATE TABLE IF NOT EXISTS user_cache (uid text, folder_name text, folder_metadata_ts timestamp, folder_metadata json)")
        self._conn.execute("CREATE TABLE IF NOT EXISTS user_data_cache (uid text, file_name text, file_metadata json, file_metadata_ts timestamp, file_data text)")

    def _convert_json(self, j):
        return json.loads(j)

    def get_user(self, uid):
        r = self._conn.execute("SELECT * FROM user_cache WHERE uid=?", (uid,)).fetchone()
        if r:
            # TODO redo prints using logging
            print "returning existing user"
            return r
        else:
            print "making new user"
            with self._conn:
                self._conn.execute("INSERT INTO user_cache VALUES (?, ?, ?, '{}')", (uid, self.folder_name, datetime.datetime.min))
            r = self._conn.execute("SELECT * FROM user_cache WHERE uid=?", (uid,)).fetchone()
            return r

    def update_folder_metadata(self, uid, timestamp, metadata):
        with self._conn:
            self._conn.execute("UPDATE user_cache SET folder_metadata_ts = ?, folder_metadata = ? WHERE uid=?", (timestamp, metadata, uid))

    def update_folder_metadata_timestamp(self, uid, timestamp):
        with self._conn:
            self._conn.execute("UPDATE user_cache SET folder_metadata_ts = ? WHERE uid=?", (timestamp, uid))

    def get_file(self, uid, file_name):
        r = self._conn.execute("SELECT * FROM user_data_cache WHERE uid=? AND file_name=?", (uid, file_name)).fetchone()
        return r

    def add_file(self, uid, file_name, timestamp, metadata, data):
        with self._conn:
            self._conn.execute("INSERT INTO user_data_cache VALUES (?, ?, ?, ?, ?)", (uid, file_name, metadata, timestamp, data))

    def update_file(self, uid, file_name, timestamp, metadata, data):
        with self._conn:
            self._conn.execute("UPDATE user_data_cache SET file_metadata = ?, file_metadata_ts = ?, file_data = ? WHERE uid=? AND file_name=?", (metadata, timestamp, data, uid, file_name))

    def update_file_timestamp(self, uid, file_name, timestamp):
        with self._conn:
            self._conn.execute("UPDATE user_data_cache SET file_metadata_ts = ? WHERE uid=? AND file_name=?", (timestamp, uid, file_name))

    def remove_file(self, uid, file_name):
        with self._conn:
            self._conn.execute("DELETE FROM user_data_cache WHERE uid=? AND file_name=?", (uid, file_name))

    def clear_cache(self):
        with self._conn:
            self._conn.execute("DELETE FROM user_data_cache")
            self._conn.execute("DELETE FROM user_cache")

    def remove_user(self, uid):
        with self._conn:
            self._conn.execute("DELETE FROM user_cache WHERE uid=?", (uid,))
            self._conn.execute("DELETE FROM user_data_cache WHERE uid=?", (uid,))

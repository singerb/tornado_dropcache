"""
========
cache.py
========

Cache system for apps managing files in a Dropbox folder; allows higher level clients to easily
follow Dropbox best practices.

Dependencies
============

Python (tested on 2.7.1).

Cache implementations other than the basic ones here may have additional dependencies for their
specific backend; see each implementation for details.

Classes
=======

The base class (using the abstract base class facility from abc) and 2 simple implementations
are contained here; more useful implementations are found seperately.

Cache
    Cache abstract base class.

EmptyCache
    Cache implementation that caches nothing; used if no cache is specified.

DictCache
    A Cache implementation that stores data in an in memory dictionary.

Other Available Implementations
===============================

Included in this module currently are the following implementations; the Async* implementations
are designed for use with the Tornado asynchronous I/O facilities.

SqliteCache (sqlite_cache.py)
    Cache using the sqlite bindings.

AsyncCouchCache
    *PENDING* Cache using CouchDB and the Corduroy bindings.

AsyncMemcachedCache
    *PENDING* Cache using memcached and TBD bindings.

Contributing
============

If you use and like this, please let me know! Patches, pull requests, suggestions etc. are all
gratefully accepted. Additional Cache implementations would also be most welcome!

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

import json
import datetime
from abc import ABCMeta, abstractmethod, abstractproperty

class Cache(object):
    """Cache abstract base class.

    All currently provided implementations derive from this, although this is
    not required in new implementations; in standard Python fashion, all you must
    do is implement these methods. In such a case, this is still useful as a list
    of required methods, and to contain documentation of all those methods.

    Implementations are provided here for an 'empty' cache, which caches nothing.

    Cache methods are documented once here, and not again in the implementations.

    """

    __metaclass__ = ABCMeta

    def __init__(self, folder_name, timeout):
        self._timeout = timeout
        self._folder_name = folder_name

    @property
    def timeout(self):
        """Timeout for cache items, a timedelta."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    @property
    def folder_name(self):
        """The folder name the app is using; can be empty. Changing it will invalidate the whole cache."""
        return self._folder_name

    @folder_name.setter
    def folder_name(self, folder_name):
        self._folder_name = folder_name
        self.clear_cache()
    
    @abstractmethod
    def get_user(self, uid):
        """Return a user dict for the given uid.

        The dict should have the following keys:
        uid - the user id
        folder_name - the Dropbox folder name this app is using; could be empty if using sandbox access
        folder_metadata_ts - the timestamp of the last retrieval of the metadata for the folder, as a datetime object
        folder_metadata - the metadata for this folder, as a JSON dict

        This implementation returns a simple dict with a timestamp such that the metadata is always re-retrieved.
        
        """
        return { "uid" : uid, "folder_name" : self._folder_name, "folder_metadata_ts" : datetime.datetime.min, "folder_metadata" : None }

    @abstractmethod
    def update_folder_metadata(self, uid, timestamp, metadata):
        """Update the metadata and timestamp of the app folder.
        
        uid - the user id
        timestamp - the timestamp of the retrieval of this metadata, as a datetime object
        metadata - the folder metadata, as a JSON string

        """
        return

    @abstractmethod
    def update_folder_metadata_timestamp(self, uid, timestamp):
        """Update the timestamp of the app folder; used if the metadata has not changed.

        uid - the user id
        timestamp - the timestamp of the retrieval of this metadata, as a datetime object

        """
        return

    @abstractmethod
    def get_file(self, uid, file_name):
        """Return a file dict for the given filename, or None if not cached yet.

        The dict should have the following keys:
        uid - the user id
        file_name - the filename
        file_metadata - the file metadata, as a JSON dict
        file_metadata_ts - the timestamp of the last retrieval for the file/metadata, as a datetime object
        file_data - the contents of the file

        This implementation returns None, as it never caches any files.

        """
        return None

    @abstractmethod
    def add_file(self, uid, file_name, timestamp, metadata, data):
        """Add a file to the cache.

        uid - the user id
        file_name - the filename
        timestamp - when the file was retrieved, as a datetime object
        metadata - the file metadata, as a JSON string
        data - the file contents

        """
        return

    @abstractmethod
    def update_file(self, uid, file_name, timestamp, metadata, data):
        """Update a file in the cache.

        uid - the user id
        file_name - the filename
        timestamp - when the file was retrieved, as a datetime object
        metadata - the file metadata, as a JSON string
        data - the file contents

        """
        return

    @abstractmethod
    def update_file_timestamp(self, uid, file_name, timestamp):
        """Update a file's timestamp in the cache; used if it hasn't changed.

        uid - the user id
        file_name - the filename
        timestamp - when the file was retrieved, as a datetime object

        """
        return

    @abstractmethod
    def remove_file(self, uid, file_name):
        """Remove a file from the cache.

        uid - the user id
        file_name - the filename

        """
        return

    @abstractmethod
    def clear_cache(self):
        """Clears all cache entries, both users/folders and items."""
        return

    @abstractmethod
    def remove_user(self, uid):
        """Removes all references to a user from the cache, ie when they log out."""
        return

class EmptyCache(Cache):
    """Cache implementation that caches nothing; used if no cache is specified."""

    def __init__(self, folder_name):
        """Construct an EmptyCache with a folder name; timeout is fixed at 0 seconds.

        The folder name is the path to this app's files, and could be the empty string
        if sandbox access is used.

        """
        super(EmptyCache, self).__init__(folder_name, datetime.timedelta(seconds=0))

    def get_user(self, uid):
        return super(EmptyCache, self).get_user(uid)

    def update_folder_metadata(self, uid, timestamp, metadata):
        super(EmptyCache, self).update_folder_metadata(uid, timestamp, metadata)

    def update_folder_metadata_timestamp(self, uid, timestamp):
        super(EmptyCache, self).update_folder_metadata_timestamp(uid, timestamp)

    def get_file(self, uid, file_name):
        return super(EmptyCache, self).get_file(uid, file_name)

    def add_file(self, uid, file_name, timestamp, metadata, data):
        super(EmptyCache, self).add_file(uid, file_name, timestamp, metadata, data)

    def update_file(self, uid, file_name, timestamp, metadata, data):
        super(EmptyCache, self).update_file(uid, file_name, timestamp, metadata, data)

    def update_file_timestamp(self, uid, file_name, timestamp):
        super(EmptyCache, self).update_file_timestamp(uid, file_name, timestamp)

    def remove_file(self, uid, file_name):
        super(EmptyCache, self).remove_file(uid, file_name)

    def clear_cache(self):
        super(EmptyCache, self).clear_cache()

    def remove_user(self, uid):
        super(EmptyCache, self).remove_user(uid)

class DictCache(Cache):
    """A Cache implementation that stores data in an in memory dictionary."""

    def __init__(self, folder_name, timeout=datetime.timedelta(seconds=30)):
        """Construct a DictCache with a folder name.

        The folder name is the path to this app's files, and could be the empty string
        if sandbox access is used.

        """
        super(DictCache, self).__init__(folder_name, timeout)

        self._user_dict = dict()
        self._data_dict = dict()

    def _key(self, uid, file_name):
        return "%s %s" % (uid, file_name)

    def get_user(self, uid):
        if uid not in self._user_dict:
            user_dict = {
                    'uid' : uid,
                    'folder_name' : self.folder_name,
                    'folder_metadata_ts' : datetime.datetime.min,
                    'folder_metadata' : dict(),
                    }
            self._user_dict[uid] = user_dict
        return self._user_dict[uid]

    def update_folder_metadata(self, uid, timestamp, metadata):
        if uid not in self._user_dict:
            return
        self._user_dict[uid]['folder_metadata_ts'] = timestamp
        self._user_dict[uid]['folder_metadata'] = json.loads(metadata)

    def update_folder_metadata_timestamp(self, uid, timestamp):
        if uid not in self._user_dict:
            return
        self._user_dict[uid]['folder_metadata_ts'] = timestamp

    def get_file(self, uid, file_name):
        if self._key(uid, file_name) not in self._data_dict:
            return None
        else:
            return self._data_dict[self._key(uid, file_name)]

    def add_file(self, uid, file_name, timestamp, metadata, data):
        file_dict = {
                'uid' : uid,
                'file_name' : file_name,
                'file_metadata' : json.loads(metadata),
                'file_metadata_ts' : timestamp,
                'file_data' : data,
                }
        self._data_dict[self._key(uid, file_name)] = file_dict

    def update_file(self, uid, file_name, timestamp, metadata, data):
        if self._key(uid, file_name) not in self._data_dict:
            return
        self._data_dict[self._key(uid, file_name)]['timestamp'] = timestamp
        self._data_dict[self._key(uid, file_name)]['metadata'] = json.loads(metadata)
        self._data_dict[self._key(uid, file_name)]['data'] = data

    def update_file_timestamp(self, uid, file_name, timestamp):
        if self._key(uid, file_name) not in self._data_dict:
            return
        self._data_dict[self._key(uid, file_name)]['timestamp'] = timestamp

    def remove_file(self, uid, file_name):
        if self._key(uid, file_name) not in self._data_dict:
            return
        del self._data_dict[self._key(uid, file_name)]

    def clear_cache(self):
        self._user_dict = dict()
        self._data_dict = dict()

    def remove_user(self, uid):
        del self._user_dict[uid]
        to_delete = [key for key in self._data_dict.iterkeys() if key.startswith("%s " % (uid))]
        for key in to_delete:
            del self._data_dict[key]

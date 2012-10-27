"""
========
mixin.py
========

Classes to provide high level Dropbox access, built on top of async_dropbox and Cache.

Dependencies
============

Python (tested on 2.7.1), tornado, and async_dropbox (a copy is provided).

Classes
=======

DropboxUserHandler
    Mixin on top of async_dropbox.DropboxMixin to provide nicer user access.
    Handler to provide nicer user access.
    
DropboxLoginHandler
    Handler to handle Dropbox login; redirects to / on success.

DropboxAPIMixin
    High level Dropbox API access for a single folder, built on top of
    async_dropbox.DropboxMixin, Cache, and DropboxUserMixin.

See the documentation for each class for more details and specifics on which
application settings and cookies are used.

Example Usage
=============

::
    class MainHandler(DropboxUserHandler, DropboxAPIMixin):
        @tornado.web.asynchronous
        @tornado.gen.engine
        def get(self):
            if not self.current_user:
                self.render("welcome.html")
            else:
                files = yield tornado.gen.Task(self.get_files)
                self.render("list.html", title="all files", files=files)

    class LoginHandler(DropboxLoginHandler):
        def set_application_cookies(self):
            self.set_secure_cookie("dropbox_folder_path", "<folder path>")

    class ViewHandler(DropboxUserHandler, DropboxAPIMixin):
        @tornado.web.authenticated
        @tornado.web.asynchronous
        @tornado.gen.engine
        def get(self, file_name):
            res = yield tornado.gen.Task(self.get_data, file_name)
            filedata = res[0][1]

            self.render("view.html", title=file_name, contents=filedata)

    logging.basicConfig(level=logging.DEBUG)

    cache = SqliteCache("<folder path>")

    settings = {
        "cookie_secret": "<COOKIE SECRET>",
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "login_url": "/login",
        "template_path": "templates/",
        "dropbox_consumer_key": "<KEY HERE>",
        "dropbox_consumer_secret": "<SECRET HERE>",
        "xsrf_cookies": True,
        "debug": True,
        "dropbox_cache": cache,
        "dropbox_api_type": "dropbox",
    }

    application = tornado.web.Application([
        tornado.web.URLSpec(r"/", MainHandler, name="main"),
        tornado.web.URLSpec(r"/view/([^/]+)", ViewHandler, name="view"),
        tornado.web.URLSpec(r"/login", LoginHandler, name="login"),
    ], **settings)

    if __name__ == "__main__":
        application.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

Contributing
============

If you use and like this, please let me know! Patches, pull requests, suggestions etc. are all
gratefully accepted.

License
=======

The included copy of async_dropbox.py is not subject to this license, but retains the
license, if any, applied by its creator.

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

import logging
import json
import datetime

import tornado.gen

from async_dropbox import DropboxMixin
from tornado.escape import utf8

logger = logging.getLogger(__name__)

class DropboxUserHandler(tornado.web.RequestHandler):
    """Handler to provide nicer user access.

    Uses a secure cookie called 'user', the value of which should be a JSON string
    that is returned from the Dropbox auth process; get_current_user will return
    it as a decoded dict.

    See DropboxLoginHandler for an example handler that sets this cookie correctly.

    """

    def get_current_user(self):
        logger.debug("user cookie '%s'", self.get_secure_cookie("user"))

        if self.get_secure_cookie("user"):
            return json.loads(self.get_secure_cookie("user"))
        else:
            return None

class DropboxLoginHandler(tornado.web.RequestHandler, DropboxMixin):
    """Handler to handle Dropbox login; redirects to / on success.
    
    Sets the Dropbox user JSON string into a secure cookie called 'user';
    thus works nicely with DropboxUserMixin.

    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        if self.get_argument("oauth_token", None):
            logger.debug("no oauth token, calling get_auth_user")
            user = yield tornado.gen.Task(self.get_authenticated_user)
            if not user:
                raise tornado.web.HTTPError(500, "Dropbox auth failed")
            logger.debug("got user, setting cookie and redirecting to /")
            self.set_secure_cookie("user", json.dumps(user))
            self.set_application_cookies()
            self.redirect('/')
        else:
            logger.debug("calling authorize_redirect")
            self.authorize_redirect(callback_uri=self.request.full_url())

    def set_application_cookies(self):
        """Override this to set any application level cookies that are required after login.
        
        Setting your default dropbox_folder_path here is recommended.

        """
        pass

class DropboxAPIMixin(DropboxMixin):
    """High level Dropbox API access for a single folder, built on top of async_dropbox.DropboxMixin and Cache.

    Provides listing, file retrieval, upload, move, and remove operations. All operations will
    update the cache automatically if the dropbox_folder_path cookie is detected to have changed.

    Uses keys from the settings dict as follows:
    dropbox_api_type - must be 'sandbox' or 'dropbox'; default 'sandbox'
    dropbox_cache - an object implementing methods from tornado_dropcache.Cache; default is an EmptyCache using dropbox_folder_path

    Uses secure cookies as follows:
    dropbox_folder_path - the path (relative to dropbox api type) of the folder that this app is managing; default is empty string

    """

    def _get_access_token(self):
        """Helper function to get the Dropbox access token for API calls."""

        # json turns this into unicode strings, but we need bytes for oauth signatures.
        return dict((utf8(k), utf8(v)) for (k, v) in self.current_user["access_token"].iteritems())

    def _get_setting(self, key, default_func):
        if key in self.settings:
            return self.settings[key]
        else:
            return default_func()

    def _get_api_type(self):
        return self._get_setting("dropbox_api_type", lambda: "sandbox")

    def _get_folder_path(self):
        if not self.get_secure_cookie("dropbox_folder_path"):
            return ""
        else:
            return self.get_secure_cookie("dropbox_folder_path")

    def _get_cache(self):
        return self._get_setting("dropbox_cache", lambda: EmptyCache(self._get_folder_path()))

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get_files(self, callback):
        """Retrieve a sequence of filenames in the folder under consideration.
        
        Filenames are returned with the folder path stripped off.

        callback - callback that will receive the filename sequence
        
        """

        cache = self._get_cache()
        uid = self.current_user["uid"]
        user = cache.get_user(uid)

        if datetime.datetime.now() - user["folder_metadata_ts"] > cache.timeout:
            logger.debug("making dropbox list request")
            response = None
            if "hash" in user["folder_metadata"]:
                response = yield tornado.gen.Task(self.dropbox_request,
                        "api", "/1/metadata/%s/%s" % (self._get_api_type(), self._get_folder_path()),
                        access_token=self._get_access_token(),
                        list="true", hash=user["folder_metadata"]["hash"])
            else:
                response = yield tornado.gen.Task(self.dropbox_request,
                        "api", "/1/metadata/%s/%s" % (self._get_api_type(), self._get_folder_path()),
                        access_token=self._get_access_token(),
                        list="true")

            try:
                response.rethrow()
            except tornado.httpclient.HTTPError as e:
                if e.code == 304:
                    logger.debug("using cached value after 304 response")
                    cache.update_folder_metadata_timestamp(uid, datetime.datetime.now())

                    user = cache.get_user(uid)

                    callback(self._files_from_metadata(user["folder_metadata"]))
                    return
                else:
                    raise

            metadata = json.load(response.buffer)

            cache.update_folder_metadata(uid, datetime.datetime.now(), json.dumps(metadata))

            callback(self._files_from_metadata(metadata))
        else:
            logger.debug("using cached value")
            callback(self._files_from_metadata(user["folder_metadata"]))

    def _files_from_metadata(self, metadata):
        logger.debug('metadata contents %s', (metadata["contents"]))
        return [content["path"].replace(self._get_folder_path(), "", 1).lstrip("/") for content in metadata["contents"]]

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get_data(self, file_name, callback, blank_on_404=False):
        """Retrieve the file data for a specified file.

        file_name - the file to retrieve
        callback - callback that will receive the file name and data
        blank_on_404 - return a blank file on a 404 error; use when planning to upload a new file in the next step

        """
        cache = self._get_cache()
        uid = self.current_user["uid"]

        f = cache.get_file(uid, file_name)
        if not f:
            logger.debug("retrieving file for first time")
            response = yield tornado.gen.Task(self.dropbox_request,
                    "api-content", "/1/files/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                    access_token=self._get_access_token())

            try:
                response.rethrow()
            except tornado.httpclient.HTTPError as e:
                if e.code == 404 and blank_on_404:
                    logger.debug("returning empty file from 404, expect to create it soon")
                    callback(file_name, "")
                    return
                else:
                    raise

            # grab metadata from header, insert new row into cache
            metadata = json.loads(response.headers["x-dropbox-metadata"])

            cache.add_file(uid, file_name, datetime.datetime.now(), json.dumps(metadata), response.body)

            callback(file_name, response.body)
        else:
            if datetime.datetime.now() - f["file_metadata_ts"] > cache.timeout:
                logger.debug("requesting new metadata")
                response = yield tornado.gen.Task(self.dropbox_request,
                        "api", "/1/metadata/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                        access_token=self._get_access_token(),
                        list="false")

                response.rethrow()

                # grab metadata from response, compare rev to cache metadata rev
                # do GET if rev does not match, callback to _on_updated_data
                # otherwise update metadata timestamp in cache and render from cached value
                metadata = json.load(response.buffer)

                local_rev = f["file_metadata"]["rev"]
                remote_rev = metadata["rev"]

                if local_rev == remote_rev:
                    logger.debug("new metadata has same rev, updating timestamp and rendering local data")
                    cache.update_file_timestamp(uid, file_name, datetime.datetime.now())
                    callback(file_name, f["file_data"])
                else:
                    logger.debug("retrieving updated copy of file")
                    response = yield tornado.gen.Task(self.dropbox_request,
                            "api-content", "/1/files/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                            access_token=self._get_access_token())

                    response.rethrow()

                    # grab metadata from header, update cache
                    metadata = json.loads(response.headers["x-dropbox-metadata"])

                    cache.update_file(uid, file_name, datetime.datetime.now(), json.dumps(metadata), response.body)

                    callback(file_name, response.body)
            else:
                logger.debug("under timeout, using old data")
                callback(file_name, f["file_data"])

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def upload_data(self, file_name, data, callback):
        """Upload new data to the specified file, creating it if it does not exist.

        file_name - the filename to upload to
        data - the new file data
        callback - callback that will receive the filename

        """
        cache = self._get_cache()
        uid = self.current_user["uid"]

        f = cache.get_file(uid, file_name)

        logger.debug("uploading new %s file: '%s'", (file_name, data))
        if f:
            logger.debug("previous rev:")
            logger.debug(f["file_metadata"]["rev"])

        response = None
        if f:
            response = yield tornado.gen.Task(self.dropbox_request,
                    "api-content", "/1/files_put/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                    access_token=self._get_access_token(),
                    put_body=data, parent_rev=f["file_metadata"]["rev"])
        else:
            response = yield tornado.gen.Task(self.dropbox_request,
                    "api-content", "/1/files_put/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                    access_token=self._get_access_token(),
                    put_body=data)

        response.rethrow()

        if not f:
            response = yield tornado.gen.Task(self.dropbox_request,
                    "api-content", "/1/files/%s/%s/%s" % (self._get_api_type(), self._get_folder_path(), file_name),
                    access_token=self._get_access_token())

            response.rethrow()

            # grab metadata from header, insert new row into cache
            metadata = json.loads(response.headers["x-dropbox-metadata"])

            cache.add_file(uid, file_name, datetime.datetime.now(), json.dumps(metadata), response.body)
            cache.update_folder_metadata_timestamp(uid, datetime.datetime.min)
        else:
            cache.update_file_timestamp(uid, file_name, datetime.datetime.min)

        callback(file_name)

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def move_file(self, file_name, new_file_name, callback):
        """Move a file within the folder.

        file_name - file to move
        new_file_name - new filename
        callback - will be called when complete

        """
        cache = self._get_cache()
        uid = self.current_user["uid"]

        logger.debug("moving %s to %s", (file_name, new_file_name))

        response = yield tornado.gen.Task(self.dropbox_request,
                "api", "/1/fileops/move",
                access_token=self._get_access_token(),
                post_args={ "root" : self._get_api_type(), "from_path" : "%s/%s" % (self._get_folder_path(), file_name), "to_path" : "%s/%s" % (self._get_folder_path(), new_file_name) })

        response.rethrow()

        # remove the old one, and just get the new one next time we request it
        cache.remove_file(uid, file_name)
        cache.update_folder_metadata_timestamp(uid, datetime.datetime.min)

        callback()

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def delete_file(self, file_name, callback):
        """Delete a file within the folder.

        file_name - file to delete
        callback - will be called when complete

        """
        cache = self._get_cache()
        uid = self.current_user["uid"]

        logger.debug("deleting %s", (file_name))

        response = yield tornado.gen.Task(self.dropbox_request,
                "api", "/1/fileops/delete",
                access_token=self._get_access_token(),
                post_args={ "root" : self._get_api_type(), "path" : "%s/%s" % (self._get_folder_path(), file_name) })

        response.rethrow()

        # remove the file, and just get a new folder list next time it's requested
        cache.remove_file(uid, file_name)
        cache.update_folder_metadata_timestamp(uid, datetime.datetime.min)

        callback()

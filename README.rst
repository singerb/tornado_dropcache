README
------

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

Usage
=====

Note that if you want to run multiple Tornado processes (in the usual nginx+Tornado manner) then
you need to use a Cache implementation that all processes can share. Currently no implementations
meet this criteria, but the planned memcached and CouchDB implementations will.

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

=======
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

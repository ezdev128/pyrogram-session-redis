Telethon Redis session
===========================

A `Pyrogram`_ session storage implementation backed by Redis.

Note: The hooks will not work until `Pyrogram`_ merge `#6b37046`_.

.. _Pyrogram: https://github.com/pyrogram/pyrogram
.. _#6b37046: https://github.com/pyrogram/pyrogram/commit/6b37046254d79274ab589d9a80ff166429e3dc67

Usage
-----
This session implementation can store multiple Sessions in the same key hive.



Installing
----------

    .. code-block:: sh

        pip3 install pyroredis


Upgrading
----------

    .. code-block:: sh

        pip3 install -U pyroredis


Quick start
-----------
    .. code-block:: python

        from pyrogram import Client
        from pyroredis import RedisSession
        import redis

        # These example values won't work. You must get your own api_id and
        # api_hash from https://my.telegram.org, under API Development.
        api_key = 12345
        api_hash = '0123456789abcdef0123456789abcdef'
        session_name = "798xxxxxxx7"

        redis_connector = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        redis_session = RedisSession(redis_connector)
        client = Client(session_name=session_name, api_key=(api_key, api_hash))
        client.load_session_hook = redis_session.load_session
        client.save_session_hook = redis_session.save_session
        client.start()


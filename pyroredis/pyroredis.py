
from pyrogram import Client
from pyrogram.client import Proxy
from pyrogram.session.auth import Auth
from pyrogram.api.types import InputPeerUser
import base64
import json
import logging
from redis import Redis, StrictRedis
import pickle
from enum import Enum
import time


class PackFunction(Enum):
    JSON = 0
    PICKLE = 1


class UnpackFunction(Enum):
    JSON = 0
    PICKLE = 1


DEFAULT_TS_STR_FORMAT = "%F %T"
DEFAULT_HIVE_PREFIX = "pyrogram:client"
DEFAULT_PACK_FUNC = PackFunction.JSON
DEFAULT_UNPACK_FUNC = UnpackFunction.JSON


class RedisSession(object):

    __log__ = logging.getLogger(__name__)

    def __init__(self, redis_connection: Redis or StrictRedis = None):
        if not redis_connection:
            raise TypeError("The given redis_connection must be a Redis or StrictRedis instance.")

        self.client: Client = None
        self.session_name: str = None
        self.dc_id: int = None
        self.auth_key: Auth = None
        self.test_mode: bool = False
        self.user_id: InputPeerUser = None
        self.proxy: dict or Proxy = None
        self.redis: Redis = redis_connection

        # module-specified props
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.hive_prefix: str = DEFAULT_HIVE_PREFIX
        self.use_indents: bool = True
        self.add_timestamps: bool = False
        self.ts_format: str = DEFAULT_TS_STR_FORMAT
        self.pack_func: PackFunction = DEFAULT_PACK_FUNC
        self.unpack_func: UnpackFunction = DEFAULT_UNPACK_FUNC
        self.sess_prefix = "{}:{}".format(self.hive_prefix, self.session_name)

    def _pack(self, o, **kwargs):
        if self.pack_func == PackFunction.JSON:
            if self.use_indents:
                kwargs["indent"] = 2
        return json.dumps(o, **kwargs) if self.pack_func == PackFunction.JSON else pickle.dumps(o, **kwargs)

    def _unpack(self, o, **kwargs):
        return json.loads(o, **kwargs) if self.unpack_func == UnpackFunction.JSON else pickle.loads(o, **kwargs)

    def _from_client(self):
        self.dc_id = self.client.dc_id
        self.user_id = self.client.user_id
        self.test_mode = self.client.test_mode
        self.proxy = self.client.proxy
        self.auth_key = self.client.auth_key

        self.session_name = self.client.session_name
        self.sess_prefix = "{}:{}".format(self.hive_prefix, self.session_name)

    def _to_client(self):
        self.client.dc_id = self.dc_id
        self.client.user_id = self.user_id
        self.client.test_mode = self.test_mode
        self.client.proxy = self.proxy
        self.client.auth_key = self.auth_key

    def _get_sessions(self, strip_prefix=False):
        key_pattern = "{}:{}:sessions:".format(self.hive_prefix, self.session_name)
        try:
            sessions = self.redis.keys(key_pattern+"*")
            return [s.decode().replace(key_pattern, "") if strip_prefix else s.decode() for s in sessions]
        except Exception as ex:
            self.log.exception(ex.args)
            return []

    def load_session(self, client: Client = None):
        assert client

        self.client = client
        self._from_client()

        try:
            s = self._get_sessions()
            if len(s) == 0:
                self.dc_id = 1
                self.auth_key = Auth(self.dc_id, self.test_mode, self.proxy).create()
                self._to_client()
                return

            s = self.redis.get(s[-1])
            assert s

            s = self._unpack(s)
            self.dc_id = s["dc_id"]
            self.test_mode = s["test_mode"]
            self.auth_key = base64.b64decode("".join(s["auth_key"]))
            self.user_id = s["user_id"]
            self._to_client()
        except Exception as ex:
            self.log.exception(ex.args)

    def save_session(self, client: Client):
        if id(client) != id(self.client):
            self.client = client

        self._from_client()

        if self.dc_id is None:
            self.log.error("client.dc_id is None. Maybe a bug! Session will not be saved!")
            return

        auth_key = base64.b64encode(self.auth_key).decode()
        auth_key = [auth_key[i: i + 43] for i in range(0, len(auth_key), 43)]

        s = {
            "dc_id": self.dc_id,
            "test_mode": self.test_mode,
            "auth_key": auth_key,
            "user_id": self.user_id,
        }

        if self.add_timestamps:
            s.update({
                "ts_ts": time.time(),
                "ts_str": time.strftime(self.ts_format, time.localtime()),
            })

        key = "{}:sessions:{}".format(self.sess_prefix, self.dc_id)
        try:
            self.redis.set(key, self._pack(s))
        except Exception as ex:
            self.log.exception(ex.args)

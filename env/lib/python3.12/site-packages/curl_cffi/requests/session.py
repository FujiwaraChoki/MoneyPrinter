import asyncio
import math
import queue
import threading
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager, suppress
from functools import partialmethod
from io import BytesIO
from json import dumps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
)
from urllib.parse import ParseResult, parse_qsl, quote, unquote, urlencode, urljoin, urlparse

from typing_extensions import Unpack

from .. import AsyncCurl, Curl, CurlError, CurlHttpVersion, CurlInfo, CurlOpt, CurlSslVersion
from ..curl import CURL_WRITEFUNC_ERROR, CurlMime
from .cookies import Cookies, CookieTypes, CurlMorsel
from .exceptions import InvalidURL, ImpersonateError, RequestException, SessionClosed, code2error
from .headers import Headers, HeaderTypes
from .impersonate import BrowserType  # noqa: F401
from .impersonate import (
    TLS_CIPHER_NAME_MAP,
    TLS_EC_CURVES_MAP,
    TLS_VERSION_MAP,
    BrowserTypeLiteral,
    ExtraFingerprints,
    ExtraFpDict,
    normalize_browser_type,
    toggle_extension,
)
from .models import Request, Response
from .websockets import ON_CLOSE_T, ON_ERROR_T, ON_MESSAGE_T, ON_OPEN_T, WebSocket

with suppress(ImportError):
    import gevent

with suppress(ImportError):
    import eventlet.tpool

if TYPE_CHECKING:

    class ProxySpec(TypedDict, total=False):
        all: str
        http: str
        https: str
        ws: str
        wss: str

    class BaseSessionParams(TypedDict, total=False):
        headers: Optional[HeaderTypes]
        cookies: Optional[CookieTypes]
        auth: Optional[Tuple[str, str]]
        proxies: Optional[ProxySpec]
        proxy: Optional[str]
        proxy_auth: Optional[Tuple[str, str]]
        base_url: Optional[str]
        params: Optional[dict]
        verify: bool
        timeout: Union[float, Tuple[float, float]]
        trust_env: bool
        allow_redirects: bool
        max_redirects: int
        impersonate: Optional[BrowserTypeLiteral]
        ja3: Optional[str]
        akamai: Optional[str]
        extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]]
        default_headers: bool
        default_encoding: Union[str, Callable[[bytes], str]]
        curl_options: Optional[dict]
        curl_infos: Optional[list]
        http_version: Optional[CurlHttpVersion]
        debug: bool
        interface: Optional[str]
        cert: Optional[Union[str, Tuple[str, str]]]

else:
    ProxySpec = Dict[str, str]
    BaseSessionParams = TypedDict

ThreadType = Literal["eventlet", "gevent"]
HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE", "PATCH"]


def _is_absolute_url(url: str) -> bool:
    """Check if the provided url is an absolute url"""
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme and parsed_url.hostname)


SAFE_CHARS = set("!#$%&'()*+,/:;=?@[]~")


def _quote_path_and_params(url: str, quote_str: str = ""):
    safe = "".join(SAFE_CHARS - set(quote_str))
    parsed_url = urlparse(url)
    parsed_get_args = parse_qsl(parsed_url.query)
    encoded_get_args = urlencode(parsed_get_args, doseq=True, safe=safe)
    return ParseResult(
        parsed_url.scheme,
        parsed_url.netloc,
        quote(parsed_url.path, safe=safe),
        parsed_url.params,
        encoded_get_args,
        parsed_url.fragment,
    ).geturl()


def _update_url_params(url: str, params: Union[Dict, List, Tuple]) -> str:
    """Add URL query params to provided URL being aware of existing.

    Parameters:
        url: string of target URL
        params: dict containing requested params to be added

    Returns:
        string with updated URL

    >> url = 'http://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> _update_url_params(url, new_params)
    'http://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting and parse
    url = unquote(url)
    parsed_url = urlparse(url)

    # Extracting URL arguments from parsed URL, NOTE the result is a list, not dict
    parsed_get_args = parse_qsl(parsed_url.query)

    # Merging URL arguments dict with new params
    old_args_counter = Counter(x[0] for x in parsed_get_args)
    if isinstance(params, dict):
        params = list(params.items())
    new_args_counter = Counter(x[0] for x in params)
    for key, value in params:
        # Bool and Dict values should be converted to json-friendly values
        if isinstance(value, (bool, dict)):
            value = dumps(value)
        # 1 to 1 mapping, we have to search and update it.
        if old_args_counter.get(key) == 1 and new_args_counter.get(key) == 1:
            parsed_get_args = [(x if x[0] != key else (key, value)) for x in parsed_get_args]
        else:
            parsed_get_args.append((key, value))

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)

    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        encoded_get_args,
        parsed_url.fragment,
    ).geturl()

    return new_url


# Adapted from: https://github.com/psf/requests/blob/1ae6fc3137a11e11565ed22436aa1e77277ac98c/src%2Frequests%2Futils.py#L633-L682
# License: Apache 2.0

# The unreserved URI characters (RFC 3986)
UNRESERVED_SET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~"
)


def unquote_unreserved(uri: str) -> str:
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri: str) -> str:
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~|"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~|"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)


# TODO: should we move this function to headers.py?
def _update_header_line(header_lines: List[str], key: str, value: str, replace: bool = False):
    """Update header line list by key value pair."""
    found = False
    for idx, line in enumerate(header_lines):
        if line.lower().startswith(key.lower() + ":"):
            found = True
            if replace:
                header_lines[idx] = f"{key}: {value}"
            break
    if not found:
        header_lines.append(f"{key}: {value}")


def _peek_queue(q: queue.Queue, default=None):
    try:
        return q.queue[0]
    except IndexError:
        return default


def _peek_aio_queue(q: asyncio.Queue, default=None):
    try:
        return q._queue[0]  # type: ignore
    except IndexError:
        return default


not_set = object()


class BaseSession:
    """Provide common methods for setting curl options and reading info in sessions."""

    def __init__(
        self,
        *,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Optional[Tuple[str, str]] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        base_url: Optional[str] = None,
        params: Optional[dict] = None,
        verify: bool = True,
        timeout: Union[float, Tuple[float, float]] = 30,
        trust_env: bool = True,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        impersonate: Optional[BrowserTypeLiteral] = None,
        ja3: Optional[str] = None,
        akamai: Optional[str] = None,
        extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]] = None,
        default_headers: bool = True,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        curl_options: Optional[dict] = None,
        curl_infos: Optional[list] = None,
        http_version: Optional[CurlHttpVersion] = None,
        debug: bool = False,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ):
        self.headers = Headers(headers)
        self.cookies = Cookies(cookies)
        self.auth = auth
        self.base_url = base_url
        self.params = params
        self.verify = verify
        self.timeout = timeout
        self.trust_env = trust_env
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects
        self.impersonate = impersonate
        self.ja3 = ja3
        self.akamai = akamai
        self.extra_fp = extra_fp
        self.default_headers = default_headers
        self.default_encoding = default_encoding
        self.curl_options = curl_options or {}
        self.curl_infos = curl_infos or []
        self.http_version = http_version
        self.debug = debug
        self.interface = interface
        self.cert = cert

        if proxy and proxies:
            raise TypeError("Cannot specify both 'proxy' and 'proxies'")
        if proxy:
            proxies = {"all": proxy}
        self.proxies: ProxySpec = proxies or {}
        self.proxy_auth = proxy_auth

        if self.base_url and not _is_absolute_url(self.base_url):
            raise ValueError("You need to provide an absolute url for 'base_url'")

        self._closed = False

    def _toggle_extensions_by_ids(self, curl, extension_ids):
        # TODO find a better representation, rather than magic numbers
        default_enabled = {0, 51, 13, 43, 65281, 23, 10, 45, 35, 11, 16}

        to_enable_ids = extension_ids - default_enabled
        for ext_id in to_enable_ids:
            toggle_extension(curl, ext_id, enable=True)

        # print("to_enable: ", to_enable_ids)

        to_disable_ids = default_enabled - extension_ids
        for ext_id in to_disable_ids:
            toggle_extension(curl, ext_id, enable=False)

        # print("to_disable: ", to_disable_ids)

    def _set_ja3_options(self, curl, ja3: str, permute: bool = False):
        """
        Detailed explanation: https://engineering.salesforce.com/tls-fingerprinting-with-ja3-and-ja3s-247362855967/
        """
        tls_version, ciphers, extensions, curves, curve_formats = ja3.split(",")

        curl_tls_version = TLS_VERSION_MAP[int(tls_version)]
        curl.setopt(CurlOpt.SSLVERSION, curl_tls_version | CurlSslVersion.MAX_DEFAULT)
        assert curl_tls_version == CurlSslVersion.TLSv1_2, "Only TLS v1.2 works for now."

        cipher_names = []
        for cipher in ciphers.split("-"):
            cipher_id = int(cipher)
            cipher_name = TLS_CIPHER_NAME_MAP[cipher_id]
            cipher_names.append(cipher_name)

        curl.setopt(CurlOpt.SSL_CIPHER_LIST, ":".join(cipher_names))

        if extensions.endswith("-21"):
            extensions = extensions[:-3]
            warnings.warn(
                "Padding(21) extension found in ja3 string, whether to add it should "
                "be managed by the SSL engine. The TLS client hello packet may contain "
                "or not contain this extension, any of which should be correct.",
                stacklevel=1,
            )
        extension_ids = set(int(e) for e in extensions.split("-"))
        self._toggle_extensions_by_ids(curl, extension_ids)

        if not permute:
            curl.setopt(CurlOpt.TLS_EXTENSION_ORDER, extensions)

        curve_names = []
        for curve in curves.split("-"):
            curve_id = int(curve)
            curve_name = TLS_EC_CURVES_MAP[curve_id]
            curve_names.append(curve_name)

        curl.setopt(CurlOpt.SSL_EC_CURVES, ":".join(curve_names))

        assert int(curve_formats) == 0, "Only curve_formats == 0 is supported."

    def _set_akamai_options(self, curl, akamai: str):
        """
        Detailed explanation: https://www.blackhat.com/docs/eu-17/materials/eu-17-Shuster-Passive-Fingerprinting-Of-HTTP2-Clients-wp.pdf
        """
        settings, window_update, streams, header_order = akamai.split("|")

        # For compatiblity with tls.peet.ws
        settings = settings.replace(",", ";")

        curl.setopt(CurlOpt.HTTP_VERSION, CurlHttpVersion.V2_0)

        curl.setopt(CurlOpt.HTTP2_SETTINGS, settings)
        curl.setopt(CurlOpt.HTTP2_WINDOW_UPDATE, int(window_update))

        if streams != "0":
            curl.setopt(CurlOpt.HTTP2_STREAMS, streams)

        # m,a,s,p -> masp
        # curl-impersonate only accepts masp format, without commas.
        curl.setopt(CurlOpt.HTTP2_PSEUDO_HEADERS_ORDER, header_order.replace(",", ""))

    def _set_extra_fp(self, curl, fp: ExtraFingerprints):
        if fp.tls_signature_algorithms:
            curl.setopt(CurlOpt.SSL_SIG_HASH_ALGS, ",".join(fp.tls_signature_algorithms))

        curl.setopt(CurlOpt.SSLVERSION, fp.tls_min_version | CurlSslVersion.MAX_DEFAULT)
        curl.setopt(CurlOpt.TLS_GREASE, int(fp.tls_grease))
        curl.setopt(CurlOpt.SSL_PERMUTE_EXTENSIONS, int(fp.tls_permute_extensions))
        curl.setopt(CurlOpt.SSL_CERT_COMPRESSION, fp.tls_cert_compression)
        curl.setopt(CurlOpt.STREAM_WEIGHT, fp.http2_stream_weight)
        curl.setopt(CurlOpt.STREAM_EXCLUSIVE, fp.http2_stream_exclusive)

    def _set_curl_options(
        self,
        curl,
        method: HttpMethod,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[Union[bool, str]] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br, zstd",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[BrowserTypeLiteral] = None,
        ja3: Optional[str] = None,
        akamai: Optional[str] = None,
        extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]] = None,
        default_headers: Optional[bool] = None,
        quote: Union[str, Literal[False]] = "",
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
        queue_class: Any = None,
        event_class: Any = None,
    ):
        c = curl

        method = method.upper()  # type: ignore

        # method
        if method == "POST":
            c.setopt(CurlOpt.POST, 1)
        elif method != "GET":
            c.setopt(CurlOpt.CUSTOMREQUEST, method.encode())
        if method == "HEAD":
            c.setopt(CurlOpt.NOBODY, 1)

        # url
        if self.params:
            url = _update_url_params(url, self.params)
        if params:
            url = _update_url_params(url, params)
        if self.base_url:
            url = urljoin(self.base_url, url)
        if quote:
            url = _quote_path_and_params(url, quote_str=quote)
        if quote is not False:
            url = requote_uri(url)
        c.setopt(CurlOpt.URL, url.encode())

        # data/body/json
        if isinstance(data, (dict, list, tuple)):
            body = urlencode(data).encode()
        elif isinstance(data, str):
            body = data.encode()
        elif isinstance(data, BytesIO):
            body = data.read()
        elif isinstance(data, bytes):
            body = data
        elif data is None:
            body = b""
        else:
            raise TypeError("data must be dict/list/tuple, str, BytesIO or bytes")
        if json is not None:
            body = dumps(json, separators=(",", ":")).encode()

        # Tell libcurl to be aware of bodies and related headers when,
        # 1. POST/PUT/PATCH, even if the body is empty, it's up to curl to decide what to do;
        # 2. GET/DELETE with body, although it's against the RFC, some applications.
        #   e.g. Elasticsearch, use this.
        if body or method in ("POST", "PUT", "PATCH"):
            c.setopt(CurlOpt.POSTFIELDS, body)
            # necessary if body contains '\0'
            c.setopt(CurlOpt.POSTFIELDSIZE, len(body))
            if method == "GET":
                c.setopt(CurlOpt.CUSTOMREQUEST, method)

        # headers
        h = Headers(self.headers)
        h.update(headers)

        # remove Host header if it's unnecessary, otherwise curl may get confused.
        # Host header will be automatically added by curl if it's not present.
        # https://github.com/lexiforest/curl_cffi/issues/119
        host_header = h.get("Host")
        if host_header is not None:
            u = urlparse(url)
            if host_header == u.netloc or host_header == u.hostname:
                h.pop("Host", None)

        # Make curl always include empty headers.
        # See: https://stackoverflow.com/a/32911474/1061155
        header_lines = []
        for k, v in h.multi_items():
            header_lines.append(f"{k}: {v}" if v else f"{k};")

        # Add content-type if missing
        if json is not None:
            _update_header_line(header_lines, "Content-Type", "application/json", replace=True)
        if isinstance(data, dict) and method != "POST":
            _update_header_line(header_lines, "Content-Type", "application/x-www-form-urlencoded")
        if isinstance(data, (str, bytes)):
            _update_header_line(header_lines, "Content-Type", "application/octet-stream")

        # Never send `Expect` header.
        _update_header_line(header_lines, "Expect", "", replace=True)

        c.setopt(CurlOpt.HTTPHEADER, [h.encode() for h in header_lines])

        req = Request(url, h, method)

        # cookies
        c.setopt(CurlOpt.COOKIEFILE, b"")  # always enable the curl cookie engine first
        c.setopt(CurlOpt.COOKIELIST, "ALL")  # remove all the old cookies first.

        for morsel in self.cookies.get_cookies_for_curl(req):
            # print("Setting", morsel.to_curl_format())
            curl.setopt(CurlOpt.COOKIELIST, morsel.to_curl_format())
        if cookies:
            temp_cookies = Cookies(cookies)
            for morsel in temp_cookies.get_cookies_for_curl(req):
                curl.setopt(CurlOpt.COOKIELIST, morsel.to_curl_format())

        # files
        if files:
            raise NotImplementedError(
                "files is not supported, use `multipart`. See examples here: "
                "https://github.com/lexiforest/curl_cffi/blob/main/examples/upload.py"
            )

        # multipart
        if multipart:
            # multipart will overrides postfields
            for k, v in cast(dict, data or {}).items():
                multipart.addpart(name=k, data=v.encode() if isinstance(v, str) else v)
            c.setopt(CurlOpt.MIMEPOST, multipart._form)

        # auth
        if self.auth or auth:
            if self.auth:
                username, password = self.auth
            if auth:
                username, password = auth
            c.setopt(CurlOpt.USERNAME, username.encode())  # pyright: ignore [reportPossiblyUnboundVariable=none]
            c.setopt(CurlOpt.PASSWORD, password.encode())  # pyright: ignore [reportPossiblyUnboundVariable=none]

        # timeout
        if timeout is not_set:
            timeout = self.timeout
        if timeout is None:
            timeout = 0  # indefinitely

        if isinstance(timeout, tuple):
            connect_timeout, read_timeout = timeout
            all_timeout = connect_timeout + read_timeout
            c.setopt(CurlOpt.CONNECTTIMEOUT_MS, int(connect_timeout * 1000))
            if not stream:
                c.setopt(CurlOpt.TIMEOUT_MS, int(all_timeout * 1000))
            else:
                # trick from: https://github.com/lexiforest/curl_cffi/issues/156
                c.setopt(CurlOpt.LOW_SPEED_LIMIT, 1)
                c.setopt(CurlOpt.LOW_SPEED_TIME, math.ceil(all_timeout))

        elif isinstance(timeout, (int, float)):
            if not stream:
                c.setopt(CurlOpt.TIMEOUT_MS, int(timeout * 1000))
            else:
                c.setopt(CurlOpt.CONNECTTIMEOUT_MS, int(timeout * 1000))
                c.setopt(CurlOpt.LOW_SPEED_LIMIT, 1)
                c.setopt(CurlOpt.LOW_SPEED_TIME, math.ceil(timeout))

        # allow_redirects
        c.setopt(
            CurlOpt.FOLLOWLOCATION,
            int(self.allow_redirects if allow_redirects is None else allow_redirects),
        )

        # max_redirects
        c.setopt(
            CurlOpt.MAXREDIRS,
            self.max_redirects if max_redirects is None else max_redirects,
        )

        # proxies
        if proxy and proxies:
            raise TypeError("Cannot specify both 'proxy' and 'proxies'")
        if proxy:
            proxies = {"all": proxy}
        if proxies is None:
            proxies = self.proxies

        if proxies:
            parts = urlparse(url)
            proxy = cast(Optional[str], proxies.get(parts.scheme, proxies.get("all")))
            if parts.hostname:
                proxy = (
                    cast(
                        Optional[str],
                        proxies.get(
                            f"{parts.scheme}://{parts.hostname}",
                            proxies.get(f"all://{parts.hostname}"),
                        ),
                    )
                    or proxy
                )

            if proxy is not None:
                c.setopt(CurlOpt.PROXY, proxy)

                if parts.scheme == "https":
                    if proxy.startswith("https://"):
                        warnings.warn(
                            "Make sure you are using https over https proxy, otherwise, "
                            "the proxy prefix should be 'http://' not 'https://', "
                            "see: https://github.com/lexiforest/curl_cffi/issues/6",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                    # For https site with http tunnel proxy, tell curl to enable tunneling
                    if not proxy.startswith("socks"):
                        c.setopt(CurlOpt.HTTPPROXYTUNNEL, 1)

                # proxy_auth
                proxy_auth = proxy_auth or self.proxy_auth
                if proxy_auth:
                    username, password = proxy_auth
                    c.setopt(CurlOpt.PROXYUSERNAME, username.encode())
                    c.setopt(CurlOpt.PROXYPASSWORD, password.encode())

        # verify
        if verify is False or not self.verify and verify is None:
            c.setopt(CurlOpt.SSL_VERIFYPEER, 0)
            c.setopt(CurlOpt.SSL_VERIFYHOST, 0)

        # cert for this single request
        if isinstance(verify, str):
            c.setopt(CurlOpt.CAINFO, verify)

        # cert for the session
        if verify in (None, True) and isinstance(self.verify, str):
            c.setopt(CurlOpt.CAINFO, self.verify)

        # referer
        if referer:
            c.setopt(CurlOpt.REFERER, referer.encode())

        # accept_encoding
        if accept_encoding is not None:
            c.setopt(CurlOpt.ACCEPT_ENCODING, accept_encoding.encode())

        # cert
        cert = cert or self.cert
        if cert:
            if isinstance(cert, str):
                c.setopt(CurlOpt.SSLCERT, cert)
            else:
                cert, key = cert
                c.setopt(CurlOpt.SSLCERT, cert)
                c.setopt(CurlOpt.SSLKEY, key)

        # impersonate
        impersonate = impersonate or self.impersonate
        default_headers = self.default_headers if default_headers is None else default_headers
        if impersonate:
            impersonate = normalize_browser_type(impersonate)
            ret = c.impersonate(impersonate, default_headers=default_headers)
            if ret != 0:
                raise ImpersonateError(f"Impersonating {impersonate} is not supported")

        # ja3 string
        ja3 = ja3 or self.ja3
        if ja3:
            if impersonate:
                warnings.warn("JA3 was altered after browser version was set.", stacklevel=1)
            permute = False
            if isinstance(extra_fp, ExtraFingerprints) and extra_fp.tls_permute_extensions:
                permute = True
            if isinstance(extra_fp, dict) and extra_fp.get("tls_permute_extensions"):
                permute = True
            self._set_ja3_options(c, ja3, permute=permute)

        # akamai string
        akamai = akamai or self.akamai
        if akamai:
            if impersonate:
                warnings.warn("Akamai was altered after browser version was set.", stacklevel=1)
            self._set_akamai_options(c, akamai)

        # extra_fp options
        extra_fp = extra_fp or self.extra_fp
        if extra_fp:
            if isinstance(extra_fp, dict):
                extra_fp = ExtraFingerprints(**extra_fp)
            if impersonate:
                warnings.warn(
                    "Extra fingerprints was altered after browser version was set.",
                    stacklevel=1,
                )
            self._set_extra_fp(c, extra_fp)

        # http_version, after impersonate, which will change this to http2
        http_version = http_version or self.http_version
        if http_version:
            c.setopt(CurlOpt.HTTP_VERSION, http_version)

        # set extra curl options, must come after impersonate, because it will alter some options
        for k, v in self.curl_options.items():
            c.setopt(k, v)

        buffer = None
        q = None
        header_recved = None
        quit_now = None
        if stream:
            q = queue_class()
            header_recved = event_class()
            quit_now = event_class()

            def qput(chunk):
                if not header_recved.is_set():
                    header_recved.set()
                if quit_now.is_set():
                    return CURL_WRITEFUNC_ERROR
                q.put_nowait(chunk)
                return len(chunk)

            c.setopt(CurlOpt.WRITEFUNCTION, qput)
        elif content_callback is not None:
            c.setopt(CurlOpt.WRITEFUNCTION, content_callback)
        else:
            buffer = BytesIO()
            c.setopt(CurlOpt.WRITEDATA, buffer)
        header_buffer = BytesIO()
        c.setopt(CurlOpt.HEADERDATA, header_buffer)

        # interface
        interface = interface or self.interface
        if interface:
            c.setopt(CurlOpt.INTERFACE, interface.encode())

        # max_recv_speed
        # do not check, since 0 is a valid value to disable it
        c.setopt(CurlOpt.MAX_RECV_SPEED_LARGE, max_recv_speed)

        return req, buffer, header_buffer, q, header_recved, quit_now

    def _parse_response(self, curl, buffer, header_buffer, default_encoding):
        c = curl
        rsp = Response(c)
        rsp.url = cast(bytes, c.getinfo(CurlInfo.EFFECTIVE_URL)).decode()
        if buffer:
            rsp.content = buffer.getvalue()
        rsp.http_version = cast(int, c.getinfo(CurlInfo.HTTP_VERSION))
        rsp.status_code = cast(int, c.getinfo(CurlInfo.RESPONSE_CODE))
        rsp.ok = 200 <= rsp.status_code < 400
        header_lines = header_buffer.getvalue().splitlines()

        # TODO history urls
        header_list = []
        for header_line in header_lines:
            if not header_line.strip():
                continue
            if header_line.startswith(b"HTTP/"):
                # read header from last response
                rsp.reason = c.get_reason_phrase(header_line).decode()
                # empty header list for new redirected response
                header_list = []
                continue
            if header_line.startswith(b" ") or header_line.startswith(b"\t"):
                header_list[-1] += header_line
                continue
            header_list.append(header_line)
        rsp.headers = Headers(header_list)
        # print("Set-cookie", rsp.headers["set-cookie"])
        morsels = [CurlMorsel.from_curl_format(c) for c in c.getinfo(CurlInfo.COOKIELIST)]
        # for l in c.getinfo(CurlInfo.COOKIELIST):
        #     print("Curl Cookies", l.decode())
        self.cookies.update_cookies_from_curl(morsels)
        rsp.cookies = self.cookies
        # print("Cookies after extraction", self.cookies)
        rsp.primary_ip = cast(bytes, c.getinfo(CurlInfo.PRIMARY_IP)).decode()
        rsp.local_ip = cast(bytes, c.getinfo(CurlInfo.LOCAL_IP)).decode()
        rsp.default_encoding = default_encoding
        rsp.elapsed = cast(float, c.getinfo(CurlInfo.TOTAL_TIME))
        rsp.redirect_count = cast(int, c.getinfo(CurlInfo.REDIRECT_COUNT))
        rsp.redirect_url = cast(bytes, c.getinfo(CurlInfo.REDIRECT_URL)).decode()

        for info in self.curl_infos:
            rsp.infos[info] = c.getinfo(info)

        return rsp

    def _check_session_closed(self):
        if self._closed:
            raise SessionClosed("Session is closed, cannot send request.")


class Session(BaseSession):
    """A request session, cookies and connections will be reused. This object is thread-safe,
    but it's recommended to use a seperate session for each thread."""

    def __init__(
        self,
        curl: Optional[Curl] = None,
        thread: Optional[ThreadType] = None,
        use_thread_local_curl: bool = True,
        **kwargs: Unpack[BaseSessionParams],
    ):
        """
        Parameters set in the init method will be override by the same parameter in request method.

        Args:
            curl: curl object to use in the session. If not provided, a new one will be
                created. Also, a fresh curl object will always be created when accessed
                from another thread.
            thread: thread engine to use for working with other thread implementations.
                choices: eventlet, gevent.
            headers: headers to use in the session.
            cookies: cookies to add in the session.
            auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
            proxies: dict of proxies to use, format: {"http": proxy_url, "https": proxy_url}.
            proxy: proxy to use, format: "http://proxy_url".
                Cannot be used with the above parameter.
            proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
            base_url: absolute url to use as base for relative urls.
            params: query string for the session.
            verify: whether to verify https certs.
            timeout: how many seconds to wait before giving up.
            trust_env: use http_proxy/https_proxy and other environments, default True.
            allow_redirects: whether to allow redirection.
            max_redirects: max redirect counts, default 30, use -1 for unlimited.
            impersonate: which browser version to impersonate in the session.
            ja3: ja3 string to impersonate in the session.
            akamai: akamai string to impersonate in the session.
            extra_fp: extra fingerprints options, in complement to ja3 and akamai strings.
            interface: which interface use.
            default_encoding: encoding for decoding response content if charset is not found in
                headers. Defaults to "utf-8". Can be set to a callable for automatic detection.
            cert: a tuple of (cert, key) filenames for client cert.

        Notes:
            This class can be used as a context manager.

        .. code-block:: python

            from curl_cffi.requests import Session

            with Session() as s:
                r = s.get("https://example.com")
        """
        super().__init__(**kwargs)
        self._thread = thread
        self._use_thread_local_curl = use_thread_local_curl
        self._queue = None
        self._executor = None
        if use_thread_local_curl:
            self._local = threading.local()
            if curl:
                self._is_customized_curl = True
                self._local.curl = curl
            else:
                self._is_customized_curl = False
                self._local.curl = Curl(debug=self.debug)
        else:
            self._curl = curl if curl else Curl(debug=self.debug)

    @property
    def curl(self):
        if self._use_thread_local_curl:
            if self._is_customized_curl:
                warnings.warn("Creating fresh curl handle in different thread.", stacklevel=2)
            if not getattr(self._local, "curl", None):
                self._local.curl = Curl(debug=self.debug)
            return self._local.curl
        else:
            return self._curl

    @property
    def executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor()
        return self._executor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        """Close the session."""
        self._closed = True
        self.curl.close()

    @contextmanager
    def stream(self, *args, **kwargs):
        """Equivalent to ``with request(..., stream=True) as r:``"""
        rsp = self.request(*args, **kwargs, stream=True)
        try:
            yield rsp
        finally:
            rsp.close()

    def ws_connect(
        self,
        url,
        *args,
        on_message: Optional[ON_MESSAGE_T] = None,
        on_error: Optional[ON_ERROR_T] = None,
        on_open: Optional[ON_OPEN_T] = None,
        on_close: Optional[ON_CLOSE_T] = None,
        **kwargs,
    ) -> WebSocket:
        """Connects to a websocket url.

        Args:
            url: the ws url to connect.
            on_message: message callback, ``def on_message(ws, str)``
            on_error: error callback, ``def on_error(ws, error)``
            on_open: open callback, ``def on_open(ws)``
            on_close: close callback, ``def on_close(ws)``

        Other parameters are the same as ``.request``

        Returns:
            a ws instance to communicate with the server.
        """
        self._check_session_closed()

        self._set_curl_options(self.curl, "GET", url, *args, **kwargs)

        # https://curl.se/docs/websocket.html
        self.curl.setopt(CurlOpt.CONNECT_ONLY, 2)
        self.curl.perform()

        return WebSocket(
            self,
            self.curl,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close,
        )

    def request(
        self,
        method: HttpMethod,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[bool] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[BrowserTypeLiteral] = None,
        ja3: Optional[str] = None,
        akamai: Optional[str] = None,
        extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]] = None,
        default_headers: Optional[bool] = None,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        quote: Union[str, Literal[False]] = "",
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
    ) -> Response:
        """Send the request, see ``requests.request`` for details on parameters."""

        self._check_session_closed()

        # clone a new curl instance for streaming response
        if stream:
            c = self.curl.duphandle()
            self.curl.reset()
        else:
            c = self.curl

        req, buffer, header_buffer, q, header_recved, quit_now = self._set_curl_options(
            c,
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            proxies=proxies,
            proxy=proxy,
            proxy_auth=proxy_auth,
            verify=verify,
            referer=referer,
            accept_encoding=accept_encoding,
            content_callback=content_callback,
            impersonate=impersonate,
            ja3=ja3,
            akamai=akamai,
            extra_fp=extra_fp,
            default_headers=default_headers,
            quote=quote,
            http_version=http_version,
            interface=interface,
            stream=stream,
            max_recv_speed=max_recv_speed,
            multipart=multipart,
            cert=cert,
            queue_class=queue.Queue,
            event_class=threading.Event,
        )

        if stream:
            header_parsed = threading.Event()

            def perform():
                try:
                    c.perform()
                except CurlError as e:
                    rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                    rsp.request = req
                    cast(queue.Queue, q).put_nowait(RequestException(str(e), e.code, rsp))
                finally:
                    if not cast(threading.Event, header_recved).is_set():
                        cast(threading.Event, header_recved).set()
                    # None acts as a sentinel
                    cast(queue.Queue, q).put(None)

            def cleanup(fut):
                header_parsed.wait()
                c.reset()

            stream_task = self.executor.submit(perform)
            stream_task.add_done_callback(cleanup)

            # Wait for the first chunk
            cast(threading.Event, header_recved).wait()
            rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
            header_parsed.set()

            # Raise the exception if something wrong happens when receiving the header.
            first_element = _peek_queue(cast(queue.Queue, q))
            if isinstance(first_element, RequestException):
                c.reset()
                raise first_element

            rsp.request = req
            rsp.stream_task = stream_task
            rsp.quit_now = quit_now
            rsp.queue = q
            return rsp
        else:
            try:
                if self._thread == "eventlet":
                    # see: https://eventlet.net/doc/threading.html
                    eventlet.tpool.execute(c.perform)
                elif self._thread == "gevent":
                    # see: https://www.gevent.org/api/gevent.threadpool.html
                    gevent.get_hub().threadpool.spawn(c.perform).get()
                else:
                    c.perform()
            except CurlError as e:
                rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                rsp.request = req
                error = code2error(e.code, str(e))
                raise error(str(e), e.code, rsp) from e
            else:
                rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                rsp.request = req
                return rsp
            finally:
                c.reset()

    head = partialmethod(request, "HEAD")
    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    options = partialmethod(request, "OPTIONS")


class AsyncSession(BaseSession):
    """An async request session, cookies and connections will be reused."""

    def __init__(
        self,
        *,
        loop=None,
        async_curl: Optional[AsyncCurl] = None,
        max_clients: int = 10,
        **kwargs: Unpack[BaseSessionParams],
    ):
        """
        Parameters set in the init method will be override by the same parameter in request method.

        Parameters:
            loop: loop to use, if not provided, the running loop will be used.
            async_curl: [AsyncCurl](/api/curl_cffi#curl_cffi.AsyncCurl) object to use.
            max_clients: maxmium curl handle to use in the session,
                this will affect the concurrency ratio.
            headers: headers to use in the session.
            cookies: cookies to add in the session.
            auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
            proxies: dict of proxies to use, format: {"http": proxy_url, "https": proxy_url}.
            proxy: proxy to use, format: "http://proxy_url".
                Cannot be used with the above parameter.
            proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
            base_url: absolute url to use for relative urls.
            params: query string for the session.
            verify: whether to verify https certs.
            timeout: how many seconds to wait before giving up.
            trust_env: use http_proxy/https_proxy and other environments, default True.
            allow_redirects: whether to allow redirection.
            max_redirects: max redirect counts, default 30, use -1 for unlimited.
            impersonate: which browser version to impersonate in the session.
            ja3: ja3 string to impersonate in the session.
            akamai: akamai string to impersonate in the session.
            extra_fp: extra fingerprints options, in complement to ja3 and akamai strings.
            default_encoding: encoding for decoding response content if charset is not found
                in headers. Defaults to "utf-8". Can be set to a callable for automatic detection.
            cert: a tuple of (cert, key) filenames for client cert.

        Notes:
            This class can be used as a context manager, and it's recommended to use via
            ``async with``.
            However, unlike aiohttp, it is not required to use ``with``.

        .. code-block:: python

            from curl_cffi.requests import AsyncSession

            # recommended.
            async with AsyncSession() as s:
                r = await s.get("https://example.com")

            s = AsyncSession()  # it also works.
        """
        super().__init__(**kwargs)
        self._loop = loop
        self._acurl = async_curl
        self.max_clients = max_clients
        self.init_pool()

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    @property
    def acurl(self):
        if self._acurl is None:
            self._acurl = AsyncCurl(loop=self.loop)
        return self._acurl

    def init_pool(self):
        self.pool = asyncio.LifoQueue(self.max_clients)
        while True:
            try:
                self.pool.put_nowait(None)
            except asyncio.QueueFull:
                break

    async def pop_curl(self):
        curl = await self.pool.get()
        if curl is None:
            curl = Curl(debug=self.debug)
        # curl.setopt(CurlOpt.FRESH_CONNECT, 1)
        # curl.setopt(CurlOpt.FORBID_REUSE, 1)
        return curl

    def push_curl(self, curl):
        with suppress(asyncio.QueueFull):
            self.pool.put_nowait(curl)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
        return None

    async def close(self) -> None:
        """Close the session."""
        await self.acurl.close()
        self._closed = True
        while True:
            try:
                curl = self.pool.get_nowait()
                if curl:
                    curl.close()
            except asyncio.QueueEmpty:
                break

    def release_curl(self, curl):
        curl.clean_after_perform()
        if not self._closed:
            self.acurl.remove_handle(curl)
            curl.reset()
            # curl.setopt(CurlOpt.PIPEWAIT, 1)
            self.push_curl(curl)
        else:
            curl.close()

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        """Equivalent to ``async with request(..., stream=True) as r:``"""
        rsp = await self.request(*args, **kwargs, stream=True)
        try:
            yield rsp
        finally:
            await rsp.aclose()

    async def ws_connect(self, url, *args, **kwargs):
        self._check_session_closed()

        curl = await self.pop_curl()
        # curl.debug()
        self._set_curl_options(curl, "GET", url, *args, **kwargs)
        curl.setopt(CurlOpt.CONNECT_ONLY, 2)  # https://curl.se/docs/websocket.html
        await self.loop.run_in_executor(None, curl.perform)
        return WebSocket(self, curl)

    async def request(
        self,
        method: HttpMethod,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[bool] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[BrowserTypeLiteral] = None,
        ja3: Optional[str] = None,
        akamai: Optional[str] = None,
        extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]] = None,
        default_headers: Optional[bool] = None,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        quote: Union[str, Literal[False]] = "",
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
    ):
        """Send the request, see ``curl_cffi.requests.request`` for details on parameters."""
        self._check_session_closed()

        curl = await self.pop_curl()
        req, buffer, header_buffer, q, header_recved, quit_now = self._set_curl_options(
            curl=curl,
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            proxies=proxies,
            proxy=proxy,
            proxy_auth=proxy_auth,
            verify=verify,
            referer=referer,
            accept_encoding=accept_encoding,
            content_callback=content_callback,
            impersonate=impersonate,
            ja3=ja3,
            akamai=akamai,
            extra_fp=extra_fp,
            default_headers=default_headers,
            quote=quote,
            http_version=http_version,
            interface=interface,
            stream=stream,
            max_recv_speed=max_recv_speed,
            multipart=multipart,
            cert=cert,
            queue_class=asyncio.Queue,
            event_class=asyncio.Event,
        )
        if stream:
            task = self.acurl.add_handle(curl)

            async def perform():
                try:
                    await task
                except CurlError as e:
                    rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                    rsp.request = req
                    cast(asyncio.Queue, q).put_nowait(RequestException(str(e), e.code, rsp))
                finally:
                    if not cast(asyncio.Event, header_recved).is_set():
                        cast(asyncio.Event, header_recved).set()
                    # None acts as a sentinel
                    await cast(asyncio.Queue, q).put(None)

            def cleanup(fut):
                self.release_curl(curl)

            stream_task = asyncio.create_task(perform())
            stream_task.add_done_callback(cleanup)

            await cast(asyncio.Event, header_recved).wait()

            # Unlike threads, coroutines does not use preemptive scheduling.
            # For asyncio, there is no need for a header_parsed event, the
            # _parse_response will execute in the foreground, no background tasks running.
            rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)

            first_element = _peek_aio_queue(cast(asyncio.Queue, q))
            if isinstance(first_element, RequestException):
                self.release_curl(curl)
                raise first_element

            rsp.request = req
            rsp.astream_task = stream_task
            rsp.quit_now = quit_now
            rsp.queue = q
            return rsp
        else:
            try:
                # curl.debug()
                # print("using curl instance: ", curl)
                task = self.acurl.add_handle(curl)
                await task
            except CurlError as e:
                rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                rsp.request = req
                error = code2error(e.code, str(e))
                raise error(str(e), e.code, rsp) from e
            else:
                rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                rsp.request = req
                return rsp
            finally:
                self.release_curl(curl)

    head = partialmethod(request, "HEAD")
    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    options = partialmethod(request, "OPTIONS")

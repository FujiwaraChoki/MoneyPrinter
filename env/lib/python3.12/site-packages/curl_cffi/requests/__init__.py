__all__ = [
    "Session",
    "AsyncSession",
    "BrowserType",
    "BrowserTypeLiteral",
    "CurlWsFlag",
    "request",
    "head",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "RequestsError",
    "Cookies",
    "Headers",
    "Request",
    "Response",
    "WebSocket",
    "WebSocketError",
    "WsCloseCode",
    "ExtraFingerprints",
    "CookieTypes",
    "HeaderTypes",
    "ProxySpec",
]

from functools import partial
from io import BytesIO
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from ..const import CurlHttpVersion, CurlWsFlag
from ..curl import CurlMime
from .cookies import Cookies, CookieTypes
from .errors import RequestsError
from .headers import Headers, HeaderTypes
from .impersonate import BrowserType, BrowserTypeLiteral, ExtraFingerprints, ExtraFpDict
from .models import Request, Response
from .session import AsyncSession, HttpMethod, ProxySpec, Session, ThreadType
from .websockets import WebSocket, WebSocketError, WsCloseCode


def request(
    method: HttpMethod,
    url: str,
    params: Optional[Union[Dict, List, Tuple]] = None,
    data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
    json: Optional[dict] = None,
    headers: Optional[HeaderTypes] = None,
    cookies: Optional[CookieTypes] = None,
    files: Optional[Dict] = None,
    auth: Optional[Tuple[str, str]] = None,
    timeout: Union[float, Tuple[float, float]] = 30,
    allow_redirects: bool = True,
    max_redirects: int = 30,
    proxies: Optional[ProxySpec] = None,
    proxy: Optional[str] = None,
    proxy_auth: Optional[Tuple[str, str]] = None,
    verify: Optional[bool] = None,
    referer: Optional[str] = None,
    accept_encoding: Optional[str] = "gzip, deflate, br, zstd",
    content_callback: Optional[Callable] = None,
    impersonate: Optional[BrowserTypeLiteral] = None,
    ja3: Optional[str] = None,
    akamai: Optional[str] = None,
    extra_fp: Optional[Union[ExtraFingerprints, ExtraFpDict]] = None,
    thread: Optional[ThreadType] = None,
    default_headers: Optional[bool] = None,
    default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
    quote: Union[str, Literal[False]] = "",
    curl_options: Optional[dict] = None,
    http_version: Optional[CurlHttpVersion] = None,
    debug: bool = False,
    interface: Optional[str] = None,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
    stream: bool = False,
    max_recv_speed: int = 0,
    multipart: Optional[CurlMime] = None,
) -> Response:
    """Send an http request.

    Parameters:
        method: http method for the request: GET/POST/PUT/DELETE etc.
        url: url for the requests.
        params: query string for the requests.
        data: form values(dict/list/tuple) or binary data to use in body,
            ``Content-Type: application/x-www-form-urlencoded`` will be added if a dict is given.
        json: json values to use in body, `Content-Type: application/json` will be added
            automatically.
        headers: headers to send.
        cookies: cookies to use.
        files: not supported, use ``multipart`` instead.
        auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
        timeout: how many seconds to wait before giving up.
        allow_redirects: whether to allow redirection.
        max_redirects: max redirect counts, default 30, use -1 for unlimited.
        proxies: dict of proxies to use, format: ``{"http": proxy_url, "https": proxy_url}``.
        proxy: proxy to use, format: "http://user@pass:proxy_url".
            Can't be used with `proxies` parameter.
        proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
        verify: whether to verify https certs.
        referer: shortcut for setting referer header.
        accept_encoding: shortcut for setting accept-encoding header.
        content_callback: a callback function to receive response body.
            ``def callback(chunk: bytes) -> None:``
        impersonate: which browser version to impersonate.
        ja3: ja3 string to impersonate.
        akamai: akamai string to impersonate.
        extra_fp: extra fingerprints options, in complement to ja3 and akamai strings.
        thread: thread engine to use for working with other thread implementations.
            choices: eventlet, gevent.
        default_headers: whether to set default browser headers when impersonating.
        default_encoding: encoding for decoding response content if charset is not found in headers.
            Defaults to "utf-8". Can be set to a callable for automatic detection.
        quote: Set characters to be quoted, i.e. percent-encoded. Default safe string
            is ``!#$%&'()*+,/:;=?@[]~``. If set to a sting, the character will be removed
            from the safe string, thus quoted. If set to False, the url will be kept as is,
            without any automatic percent-encoding, you must encode the URL yourself.
        curl_options: extra curl options to use.
        http_version: limiting http version, defaults to http2.
        debug: print extra curl debug info.
        interface: which interface to use.
        cert: a tuple of (cert, key) filenames for client cert.
        stream: streaming the response, default False.
        max_recv_speed: maximum receive speed, bytes per second.
        multipart: upload files using the multipart format, see examples for details.

    Returns:
        A ``Response`` object.
    """
    with Session(thread=thread, curl_options=curl_options, debug=debug) as s:
        return s.request(
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
            default_encoding=default_encoding,
            quote=quote,
            http_version=http_version,
            interface=interface,
            cert=cert,
            stream=stream,
            max_recv_speed=max_recv_speed,
            multipart=multipart,
        )


head = partial(request, "HEAD")
get = partial(request, "GET")
post = partial(request, "POST")
put = partial(request, "PUT")
patch = partial(request, "PATCH")
delete = partial(request, "DELETE")
options = partial(request, "OPTIONS")

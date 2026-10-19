#!/usr/bin/env python3
"""一次性测试智增增纯文本输入；API Key 仅通过终端隐藏输入。"""

import getpass
import json
import socket
import sys
import urllib.error
import urllib.request
import warnings


URL = "https://api.zhizengzeng.com/v1/chat/completions"
class NoRedirect(urllib.request.HTTPRedirectHandler):
    """禁止重定向，确保只发送一次请求且不向其他地址转发 Key。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    if not sys.stdin.isatty():
        print("错误类型：安全输入不可用；请在 Mac 交互式终端中运行脚本。")
        return 1

    try:
        # getpass 无法隐藏输入时禁止退回明文输入。
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            api_key = getpass.getpass("请输入智增增 API Key（输入隐藏）：")
    except (getpass.GetPassWarning, EOFError):
        print("错误类型：安全输入失败；未发送请求。")
        return 1
    except KeyboardInterrupt:
        print("\n已取消，未发送请求。")
        return 1

    if not api_key or any(char.isspace() for char in api_key):
        print("错误类型：API Key 为空或包含空白字符；未发送请求。")
        return 1

    def safe_print(value):
        # 响应或异常若意外回显 Key，也不将其输出到终端。
        text = str(value)
        for secret in (api_key, json.dumps(api_key, ensure_ascii=True)[1:-1]):
            text = text.replace(secret, "[已隐藏 API Key]")
        print(text)

    payload = {
        "model": "gpt-6-luna",
        "messages": [
            {"role": "user", "content": "1+2等于多少？只回答数字。"}
        ],
        "max_completion_tokens": 1024,
        "stream": False,
    }
    request = urllib.request.Request(
        URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    # 仅本次请求直连 HTTPS；不读取或修改系统代理配置。
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )

    try:
        try:
            response = opener.open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            # HTTP 错误也保留响应头和正文，以区分 API JSON 与 nginx HTML。
            response = exc

        with response:
            status = response.code
            headers = response.headers
            safe_print("HTTP 状态码：" + str(status))
            for name in ("Content-Type", "Server", "x-request-id"):
                value = headers.get(name)
                if value is not None:
                    safe_print(name + ": " + value)
                elif name != "x-request-id":
                    safe_print(name + ": （未提供）")
            raw_body = response.read()

        charset = headers.get_content_charset() or "utf-8"
        try:
            body = raw_body.decode(charset, errors="replace")
        except LookupError:
            body = raw_body.decode("utf-8", errors="replace")

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            server = headers.get("Server", "").lower()
            if status == 400 and ("nginx" in server or "nginx" in body.lower()):
                safe_print("错误类型：nginx 400 Bad Request（非 JSON 响应）")
            else:
                safe_print("错误类型：JSON 解析错误（JSONDecodeError）")
            safe_print("JSON 解析位置：行 {}，列 {}".format(exc.lineno, exc.colno))
            safe_print("响应正文：\n" + body)
            return 1

        if not 200 <= status < 300:
            safe_print("错误类型：HTTPError（JSON 错误响应）")
            safe_print("响应正文：\n" + body)
            return 1
        if isinstance(result, dict) and "error" in result:
            safe_print("错误类型：API JSON 错误响应")
            safe_print("响应正文：\n" + body)
            return 1

        try:
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str):
                raise TypeError("模型回答不是字符串")
        except (KeyError, IndexError, TypeError):
            safe_print("错误类型：JSON 响应结构异常（未找到文本模型回答）")
            safe_print("响应正文：\n" + body)
            return 1

        safe_print("模型回答：" + answer)
        return 0
    except urllib.error.URLError as exc:
        safe_print("错误类型：URLError / " + type(exc.reason).__name__)
        safe_print("错误详情：" + str(exc.reason))
        safe_print("响应正文：不可用（未收到完整 HTTP 响应）")
        return 1
    except (TimeoutError, socket.timeout):
        safe_print("错误类型：TimeoutError（请求或响应读取超时，timeout=60 秒）")
        safe_print("响应正文：不可用（未收到完整 HTTP 响应）")
        return 1
    except Exception as exc:
        safe_print("错误类型：" + type(exc).__name__)
        safe_print("错误详情：" + str(exc))
        safe_print("响应正文：不可用（请求未完成）")
        return 1


if __name__ == "__main__":
    sys.exit(main())

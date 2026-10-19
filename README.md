# zzz-api-verified-tests：智增增 API 已验证测试

使用 Python 3 标准库，直接测试智增增 Chat Completions 接口。包含已在 Mac 上由使用者手动调用成功的两种请求方案，便于在其他电脑、网络和客户端之间做对照。

## 文件

| 文件 | 用途 |
| --- | --- |
| `test_zzz_text_api.py` | 纯文本 `1+2` 测试，最大输出 1024 Token |
| `test_zzz_api.py` | 单张本地图片复述测试，最大输出 10000 Token |

两个脚本均可独立运行，不需要安装依赖、配置环境变量或使用 CC Switch / Claude Code。不包含 API Key 或测试图片。

## 运行

在 Mac 交互式终端切换到下载或保存仓库的父目录，再进入本文件夹：

```bash
cd zzz-api-verified-tests
```

如果从 GitHub 下载到其他位置，请改成实际文件夹路径。

先测试纯文本：

```bash
python3 test_zzz_text_api.py
```

按提示输入 API Key。输入隐藏，不会显示字符；输入后按回车。预期模型回答 `3`。

再测试图片：

```bash
python3 test_zzz_api.py
```

先输入一张本地图片的路径，也可从 Finder 将图片拖入终端后按回车；再隐藏输入 API Key。脚本识别 PNG、JPEG、GIF、WebP 文件标记，并将原始文件作为 Base64 数据发送，不会将本地路径作为图片地址。具体图片限制取决于服务端。

图片提示词固定为：

> 复述这个就行了。不需要任何修饰和思考和调用工具。

这是一条文本指令；脚本没有设置额外的推理参数，也没有提供工具。

## 成功请求的配置

| 项目 | 设置 |
| --- | --- |
| 完整请求地址 | `https://api.zhizengzeng.com/v1/chat/completions` |
| 请求方法 | `POST` |
| 模型 | `gpt-6-luna` |
| 请求编码 | UTF-8 JSON |
| Content-Type | `application/json` |
| 认证头 | `Authorization: Bearer <终端隐藏输入的 Key>` |
| 流式输出 | `stream: false` |
| 超时参数 | `timeout=60` 秒 |
| 重试 | 无 |
| HTTP 重定向 | 禁止 |
| 代理 | 显式使用 `ProxyHandler({})`，不使用 urllib 的系统或环境代理 |

代理设置仅针对脚本本次连接，不修改本机环境变量、系统代理或其他配置。60 秒是 urllib 连接/阻塞读取的超时参数，不是整个进程的严格总时长上限。

纯文本请求正文：

```json
{
  "model": "gpt-6-luna",
  "messages": [
    {"role": "user", "content": "1+2等于多少？只回答数字。"}
  ],
  "max_completion_tokens": 1024,
  "stream": false
}
```

图片请求正文（Base64 内容以占位符展示，运行时由脚本生成）：

```json
{
  "model": "gpt-6-luna",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "复述这个就行了。不需要任何修饰和思考和调用工具。"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,<图片的 Base64 内容>"
          }
        }
      ]
    }
  ],
  "max_completion_tokens": 10000,
  "stream": false
}
```

`max_completion_tokens` 是输出上限，并不表示实际生成了这么多 Token。请求中不添加 `temperature`、`top_p`、`tools` 或其他可选参数。

如果其他客户端需要填写 Base URL，需核对它最终发出的完整地址是否与上表一致，避免重复拼接路径。

## 输出与错误排查

脚本打印 HTTP 状态码、`Content-Type`、`Server`、存在时的 `x-request-id`，以及模型回答。失败时打印错误类型和可用的响应正文，并区分 JSON 错误与 nginx 的非 JSON `400 Bad Request` 响应。网络错误或读取中断时可能没有完整响应正文。

- `200` 且取得模型回答：这一次接口调用成功；`Server: nginx` 本身不是错误。
- HTTP 错误且正文为 JSON：查看返回的 API 错误正文。
- `400`、非 JSON 且服务器或正文包含 nginx：脚本标记为 nginx 400，需结合正文排查。
- 超时、连接或证书错误：检查当前网络、访问策略和 Python 的 TLS 环境。

公司电脑对照方法：使用相同脚本、相同 Key 和相同图片，先文本、后图片，各手动运行一次。若脚本成功而客户端失败，比较客户端实际地址、接口格式、额外参数和代理；若脚本也失败，保留已脱敏的错误正文和请求 ID，继续排查网络或服务端问题。

## 已有成功记录

2026 年 10 月 19 日，使用者在 Mac 终端手动运行并提供结果：

| 测试 | HTTP 状态 | 响应类型 | 模型回答 |
| --- | --- | --- | --- |
| 纯文本，1024 Token 上限 | 200 | JSON | `3` |
| 图片，10000 Token 上限 | 200 | JSON | 正确复述图片中的文字 |

这记录了当时的成功结果，不保证其他网络或时间始终可用。整理文件时没有重新发送真实 API 请求。

## Key 与上传范围

- Key 只由使用者通过 `getpass` 隐藏输入；无法隐藏输入时脚本停止。
- 不自动读取已有 Key，不将 Key 写入代码、配置或日志，不输出 Authorization 请求头。
- 每次运行最多发送一次请求；是否运行由使用者决定。
- 图片会发送给智增增服务；请自行选择用于测试的图片。
- GitHub 上传范围仅为这个文件夹的脚本、说明和 `.gitignore`，不包含原工作目录的其他文件、Key 或私人图片。
- `.gitignore` 忽略常见图片、环境文件和日志；提交前仍应检查具体上传文件。

## Windows PowerShell 运行

本仓库单独保存已在 Mac 实测成功的最小测试，不包含尚未开发的批量评分系统。Windows 网络与 API 调用仍需在公司电脑上单独验证。

从 GitHub 下载 ZIP、解压后，在包含脚本的文件夹打开 PowerShell。GitHub ZIP 的文件夹名可能带有 `-main` 后缀。

先确认已有 Python：

```powershell
py --version
```

若系统没有 `py`，但已安装 Python，可改用 `python --version`，后续命令也相应改用 `python`。脚本不要求安装第三方依赖。

经使用者决定后，手动运行对应测试：

```powershell
py .\test_zzz_text_api.py
py .\test_zzz_api.py
```

以上是两个独立命令，每个脚本各发送一次请求。图片路径建议使用完整路径（例如 `C:\data\test.png`），API Key 仅在终端隐藏输入。请勿将 API Key、私人图片或公司数据提交到本仓库。

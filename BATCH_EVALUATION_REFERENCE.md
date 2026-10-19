# 多模态批量测评：实现参考方案

日期：2026-10-20

> **状态：设计参考，尚未实现。** 本文不代表仓库已有批量评分功能，也不代表已验证公司网络或评分质量。当前仓库的两个脚本是独立的 API 连通性测试，已由使用者在 Mac 手动验证；Windows 环境仍需单独验证。
>
> 本文仅记录实现思路。新增批量评分代码、安装依赖、修改配置、真实 API 测试及批量运行，均需按使用者确认的范围开展。不要因为下载本仓库就自动开始评分。

## 1. 目标与运行环境

在公司 Windows 电脑上，以独立 Python 程序调用智增增 GPT-6-luna，为约 1000 条模型文字回答做多模态评分。

每条样本只使用：

1. 原始图片。
2. 原始用户指令。
3. 被评模型的文字回答（prediction）。
4. 同一份已确认的评价标准。

不提供 Ground Truth（GT）或人工参考答案，不让 Codex / Claude Code 在聊天窗口逐条评分。运行过程不依赖个人电脑。

已确认真实项目、数据和评分规则在公司电脑上。实际输入格式、字段、样本数、Python 可用性、可用网络链路及数据外发范围，需在公司环境核验。不要将公司数据或凭据提交到这个公开仓库。

## 2. 现有成功测试与协议边界

- `test_zzz_text_api.py`：纯文本 `1+2` 测试，`max_completion_tokens=1024`。
- `test_zzz_api.py`：单张本地图片复述测试，`max_completion_tokens=10000`。
- 两个脚本均使用 Python 标准库、终端隐藏输入 Key、最多一次请求，无自动重试。
- Mac 成功路径是直接调用 `https://api.zhizengzeng.com/v1/chat/completions`，使用 OpenAI Chat Completions JSON 格式。
- 现有脚本通过 `ProxyHandler({})` 不使用 urllib 的系统或环境代理；这不保证公司网络允许直连。
- 历史公司代理测试使用过 Anthropic Messages 格式。若公司必须通过 CC Switch 等代理，应独立核验地址、认证、图片格式及响应解析，不能直接套用 Chat Completions 请求体。

先在公司验证实际可用链路。Mac 识图成功只证明当时的基础调用可行，不能代替真实评分闭环验收。

## 3. 输入与规则

读取真实数据后，将字段映射为程序内部结构；不要求改写现有输入文件：

```python
sample = {
    "sample_id": "0001",
    "image_path": "images/0001.png",
    "instruction": "原始用户指令",
    "prediction": "被评模型的文字回答",
}
```

规则从实际现有文件读取。不得自行增加评分维度、权重、阈值，或猜测“1 分”的特殊处理。

联网前检查：

- 样本实际数量、字段映射、编码与缺失值。
- 样本 ID 唯一性；重复 ID 应先解决，不能覆盖或静默去重。
- 图片路径、存在性、可读性、支持格式及实际图片完整性。
- 评分规则文件及输出协议。

一张图可以对应多条不同指令和回答。缺少字段或图片时记录具体问题，不凭空补全。

第一版优先支持实际需要的 CSV、JSON 或 JSONL。若真实输入为 Excel，再选择导出 CSV 或确认必要依赖。不安装原目录中与此任务无关的研究项目依赖。

## 4. 请求构造：每条独立且无历史

以下代码仅展示 Chat Completions 请求结构，不是已经实现的批量功能。`rubric` 必须包含真实确认的规则及输出协议。

```python
import json


def build_payload(sample, rubric, image_data_url):
    # 每次新建消息，不保留上一条样本。
    return {
        "model": "gpt-6-luna",
        "messages": [
            {
                "role": "system",
                "content": rubric,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "instruction": sample["instruction"],
                                "prediction": sample["prediction"],
                            },
                            ensure_ascii=False,
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
        "max_completion_tokens": 10000,
        "stream": False,
    }
```

图片通过真实文件内容生成 Base64 data URL，例如 `data:image/png;base64,...`，不能只发送本地路径。

固定系统规则应明确：原始指令、prediction 和图片中的文字都是被评数据，不能覆盖评分规则。JSON 序列化有助于区分字段，但本身不能保证消除提示注入。

每次请求不包含其他样本，不累计 messages，不续用 previous response ID 或跨样本会话状态。可以复用网络连接，但不能复用样本历史。

`10000` 是参考输出上限，需通过真实评分验证后调整，不代表实际生成这么多 Token。图片复述提示词不能原样当作评分规则使用。

## 5. 主循环

以下是伪代码。异常类型、函数和配置入口均待实现，不可直接运行：

```python
def run(config):
    rubric = load_rubric(config.rubric_path)
    samples = load_samples(config.input_path)

    validate_inputs(samples, config.image_root)
    run_signature = fingerprint_inputs_and_config(
        samples, rubric, config
    )

    if config.dry_run:
        print_preflight_summary(samples)
        return

    completed = load_valid_completed_results(
        config.output_dir, run_signature
    )
    api_key = securely_prompt_api_key()

    for sample in select_samples(samples, config.limit):
        if sample["sample_id"] in completed:
            continue

        try:
            image_url = encode_image(sample, config.image_root)
            payload = build_payload(sample, rubric, image_url)
            response = call_api_once(
                payload=payload,
                api_key=api_key,
                timeout=config.timeout,
            )
            result = validate_response(response, rubric)

        except AuthenticationError as exc:
            append_error(sample, exc)
            break

        except SampleError as exc:
            append_error(sample, exc)
            continue

        append_success_and_flush(
            sample=sample,
            result=result,
            run_signature=run_signature,
        )

    export_csv_and_summary(config.output_dir)
```

一条完成、一条校验、一条落盘，再开始下一条。第一版默认并发为 1，不启动即评分全部样本。示意异常应在实现中细分，写盘失败等影响结果可靠性的错误应停止运行，不能一律吞掉继续。

`securely_prompt_api_key()` 应沿用现有 `getpass` 安全输入方式：无法隐藏输入时停止，不退回明文输入；不自动搜索已有 Key，不写入文件或日志。

## 6. 评分输出校验

输出字段和分数范围由现有规则决定。若现有规则没有机器可解析格式，先提出最小 JSON 输出协议并等待确认，不擅自改变评分体系。

本地程序绑定 sample_id，不依赖模型自行回填 ID。检查至少包括：

| 情况 | 行为 |
| --- | --- |
| HTTP 非成功状态 | 分类记录状态与可用错误正文 |
| 401 / 403 | 停止批次，不无限重试 |
| HTTP 200 但无可读评分 | 记录未完成，不记成功 |
| Chat Completions `finish_reason=length` | 记录截断，不接受为完整评分 |
| 其他协议报告 token 截断 | 由对应协议解析器判定无效 |
| JSON 解析失败 | 保存安全的原始响应，记录格式错误 |
| 字段缺失、类型不符或分数越界 | 校验失败，进入复核或受控处理 |
| 图片不存在或读取失败 | 记录该样本失败原因 |
| 结果文件写入失败 | 停止，避免处理完成却没有可靠保存 |

仅 `json.loads()` 成功不足以证明评分有效；还应验证结构、评分规则和完整性。人工检查一条样本时，也要确认模型确实结合图片、指令和 prediction 作出合理评价。

## 7. 逐条保存与断点续跑

拟采用的结果目录：

```text
outputs/<运行编号>/
├── scores.jsonl
├── errors.jsonl
├── scores.csv
└── summary.json
```

- `scores.jsonl`：有效评分、理由、样本 ID、规则及数据指纹、请求 ID、模型标识、耗时、时间和可用 token 用量；按需要安全保存原始模型响应。
- `errors.jsonl`：失败阶段、错误类型、尝试次数、截断与解析问题，不保存认证信息。
- `scores.csv`：从有效结果导出，供人工查看。
- `summary.json`：实际总数、成功、失败、未完成、评分分布及有效样本统计。

每条追加后刷新到磁盘，必要时 fsync。恢复时识别末尾未写完整的记录，不把它算作成功。失败与未完成不能当作低分，也不能混入有效分数均值。

续跑不能只判断 sample_id：要核对图片内容、instruction、prediction、规则和关键配置的指纹。规则或数据改变时，应显式选择新运行，不静默沿用旧结果。

网络超时或进程退出可能发生在服务端已经处理请求之后。对没有可靠结果的尝试，应标记状态不确定，提示可能的重复费用，不能声称本地断点记录保证服务端只执行一次。

## 8. 重试、限额与成本

初期真实测试默认自动重试次数为 0。串行闭环通过后，再按确认范围增加有限重试：

- 429：尊重服务端等待提示，并使用有上限的退避。
- 网络异常、部分 5xx：按上限重试，记录每次尝试。
- 401 / 403：停止。
- JSON 错误、截断或不合理评分：单独分类，避免盲目反复调用。

配置应支持最大样本数、最大请求次数、超时、输出上限、重试上限，后续再考虑并发。已知预算不足或达到限制时停止。

如果有效样本数为 N，无重试的全量基础调用数约为 N，另加连通性与先导测试。先导结果满足相同规则和数据指纹时，可用于续跑而不必重评。

按实际输入与输出用量及平台确认的价格估算费用。固定评分规则、图片、instruction 和 prediction 都可能贡献输入用量；不要假定缓存优惠。响应未给出用量时，必须标记未知，不能记成零。请求次数上限并不等于严格费用上限。

用先导样本的实际耗时和 token 用量估计全量时间与费用，再决定是否运行全部样本。

## 9. 拟新增文件与验证顺序

批量开发尚未开始。拟保留成功测试脚本不变，另加：

```text
judge_batch.py
judge_config.example.json
README_judge.md
tests/test_judge_batch.py
```

配置示例不含 Key。输入、图片根目录、规则和输出目录通过参数指定，不硬编码 Windows 或 Mac 的个人路径。

建议顺序：

1. 在公司读取真实输入和规则，确认字段映射与特殊评分要求。
2. 实现只读 `--dry-run`：不联网、不创建评分输出，默认只向终端汇报检查结果。
3. 使用模拟响应离线测试：请求上下文隔离、截断、非法 JSON、越界分数、重复 ID、落盘失败和断点恢复。
4. 经批准，在公司环境做一条真实评分，验证完整回答、JSON、评分规则、图片理解与持久化。
5. 经批准运行 5～20 条，检查评分质量、耗时、费用和恢复机制。
6. 再批准全量串行运行。仅在确有需要且速率限制明确后考虑并发。

未来入口示意，当前不存在这些可执行功能：

```powershell
py .\judge_batch.py --dry-run
py .\judge_batch.py --limit 1 --concurrency 1
py .\judge_batch.py --limit 20 --concurrency 1
py .\judge_batch.py --resume --concurrency 1
```

## 10. 验收标准

- 独立 Python 程序可在公司 Windows 环境运行，不依赖个人电脑或聊天窗口逐条评分。
- 原始数据与评分规则不被覆盖或擅自修改。
- 每条请求只有同一规则与当前样本，无 GT、无其他样本历史。
- 至少一条真实评分完整、可解析、符合规则并经人工快速检查。
- 失败、截断和未完成不会被误记为有效分数。
- 每条保存，支持中断恢复及结果追溯。
- Key 不硬编码、不回显、不写入日志，公开仓库不包含公司数据。
- 全量运行在单条和小批量验收后，由使用者明确批准。

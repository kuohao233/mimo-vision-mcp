# mimo-vision

`mimo-vision` 是一个面向 Claude Code 的 MiMo 视觉桥接 MCP Server。它的目标是让主会话继续使用代码和推理能力更强的 MiMo Pro 文本模型，同时把读图、截图理解、OCR、多图对比等多模态任务自动交给支持视觉能力的 `mimo-v2.5` 完成。

## 为什么需要它

在 Claude Code 中接入 MiMo 系列模型时，会遇到一个明显的取舍：

- MiMo v2.5 Pro 更适合长期作为主力模型处理代码、推理和复杂任务。
- MiMo v2.5 支持多模态读图，但整体代码和推理能力不如 Pro。
- 手动用 `cc switch` 来回切换模型会打断工作流，也容易忘记切回主力模型。

`mimo-vision` 提供了一个轻量桥接层：主会话仍然挂在 MiMo Pro，遇到图片任务时，通过 MCP 工具把图片转交给 `mimo-v2.5` 分析，再把分析结果以文本形式返回给主模型继续处理。

## 效果

- **无缝**：日常对话和编码仍由 MiMo Pro 完成，图片理解在后台通过 MCP 工具完成。
- **不干扰**：Claude、GPT、Gemini 等原生多模态模型可以继续使用自身视觉能力；只有在需要桥接时才调用本 MCP 工具。
- **可扩展**：当前桥接视觉能力，后续可以用同样的 MCP 方式扩展语音、联网搜索、沙箱等能力。
- **贴近 Claude Code 工作流**：工具命名清晰，适合写进全局提示词或项目规则，让纯文本模型在遇到图片时自动选择对应工具。

## 工作原理

`server.py` 使用 `mcp.server.fastmcp.FastMCP` 暴露三个 MCP 工具：

1. 读取本地图片文件。
2. 校验图片格式和大小；超过 5MB 时自动缩放。
3. 将图片编码为 Anthropic 兼容的 `image` content block。
4. 调用 MiMo 的 Anthropic 兼容 `/v1/messages` 接口。
5. 提取返回结果中的文本内容，交还给 Claude Code 主会话。

默认视觉模型为：

```text
mimo-v2.5
```

默认接口地址为：

```text
https://token-plan-cn.xiaomimimo.com/anthropic
```

## 工具列表

### `describe_image`

单张图片理解工具，适用于截图、UI 图、设计稿、流程图、报错截图、照片等。

参数：

- `image_path`：图片路径，支持绝对路径或相对路径。
- `prompt`：具体说明你想从图中获取什么信息。为空时会返回通用描述。

适合的问题：

```text
请提取截图中的报错信息和堆栈。
请列出这个 UI 截图里的按钮、输入框、标题和布局关系。
请描述这张流程图中的节点和连线。
```

### `analyze_images`

多图联合分析工具，适用于前后对比、A/B 方案比较、多帧截图分析等。

参数：

- `image_paths`：图片路径列表。
- `prompt`：对比或综合分析要求。

适合的问题：

```text
对比这两张截图，说明 UI 有哪些变化。
判断这几张设计稿是否保持了一致的设计系统。
分析这组截图展示的操作流程。
```

### `extract_text_from_image`

纯 OCR 工具，适用于日志截图、终端截图、代码截图、错误弹窗、文档截图等。

参数：

- `image_path`：图片路径。

该工具会尽量保留换行和缩进，只输出图中文字，不做解释。

## 安装

项目只有一个核心入口文件：

```text
server.py
```

依赖主要是 Python MCP SDK。建议在虚拟环境中安装：

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Windows PowerShell 用户可以使用：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果你已经在当前目录创建过虚拟环境，只需要确保 `mcp` 包可用即可。

**注意事项：**默认的`MIMO_BASE_URL`是token plan的url，如果你是api调用需要手动换一下url

## 环境变量

### 必填

| 变量 | 说明 |
| --- | --- |
| `MIMO_API_KEY` | MiMo API Key。未设置时服务会直接启动失败。 |

### 可选

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MIMO_BASE_URL` | `https://token-plan-cn.xiaomimimo.com/anthropic` | MiMo Anthropic 兼容接口地址。 |
| `MIMO_VISION_MODEL` | `mimo-v2.5` | 实际负责读图的视觉模型。 |
| `MIMO_MAX_TOKENS` | `8192` | 单次返回的最大 token 数。 |

仓库提供了 `.env.example` 作为配置模板：

```bash
cp .env.example .env
```

请只在本地 `.env` 或 Claude Code MCP 配置中填写真实 `MIMO_API_KEY`，不要把真实密钥提交到 Git 仓库。

## 在 Claude Code 中配置

可以用 `claude mcp add` 把本地服务加入 Claude Code。

示例：

```bash
claude mcp add -s user -e MIMO_API_KEY=你的_API_KEY mimo-vision -- python /path/to/mimo-vision/server.py
```

如果想显式指定视觉模型和接口地址：

```bash
claude mcp add -s user \
  -e MIMO_API_KEY=你的_API_KEY \
  -e MIMO_VISION_MODEL=mimo-v2.5 \
  -e MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic \
  mimo-vision -- python /path/to/mimo-vision/server.py
```

配置后可以检查 MCP Server 是否已注册：

```bash
claude mcp list
```

在 Claude Code 中，工具通常会显示为：

```text
mcp__mimo-vision__describe_image
mcp__mimo-vision__analyze_images
mcp__mimo-vision__extract_text_from_image
```

## 推荐使用方式

在 MiMo Pro 这类纯文本主模型下，建议在全局或项目提示词中加入类似规则：

```text
当用户提供图片、截图、UI 图、设计稿、报错截图等内容时，不要使用 Read 工具读取图片文件。
应根据任务选择 mimo-vision MCP 工具：
- 单图理解或描述：describe_image
- 多图对比或序列分析：analyze_images
- 纯文本提取：extract_text_from_image
调用时 prompt 必须具体说明要从图中获取什么信息。
```

这样主模型可以继续专注编码和推理，把视觉理解自动外包给 `mimo-v2.5`。

## Prompt 编写建议

视觉模型的输出质量很依赖任务描述。尽量避免只写：

```text
描述这张图。
```

更推荐写成：

```text
提取截图里的完整报错信息、文件路径、行号和堆栈，并按出现顺序输出。
```

```text
识别这个登录页 UI 中所有可见文本、按钮、输入框、颜色层级和布局结构，方便后续用前端代码复现。
```

```text
对比两张截图，说明布局、颜色、文案、组件状态和交互反馈有哪些差异。
```

## 公开仓库安全注意事项

- 不要把真实 `MIMO_API_KEY` 写进 `README.md`、`server.py`、`.env.example`、提交记录或公开 issue。
- 本仓库的 `.gitignore` 会忽略 `.env` 和 `.env.*`，但保留 `.env.example` 作为配置模板。
- 如果曾经误提交真实密钥，请立即撤销或轮换该密钥；只从最新提交中删除并不等于清除了 Git 历史。
- 发布前建议检查 `git status` 和 `git diff --cached`，确认没有把虚拟环境、缓存文件或本地配置加入提交。

## 支持的图片格式与限制

支持格式：

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.gif`

限制：

- 单张图片最大 5MB，超过时自动缩放（渐进式：缩尺寸 → 降 JPEG 质量 → 兜底砍半），统一输出 JPEG。
- 当前服务读取的是本地文件路径，不负责下载远程图片。

## 常见问题

### 启动时报 `MIMO_API_KEY environment variable is required`

说明没有设置 `MIMO_API_KEY`。请在 `claude mcp add` 中通过 `-e MIMO_API_KEY=...` 注入，或在运行环境中提前设置该变量。

### 报 `图片不存在`

请确认传入的是 Claude Code 当前环境可访问的本地路径。Windows 下建议使用绝对路径，或确认相对路径是相对于当前工作目录解析的。

### 报 `不支持的格式`

当前只支持 `png`、`jpg`、`jpeg`、`webp`、`gif`。其他格式请先转换。

### 报 `图片过大`

图片超过 5MB 时会自动缩放到限制内（渐进式：缩尺寸 → 降 JPEG 质量 → 兜底砍半），通常不需要手动处理。如果自动缩放后 OCR 质量不满意，可以手动缩放到合适大小再调用。

### 报 `MiMo API ...`

这是上游 MiMo API 返回的 HTTP 错误。通常需要检查 API Key、账户权限、模型名、接口地址或请求额度。

### 报 `网络错误`

请检查本机网络、代理设置和 `MIMO_BASE_URL` 是否可访问。

### 报 `MiMo 返回空文本`

上游返回格式中没有可提取的文本内容。常见原因是 `max_tokens` 被模型的 thinking 阶段耗尽——服务会自动翻倍重试（8192 → 16384 → 32768 封顶），一般能自动恢复。如果仍然失败，可以尝试把 prompt 写得更具体，或检查上游模型服务是否正常。

## Community

This project is shared with the [LINUX DO](https://linux.do/) community.

## License

本项目使用 MIT License，详见 [LICENSE](LICENSE)。

## 设计边界

`mimo-vision` 只负责把图片理解能力桥接进 Claude Code，不替代主模型的推理和编码职责。

推荐分工是：

- MiMo Pro：主会话、代码修改、复杂推理、任务编排。
- `mimo-v2.5`：通过 MCP 工具执行图片理解、OCR 和多图分析。
- Claude Code：根据当前模型能力和提示词约束，决定何时调用 MCP 工具。

这样可以避免频繁切换模型，同时保留 MiMo Pro 的主力能力和 MiMo v2.5 的视觉能力。

# DeepSeek-OCR for ComfyUI

一个用于适用于高版本transformers的 Deepseek-OCR 的 ComfyUI 的 插件，可以使用 Deepseek-OCR 来实现OCR任务以及图像反推

## 🚀 功能亮点

- ✨ **多任务支持**：支持文档转换、自由 OCR、图像识别等多种任务类型
- 💡 **自定义提示词**：自定义提示词功能，满足不同场景需求
- 📄 **PDF 支持**：直接处理 PDF 文件


## 🛠 安装方法

### 1. 安装依赖

```bash
# 安装 poppler（用于 PDF 处理）
# Windows: 下载 https://github.com/oschwartz10612/poppler-windows/releases
# 下载后解压，将bin文件夹目录设置到系统环境的path中

# Linux (Ubuntu/Debian):
sudo apt install poppler-utils

# 安装 ComfyUI DeepSeek-OCR 节点
git clone https://github.com/swan7-py/ComfyUI-DeepseekOCR-easy.git
cd ComfyUI-DeepseekOCR-easy
```

### 2. 安装模型

```bash
下载模型[DeepSeek-OCR-Latest-BF16.I64](https://huggingface.co/prithivMLmods/DeepSeek-OCR-Latest-BF16.I64)
放置到models下的DeepSeek-OCR-Latest-BF16.I64
注意不使用官方的模型，感谢prithivMLmods使得该模型可以用于高版本transformers
```

## 📚 模型使用

### 1. 基本流程

1. 使用 `LoadPDFtoImage` 节点加载 PDF
2. 通过 `DeepSeekOCRNode` 节点进行 OCR 处理
3. 输出为 Markdown 格式的文本

### 2. 任务类型与提示词

| 任务类型              | 默认提示词                                      | 适用场景                     |
|---------------------|---------------------------------------------|--------------------------|
| `document`          | `<image>\n<|grounding|>Convert the document to markdown.` | 文档内容转换为 Markdown     |
| `without layouts`   | `<image>\nFree OCR.`                        | 无布局的简单文字提取         |
| `other image`       | `<image>\n<|grounding|>OCR this image.`      | 一般图像的文字识别           |
| `figures in document`| `<image>\nParse the figure.`                | 文档中的图表/图形解析        |
| `general`           | `<image>\nDescribe this image in detail.`   | 图像内容详细描述             |

### 3. 自定义提示词

如果填写了自定义提示词，将**覆盖**任务类型对应的默认提示词：


## 🔧 参数说明

| 参数名           | 类型        | 默认值       | 说明                                                                 |
|----------------|-----------|-----------|--------------------------------------------------------------------|
| `images`       | IMAGE     | -         | 输入图像或 PDF 转换的图像列表（由 `LoadPDFtoImage` 提供）                      |
| `mode`         | 选择框      | `Gundam`  | 模型大小选项：`Tiny`, `Small`, `Base`, `Large`, `Gundam`（推荐 `Gundam`） |
| `task_type`    | 选择框      | `document`| 任务类型：`document`, `without layouts`, `other image`, `figures in document`, `general` |
| `custom_prompt`| 文本输入框   | (空)      | 自定义提示词，优先级高于任务类型默认提示词                                 |

## 📝 使用示例

### 示例 1：标准文档转换

1. 使用 `LoadPDFtoImage` 节点加载 PDF
2. 连接 `DeepSeekOCRNode`，设置：
   - `mode`: `Gundam`
   - `task_type`: `document`
   - `custom_prompt`: (留空)
3. 输出将为结构化的 Markdown 文档

### 示例 2：自定义提示词

1. 使用 `LoadPDFtoImage` 加载 PDF
2. 连接 `DeepSeekOCRNode`，设置：
   - `mode`: `Large`
   - `task_type`: `document`
   - `custom_prompt`: `<image>\nExtract all financial figures and their values.`
3. 输出将包含提取的财务数据

## 📌 注意事项

1. **poppler 安装**：Windows 用户需要安装 poppler 并添加到系统 PATH
2. **模型大小**：`Gundam` 模型提供最佳平衡，`Tiny` 速度最快但精度较低
3. **路径问题**：Windows 路径使用 `M:/file.pdf` 格式（避免反斜杠转义问题）
4. **输出文件**：结果会保存在 ComfyUI 输出目录的 `deepseek_ocr_output.md` 中

## 📬 获取支持

- 项目仓库: [https://github.com/deepseek-ai/ComfyUI-DeepseekOCR](https://github.com/deepseek-ai/ComfyUI-DeepseekOCR)
- 模型下载: [https://huggingface.co/deepseek-ai/DeepSeek-OCR-Latest-BF16.I64](https://huggingface.co/deepseek-ai/DeepSeek-OCR-Latest-BF16.I64)

> 💡 **提示**：如需更详细的 OCR 优化，建议使用 `Gundam` 模型并设置 `task_type` 为 `document`。

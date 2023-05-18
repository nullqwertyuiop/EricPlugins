from library.util.dispatcher import PrefixMatch
from library.util.image import render_md


async def chat_help() -> bytes:
    help_str = """
# ChatCompletion 组件使用帮助

> 调整 ChatCompletion 的各类参数，使结果更加个性化

## 快速参考

| 命令                                 | 参数           | 说明                                                          |
|------------------------------------|--------------|-------------------------------------------------------------|
| `{prefix}chat --help`                     | 无            | 获取当前的帮助菜单                                                   |
| `{prefix}chat --set-system 内容`            | 内容           | 输入并替换系统提示为 “内容”，内容可以是任意字符串，但是需要使用引号包裹                       |
| `{prefix}chat --flush [--system]`         | 无            | 清空当前的聊天记录，如果加上 `--system` 参数，则同时清空系统提示                      |
| `{prefix}chat --export`                   | 无            | 回复一条消息以导出这条消息所属的会话链条                                        |
| `{prefix}chat --timeout 整数`               | 整数           | 设置等待超时时间，如果模型在给定时间内没有完成回复，则会自动结束当前回复                        |
| `{prefix}chat --cache 整数`                 | 整数           | 设置缓存区上下文大小，用于向模型提供会话链条的上下文信息（包括用户消息与模型回复）                   |
| `{prefix}chat --temperature 浮点数（0.0~2.0）` | 浮点数（0.0~2.0） | 设置模型的温度参数，用于调整模型生成结果的多样性。越低的温度，模型生成的结果越单一，越高的温度，模型生成的结果越多样。 |

## 示例

`.chat --set-system "You are a helpful assistant." --timeout 60 --cache 8 --temperature 1.0`

这段命令将会：

* 将系统提示设置为 “**You are a helpful assistant.**”
* 将等待超时时间设置为 **60** 秒
* 将缓存区上下文大小设置为 **8** 条
* 将模型温度设置为 **1.0**

## `{prefix}chat --help`

获取当前的帮助菜单

## `{prefix}chat --set-system 内容`

输入并替换系统提示为 “内容”，内容可以是任意字符串，但是需要使用引号包裹

:::tip 提示

系统提示会显著影响生成结果，可以用于自定义模型的输出内容与风格

:::

## `{prefix}chat --flush [--system]`

清空当前的聊天记录，如果加上 `--system` 参数，则同时清空系统提示

## `{prefix}chat --export`

回复一条消息以导出这条消息所属的会话链条

## `{prefix}chat --timeout 整数`

设置等待超时时间，如果模型在给定时间内没有完成回复，则会自动结束当前回复

:::warning 不建议设置过于极端的数值

一般保持默认即可，默认值为 30 秒

:::

## `{prefix}chat --cache 整数`

设置缓存区上下文大小，用于向模型提供会话链条的上下文信息（包括用户消息与模型回复）

:::warning 不建议设置过于极端的数值

一般保持默认即可，默认值为 4 条

如需要使模型记忆更多条数，可以酌情增加，如缓存区过大则会导致上下文过长而回复失败

:::

## `{prefix}chat --temperature 浮点数（0.0~2.0）`

设置模型的温度参数，用于调整模型生成结果的多样性。

越低的温度，模型生成的结果越单一，越高的温度，模型生成的结果越多样。
"""
    return await render_md(help_str.format(prefix=PrefixMatch.get_prefix()[0]))

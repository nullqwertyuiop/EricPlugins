# AI 画图

## 开始使用

此处默认已设置全局 Stable Diffusion 链接

```text
{prefix}生成图片 <正面标签组合>
```

你也可以自定义参数，参数使用换行分隔，参数顺序不限

```text
{prefix}生成图片
pos: <正面标签组合>
neg: <负面标签组合>
steps: <步数，不超过 250>
method: <采样方法，可选值为 `Euler a` `Euler b` `Euler c` `RK4`>
cfg: <CFG，浮点数，不低于 0>
```

:::warning 提示链接失效？

请检查是否已设置全局 Stable Diffusion 链接，或 Stable Diffusion 的 `webui` 是否已启动

如果都不是，你可能设置了不兼容的 `webui` 版本

:::

## 设置 Stable Diffusion 链接

:::warning 设置权限

更改链接需要 `机器人管理员` 权限

:::

:::danger 注意

此处设置的地址为全局共用，所有 AI 画图的任务都会使用此地址。

:::

```text
{prefix}设置 sd 链接 <链接>
```

如设置成功，应当返回一个 `WebSocket` 链接。

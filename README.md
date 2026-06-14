> 本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。
>
> 你可以使用、修改和分发，但必须遵守 GPLv3：保留许可证与版权声明，分发修改版时按 GPLv3 继续开放对应源码。

# gs_wuwa_daily_wife

GSCore / GsUID 用的「鸣潮今日老婆」插件。

这个插件可以做两类事情：

1. **抽鸣潮角色**：`今日老婆`、`今日老公`、`抢老婆`、老婆/老公列表；
2. **抽群友**：`今日老婆` 可以按概率抽群友，也可以单独用 `娶群友`。

请先看清楚依赖关系：

| 功能 | 是否依赖 XutheringWavesUID（XWUID） | 说明 |
| --- | --- | --- |
| 今日老婆 / 今日老公抽鸣潮角色 | **依赖** | 需要读取 XWUID 本地图片目录里的鸣潮角色图片。没有 XWUID 资源目录，就没有角色图片可发。 |
| 抢老婆 | **依赖** | 抢的是别人当天抽到的鸣潮角色老婆，所以也依赖角色图片。 |
| 老婆列表 / 老公列表 | 间接依赖 | 列表本身只显示文字，但列表数据来自今日老婆 / 今日老公记录。 |
| 今日老婆概率抽群友 | **不依赖 XWUID** | 只需要 GSCore 的群成员缓存和 QQ 头像接口。 |
| 娶群友 | **不依赖 XWUID** | 只需要 GSCore 的群成员缓存和 QQ 头像接口。 |

## 这是不是 XWUID 的扩展插件？

严格来说：**不是。**

本插件是一个独立的 GSCore / GsUID 插件，目录名是：

```text
gs_wuwa_daily_wife
```

它不是 XutheringWavesUID 仓库里面的子插件，也不是必须放进 XWUID 目录里的扩展包。

但是：

- 本插件的「鸣潮角色图片」功能需要读取 XWUID 下载/维护的本地图片资源；
- 所以普通用户想正常抽鸣潮角色老婆/老公，机器里需要安装并运行过 XWUID，让它把资源目录准备好；
- 群友相关功能不读取 XWUID 图片目录，不需要 XWUID。

一句话总结：

```text
插件本体是独立插件；
鸣潮角色图片依赖 XWUID 的本地资源；
抽群友不依赖 XWUID。
```

## 安装位置

把插件目录放到 GSCore 的插件目录里，例如：

```text
gsuid_core/gsuid_core/plugins/gs_wuwa_daily_wife
```

目录结构大概是：

```text
gsuid_core/
├── gsuid_core/
│   └── plugins/
│       └── gs_wuwa_daily_wife/
│           ├── __init__.py
│           ├── config_default.py
│           ├── daily_wife_config.py
│           ├── role_id_map.txt
│           └── README.md
└── data/
    └── XutheringWavesUID/
        ├── custom_role_pile/
        └── resource/
            └── role_pile/
```

安装后重启 GSCore，或者按你的部署方式刷新插件。

## 鸣潮角色图片从哪里来？

本插件**不再使用画廊接口，也不会联网下载鸣潮角色图**。

它只读取本地图片。

默认会自动查找这些路径：

```text
gsuid_core/data/XutheringWavesUID/custom_role_pile
```

以及：

```text
data/XutheringWavesUID/custom_role_pile
```

如果自定义图片目录没有对应角色图片，还会尝试使用 XWUID 的默认面板图目录兜底：

```text
gsuid_core/data/XutheringWavesUID/resource/role_pile
```

默认面板图文件名一般类似：

```text
role_pile_1211.png
role_pile_1304.png
```

自定义角色图片目录结构一般是这样：

```text
custom_role_pile/
├── 1211/        # 达妮娅
│   ├── 1.png
│   └── 2.jpg
├── 1304/        # 今汐
│   └── a.png
└── 1505/        # 守岸人
    └── b.webp
```

这里的 `1211`、`1304`、`1505` 是角色 ID。

角色 ID 和角色名的对应关系由插件里的：

```text
role_id_map.txt
```

决定，格式是：

```text
1211：达妮娅
1304：今汐
1505：守岸人
```

## 没装 XWUID 会怎样？

如果没有 XWUID，或者 XWUID 没有准备本地资源目录，那么这些功能可能不可用：

```text
今日老婆
今日老公
抢老婆
```

常见提示可能是：

```text
没有找到 custom_role_pile 或默认 role_pile 图片目录。
```

或者：

```text
图片目录里没有找到可用角色图片。
```

这不是插件坏了，而是没有可读取的鸣潮角色图片。

解决办法：

1. 安装并运行 XutheringWavesUID；
2. 确认存在：

```text
data/XutheringWavesUID/custom_role_pile
```

或：

```text
data/XutheringWavesUID/resource/role_pile
```

3. 如果你的目录不在默认位置，就去控制台配置 `DailyWifeCustomRolePilePath`。

## 抽群友是否依赖 XWUID？

不依赖。

群友功能只依赖 GSCore 自己的群成员缓存：

```python
CoreUser.get_group_all_user(str(ev.group_id))
```

也就是说，只要 GSCore 记录过这个群的成员，就可以抽群友。

群友头像逻辑是：

1. 先看本地缓存目录有没有头像：

```text
group_member_avatar_cache/{user_id}.jpg
```

2. 如果没有，就用群友 QQ 号请求 QQ 头像接口；
3. 下载成功后缓存到本地；
4. 发送时发送本地缓存头像。

注意：

- 群友功能不读取 XWUID 的 `custom_role_pile`；
- 群友功能不需要鸣潮角色图片；
- 群友功能需要群成员缓存，如果缓存为空，就抽不到群友；
- 群友头像缓存目录已经加入 `.gitignore`，不会提交到仓库。

## 命令说明

插件禁用了 GSCore 强制前缀继承，可以直接发中文命令。

### 今日老婆

```text
今日老婆
```

也可以用别名：

```text
娶婆娘
```

从鸣潮女角色池里抽一个今日老婆。

同一个用户在同一天、同一个群里结果固定。

如果开启了 `DailyWifeEnableGroupMember`，则有概率抽到群友；没抽中群友时，会正常抽鸣潮女角色。

### 老婆列表

推荐使用：

```text
老婆列表
```

也可以使用：

```text
今日老婆列表
```

查看当前群今天已经抽过老婆的记录。

### 自定义老婆图片上传

以下命令需要 GSCore 主人权限。

先创建自定义老婆角色：

```text
老婆创建达妮娅老婆
```

插件会自动：

- 分配一个 `900001` 起步的数字角色 ID；
- 在 GSCore / 早柚核心的 `data/gs_wuwa_daily_wife/custom_role_pile/` 下创建对应数字文件夹；
- 把 `角色ID：角色名` 写入 GSCore / 早柚核心的 `data/gs_wuwa_daily_wife/custom_role_map.txt`。

这些自定义老婆图片不会写进 XWUID 的 `custom_role_pile`，而是写进 GSCore / 早柚核心 `data/gs_wuwa_daily_wife/`，避免和 XWUID 面板图冲突。

然后发送图片并带命令：

```text
老婆上传图片达妮娅
```

也可以不提前创建，直接上传图片；如果角色不存在会自动创建。

上传成功会返回每张图片的 8 位图片 ID，后续删除要用这个 ID。

查看某个自定义老婆的图片列表：

```text
老婆图片列表达妮娅
```

列表会通过合并转发发送，每张图片和对应图片 ID 分开显示，方便复制 ID 删除。

删除某张自定义老婆图片：

```text
老婆删除图片达妮娅 图片ID
```

例如：

```text
老婆删除图片达妮娅 abcd1234
```

删除整个自定义老婆角色：

```text
老婆删除达妮娅
```

这个命令会删除该角色在 GSCore / 早柚核心 `data/gs_wuwa_daily_wife/` 下的全部自定义图片和映射，需要二次确认。发起后按提示发送：

```text
老婆删除确认
```

如果不想删除，可以发送：

```text
老婆删除取消
```

### 今日老公

需要先在控制台开启：

```text
DailyWifeHusbandEnabled
```

然后发送：

```text
今日老公
```

只从男角色池里抽。

### 老公列表

推荐使用：

```text
老公列表
```

查看当前群今天已经抽过老公的记录。

### 娶群友

需要先在控制台开启：

```text
DailyWifeMarryGroupMemberEnabled
```

然后发送：

```text
娶群友
```

这个命令只抽群友，不抽鸣潮角色。

它不依赖 XWUID。

### 抢老婆

需要先在控制台开启：

```text
DailyWifeRobEnabled
```

用法：

```text
抢老婆 @对方
```

或者：

```text
抢老婆 对方QQ
```

也可以用：

```text
抢今日老婆 @对方
```

或别名：

```text
抢婆娘 @对方
```

规则：

- 对方今天必须已经抽过 `今日老婆`；
- 自己不能抢自己；
- 普通用户每天只能抢一次；
- GSCore 主人不受次数限制；
- 成功后，你当天的老婆会变成对方那一个；
- 被抢的人当天不会自动补抽，再发 `今日老婆` 会提示老婆已经被抢走。

## Debug 模式

控制台配置：

```text
DailyWifeDebugMode
```

开启后，**只有 GSCore 主人**可以使用 Debug 功能。

Debug 模式下：

- 主人可以无限抽；
- 主人可以指定角色名；
- Debug 抽取结果不写入今日老婆/老公列表。

示例：

```text
今日老婆 达妮娅
```

```text
今日老公 忌炎
```

普通用户不能指定角色。普通用户发送类似命令时会提示没有权限。

## 控制台配置说明

| 配置项 | 默认值 | 小白解释 |
| --- | --- | --- |
| `DailyWifeCustomRolePilePath` | 空 | 本地角色图片目录。留空会自动找 XWUID 的 `custom_role_pile`。如果自动找不到，再手动填绝对路径。 |
| `DailyWifeRoleMapPath` | 空 | 角色 ID 对照表路径。留空用插件自带的 `role_id_map.txt`。 |
| `DailyWifeSendText` | 开启 | 发图片前是否带一句“你今天的老婆是xxx”。 |
| `DailyWifeAtUser` | 开启 | 发结果时是否艾特触发命令的人。 |
| `DailyWifeShowRoleId` | 关闭 | 是否在文字里显示角色 ID。 |
| `DailyWifeDebugMode` | 关闭 | 主人调试模式。开启后主人可以指定角色，且不计入列表。 |
| `DailyWifeTextTemplate` | `你今天的老婆是{name}` | 今日老婆文字模板。可用 `{name}`、`{role_id}`。 |
| `DailyWifeEnableGroupMember` | 关闭 | 今日老婆是否有概率抽群友。 |
| `DailyWifeGroupMemberProbability` | `0.1` | 抽群友概率。`0.1` 是 10%，`0.5` 是 50%，`1` 是必定抽群友。 |
| `DailyWifeGroupMemberTextTemplate` | `你今天的老婆是{name}` | 今日老婆抽到群友时的文字模板。可用 `{name}`、`{user_id}`。 |
| `DailyWifeMarryGroupMemberEnabled` | 关闭 | 是否启用 `娶群友`。 |
| `DailyWifeMarryGroupMemberTextTemplate` | `你娶到的群友是{name}` | 娶群友文字模板。可用 `{name}`、`{user_id}`。 |
| `DailyWifeHusbandEnabled` | 关闭 | 是否启用 `今日老公`。 |
| `DailyHusbandTextTemplate` | `你今天的老公是{name}` | 今日老公文字模板。可用 `{name}`、`{role_id}`。 |
| `DailyWifeRobEnabled` | 开启 | 是否启用抢老婆。 |
| `DailyWifeRobSuccessRate` | `0.5` | 抢老婆成功概率。`0.5` 是 50%。 |
| `DailyWifeRobSuccessTemplate` | `抢老婆成功！你把对方今天的老婆{name}抢过来了！` | 抢老婆成功后的提示。可用 `{name}`、`{role_id}`、`{target}`。 |

## 推荐配置方式

### 只想抽鸣潮老婆

你需要：

1. 安装 XWUID；
2. 确认 XWUID 的角色图片资源存在；
3. 保持群友功能关闭。

推荐配置：

```text
DailyWifeEnableGroupMember = 关闭
DailyWifeMarryGroupMemberEnabled = 关闭
DailyWifeHusbandEnabled = 按需开启
```

### 想让今日老婆偶尔抽到群友

推荐配置：

```text
DailyWifeEnableGroupMember = 开启
DailyWifeGroupMemberProbability = 0.1
```

意思是：

```text
90% 概率抽鸣潮女角色
10% 概率抽群友
```

如果你想更刺激，可以改成：

```text
DailyWifeGroupMemberProbability = 0.3
```

### 只想单独玩娶群友

推荐配置：

```text
DailyWifeMarryGroupMemberEnabled = 开启
```

然后直接发：

```text
娶群友
```

这个不要求 XWUID 图片目录存在。

## 常见问题

### 1. 发 `今日老婆` 没图片

先检查 XWUID 资源目录是否存在。

常见路径：

```text
gsuid_core/data/XutheringWavesUID/custom_role_pile
```

或：

```text
gsuid_core/data/XutheringWavesUID/resource/role_pile
```

如果这两个都没有，说明 XWUID 资源没准备好。

### 2. 为什么群友能抽，鸣潮角色不能抽？

因为这两个功能依赖不一样。

```text
群友：依赖 GSCore 群成员缓存 + QQ 头像接口
鸣潮角色：依赖 XWUID 本地角色图片
```

所以群友能抽，不代表鸣潮角色图片目录一定存在。

### 3. 为什么鸣潮角色能抽，群友不能抽？

可能是 GSCore 还没有记录到群成员缓存。

可以让群里成员多发几句话，或者确认你的协议端/适配器是否能把群成员写入 GSCore 的 `CoreUser`。

### 4. 为什么 `今日老公` 没反应？

先去控制台开启：

```text
DailyWifeHusbandEnabled
```

不开启时，`今日老公` 会提示功能关闭。

### 5. 为什么 `娶群友` 没反应？

先去控制台开启：

```text
DailyWifeMarryGroupMemberEnabled
```

不开启时，`娶群友` 会提示功能关闭。

### 6. 为什么抢不了别人老婆？

常见原因：

- `DailyWifeRobEnabled` 关闭了；
- 对方今天还没有发过 `今日老婆`；
- 你已经抢过一次；
- 你抢的是自己；
- 对方今天抽到的是群友，群友不能被抢。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `__init__.py` | 插件主逻辑。 |
| `config_default.py` | 控制台默认配置。 |
| `daily_wife_config.py` | 配置读取入口。 |
| `role_id_map.txt` | 鸣潮角色 ID 和名字对应表。 |
| `daily_wife_data.json` | 每日抽取记录，运行时生成，不提交。 |
| `group_member_avatar_cache/` | 群友头像缓存目录，运行时生成，不提交。 |

## 致谢

- [CWalkene](https://github.com/CWalkene)：感谢他给本插件提了很多 PR 和改进建议，包括抢老婆相关逻辑、老婆列表显示、默认面板图兜底、Debug 模式与指令修复等，让插件功能更完整、使用体验更好。

## 一句话给小白

如果你只是想用：

```text
今日老婆
今日老公
抢老婆
```

请先装好 XWUID，并确认 XWUID 的本地角色图片资源存在。

如果你只是想用：

```text
娶群友
```

不需要 XWUID，只要 GSCore 有群成员缓存就行。

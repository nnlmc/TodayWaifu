> 本项目采用 **GNU General Public License v3.0（GPLv3）** 开源。
>
> 你可以使用、修改和分发，但必须遵守 GPLv3：保留许可证与版权声明，分发修改版时按 GPLv3 继续开放对应源码。

# gs_wuwa_daily_wife

GSCore / GsUID 版鸣潮“今日老婆”插件。

插件现在只使用 XWUID 画廊接口获取图片，不再读取本地角色图片目录，也不再需要本地角色 ID 对照表。

## 插件目录

```text
gs_wuwa_daily_wife
```

## 使用方法

固定触发命令：

```text
今日老婆
```

插件禁用 GSCore 强制前缀继承，直接发送 `今日老婆` 即可触发。

触发后，插件会按当天日期、用户 ID 和当前群号固定随机一个结果；同一个用户在不同群会分别固定，不再跨群同步。

抽取流程：

1. 请求 `DailyWifeGalleryApiUrl` 配置的 XWUID 画廊接口；
2. 过滤男角色和所有名字包含 `漂泊者` 的角色；
3. 从保留角色中随机一个角色；
4. 只使用该角色的 `角色立绘` 图片列表；
5. 随机下载一张图片并发送。

画廊接口和图片路径都需要账号密码。插件会用控制台配置的画廊账号密码请求接口和下载图片，然后以图片字节发送，不会把账号密码拼进图片 URL。

## 控制台配置

- `DailyWifeGalleryApiUrl`：画廊接口地址，默认 `https://img.xlinxc.cn/api/xwuid/roles`；
- `DailyWifeGalleryUsername`：画廊账号；
- `DailyWifeGalleryPassword`：画廊密码；
- `DailyWifeSendText`：是否发送“你今天的老婆是xxx”；
- `DailyWifeAtUser`：发送今日老婆和抢老婆成功图片时是否艾特对应用户；
- `DailyWifeShowRoleId`：是否显示角色 ID；
- `DailyWifeTextTemplate`：文字模板，可用变量 `{name}`、`{role_id}`；
- `DailyWifeMasterUnlimited`：主人无限抽老婆，开启后 GSCore 主人不会固定当天结果；
- `DailyWifeRobSuccessRate`：抢老婆成功概率；
- `DailyWifeRobSuccessTemplate`：抢老婆成功提示，可用变量 `{name}`、`{role_id}`、`{target}`。

## 抢老婆

使用 `wl抢老婆 @对方` 或 `wl抢老婆 对方QQ` 可以抢别人的今日老婆。

- 普通用户每天只能抢一次；
- 机器人主人不受次数限制；
- 抢老婆有成功/失败概率；
- 失败提示固定为：`抢老婆失败了，还被对方痛扁了一顿！`；
- 成功后，自己的今日老婆会被替换成对方今天的老婆。

## 账号发放

画廊账号密码由管理员单独发放。用户拿到账号密码后，在插件控制台填写 `DailyWifeGalleryUsername` 和 `DailyWifeGalleryPassword` 即可。

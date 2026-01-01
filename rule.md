# 适配说明

由于作者精力有限，不会主动适配不常用或者自己不用的软件。提交Issue时请给出截图、应用包名、必需的Activity适配信息和具体适配要求；PR时建议在本地提前进行验证，填写[list.csv](list.csv)，修改[changelog.md](changelog.md)。
对于部分大厂软件可能无法生效。

你可以在这里获取针对特定应用的[一些经验](https://github.com/Ianzb/MiNavBarImmerse/discussions)，并分享你的经验。

## 原理

模块通过替换`/data/system/cloudFeature_navigation_bar_immersive_rules_list.json`生效，规则位于[module/immerse_rules.json](/module/immerse_rules.json)，模块内的文件是基于源文件修改得来的。

新版配置文件为JSON格式，支持更灵活的沉浸式规则配置。

## 配置文件结构

### 基本结构
```json
{
  "dataVersion": "250912",
  "modules": "navigation_bar_immersive_application_config_new",
  "modifyApps": "modifyApps",
  "NBIRules": {
    "应用包名": {
      "name": "应用名称（模块为便于管理而自行添加的项目）",
      "enable": true,
      "activityRules": {
        "Activity名称": {
          "mode": "适配模式",
          "color": "颜色值"
        }
      }
    }
  }
}
```

### 规则说明

#### 应用级别配置
- `name`: 应用显示名称（可选）
- `enable`: 是否启用该应用的沉浸式适配
- `activityRules`: 活动规则列表

#### 活动规则配置
- `Activity名称`: 可以是具体的Activity类名，或使用通配符`*`表示所有Activity
- `mode`: 适配模式（0-3）
- `color`: 颜色值（仅当mode=1时有效，ARGB格式的32位整数）

## 适配模式

### 0：默认样式
- 使用系统默认的导航栏样式
- 通常显示黑色或灰色的导航栏背景

### 1：取色模式
- 小白条背景为指定颜色
- 必须提供`color`字段
- 颜色值使用有符号32位整数表示
- 示例：
  - `"color": 0`：透明（0x00000000）
  - `"color": -16777216`：不透明黑色（0xFF000000）
  - `"color": -1`：不透明白色（0xFFFFFFFF）

### 2：悬浮显示模式
- 小白条悬浮显示在应用内容上方
- 可能会有轻微遮挡
- 无`color`字段或`color`为`null`

### 3：自适应模式（推测）
- 可能根据内容自动调整导航栏样式
- 具体行为取决于系统实现

## 通配符使用

使用`*`作为Activity名称可以匹配应用的所有Activity：
```json
"activityRules": {
  "*": {
    "mode": 2,
    "color": null
  }
}
```

## 多Activity配置示例

```json
{
  "com.example.app": {
    "name": "示例应用",
    "enable": true,
    "activityRules": {
      "*": {
        "mode": 2,
        "color": null
      },
      "MainActivity": {
        "mode": 0,
        "color": null
      },
      "VideoPlayerActivity": {
        "mode": 1,
        "color": -16777216
      }
    }
  }
}
```

## 推荐适配策略

### 快速适配方案
对于大多数应用，推荐使用：
1. 全局悬浮显示 + 主界面默认样式
2. 或全局悬浮显示 + 特定页面取色

### 悬浮显示模式 (mode 2)
**适用场景：**
- 需要上下滑动的信息流页面（如微博、知乎）
- 搜索、设置、地图等无底部固定控件的页面
- 共用Activity但UI变化大的页面

**注意事项：**
- 可能会遮挡底部内容
- 需要测试不同页面的显示效果

### 取色模式 (mode 1)
**适用场景：**
- 有固定底栏的页面
- 颜色相对固定的界面

**限制：**
- 不支持动态取色
- 不适用于支持主题/皮肤/深浅色切换的界面
- 如果应用自带的颜色填充已经满意，建议维持默认

## 调试技巧

### 1. 悬浮效果预览
在HyperOS的关机界面，小白条会自动隐藏，此时悬浮效果会强制生效，可以通过这种方式初步判断指定Activity能否适配悬浮样式。

### 2. 颜色测试
可以通过临时修改`color`值，查看不同颜色在界面上的表现。

### 3. 优先级测试
配置文件优先级较低，可能被应用自身设置覆盖。如果配置不生效：
- 检查应用是否强制设置了导航栏样式
- 尝试不同的`mode`值

## 提交适配

### 准备工作
1. 安装并测试应用的各种页面
2. 确定需要适配的Activity名称
3. 选择合适的适配模式
4. 如果需要取色，确定合适的颜色值

### 修改配置文件
1. 在`module/navigation_bar_immersive_rules_list.json`中添加或修改规则
2. 更新`list.csv`记录适配信息
3. 在`changelog.md`中添加更新说明

### 验证
- 在本地设备上测试适配效果
- 确保不会造成界面异常或功能问题
- 截图记录适配前后的对比

## 常见问题

### Q: 配置为什么不生效？
A: 可能的原因：
1. 应用强制设置了导航栏样式
2. Activity名称不正确
3. 被系统云控覆盖
4. 配置文件格式错误

### Q: 如何获取Activity名称？
A: 可以使用以下方法：
1. 开发者选项中的"显示布局边界"
2. ADB命令：`adb shell dumpsys activity activities`
3. 第三方Activity检测工具，如MT管理器

### Q: 颜色值如何确定？
A: 可以使用：
1. 取色工具获取底栏颜色
2. 将ARGB十六进制值转换为有符号32位整数
3. 常见的颜色值：
   - 透明：0
   - 黑色：-16777216
   - 白色：-1

### Q: 通配符`*`会覆盖具体Activity规则吗？
A: 不会，具体Activity规则优先级高于通配符规则。系统会优先匹配具体的Activity名称，如果没有匹配到，才会使用通配符规则。

---

**重要提示：**
- 适配前请充分测试
- 记录所有修改和测试结果
- 对于复杂的应用，建议分步骤适配
- 如果遇到无法解决的问题，可以先维持默认样式

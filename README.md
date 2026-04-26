# 自动赚钱脚本面板

一个基于 Python 的桌面脚本工具，启动后打开 GUI 面板，支持选择不同赚钱模式、显示脚本说明、通过全局热键控制开始/暂停/结束，并按配置文件执行键盘鼠标自动化操作。

## 当前功能

- GUI 面板展示作者信息与 B 站链接
- 左侧模式选择，右侧显示脚本说明
- 支持全局热键
- `F9` 暂停 / 继续
- `F10` 开始 / 结束
- 支持执行次数设置
- 支持动作类型：按键、鼠标移动、鼠标点击、等待、循环
- 支持 `16:9` 分辨率校验与自动缩放
- 每次开始执行前自动重载当前脚本配置
- 已内置 `泯除方块`、`店长特供（团三郎）`、`店长特供（45秒娜娜莉海月）`、`店长特供（45秒娜娜莉白藏）`

## 项目结构

```text
nte_auto_make_money/
├── auto_money_gui.py
├── start_gui.bat
├── requirements.txt
├── README.md
└── configs/
    ├── 01_泯除方块.txt
    ├── 02_店长特供（团三郎）.txt
    ├── 03_店长特供（45秒娜娜莉海月）.txt
    └── 04_店长特供（45秒娜娜莉白藏）.txt
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动方式

### 方式一：命令行启动

```bash
python auto_money_gui.py
```

### 方式二：Windows 双击启动

直接双击项目根目录下的 `start_gui.bat`。

请使用管理员模式启动 `start_gui.bat`。

这个批处理会自动：

- 进入脚本所在目录
- 检查 `py` 或 `python` 命令
- 安装依赖
- 启动 GUI

## 配置文件格式

每个脚本一个 `.txt` 文件，放在 `configs` 目录中。

配置文件不再依赖固定行号，而是使用 `@` 标签头：

```text
@resolution 2560x1440
@name 泯除方块
@description
请先手操一把。
在游戏机前，可以按F的情况下开启脚本。
务必调低画质，确保加载速度！
@actions
KEY f
WAIT 2
MOVE 2125 488
CLICK left
MOVE 2238 1347
CLICK left
WAIT 7
LOOP_START 14
KEY space
WAIT 0.2
LOOP_END
KEY esc
WAIT 3
```

### 配置标签说明

- `@resolution` 基准分辨率，例如 `2560x1440`
- `@name` 脚本名称
- `@description` 脚本说明文本，会显示在 GUI 右侧
- `@description` 可单行书写，也可单独占一行后继续写多行正文
- `@actions` 表示从下一行开始进入动作区
- `#` 表示单行注释，可用于头部和动作区

多行说明示例：

```text
@name 泯除方块
@description
请先手操一把。
在游戏机前，可以按F的情况下开启脚本。
@actions
```

## 支持的动作指令

```text
KEY f
KEY space
MOVE 2125 488
CLICK left
WAIT 2
LOOP_START 14
LOOP_END
EMPTY
```

### 指令说明

- `KEY xxx`：按下一个按键，例如 `f`、`esc`、`space`
- `MOVE x y`：将鼠标移动到指定坐标，运行时会根据实际分辨率自动缩放
- `CLICK left`：鼠标点击，当前支持 `left`
- `WAIT 秒数`：等待指定秒数，例如 `WAIT 0.2`
- `LOOP_START 次数`：开始循环
- `LOOP_END`：结束循环
- `EMPTY`：空脚本占位，用于尚未编写动作的模式

## 分辨率规则

- 配置文件中的基准分辨率默认为 `2560x1440`
- 如果实际运行分辨率仍为 `16:9`，程序会自动按比例缩放坐标
- 如果当前屏幕不是 `16:9`，程序会弹出错误提示并拒绝执行

## 热键说明

- `F9`：暂停 / 继续
- `F10`：开始 / 结束

## 鼠标移动说明

- 鼠标移动使用平滑轨迹
- 会附带轻微随机偏移，避免机械直线
- 整体保持近似恒定速度

## 注意事项

- 运行脚本前请确认游戏窗口状态正确
- 首次运行前请先安装依赖
- 全局热键依赖系统权限，部分环境下可能需要允许辅助功能权限
- `pyautogui` 默认启用 failsafe，鼠标迅速移到屏幕左上角可中断自动化操作

## Git 仓库

当前本地目录已初始化 Git 仓库，并已关联远程：

`https://github.com/AmicBeam/nte_auto_make_money`

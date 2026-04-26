import math
import random
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyautogui
import tkinter as tk
from pynput import keyboard
from tkinter import messagebox, ttk


CONFIG_DIR = Path(__file__).resolve().parent / "configs"
BILIBILI_URL = "https://space.bilibili.com/9412490"
APP_TITLE = "自动赚钱脚本面板"
RATIO_TOLERANCE = 0.03
UI_FONT_FAMILY = "Microsoft YaHei UI"
UI_FONT_BODY = (UI_FONT_FAMILY, 10)
UI_FONT_TITLE = (UI_FONT_FAMILY, 12, "bold")
UI_FONT_LINK = (UI_FONT_FAMILY, 10, "underline")


@dataclass
class Action:
    kind: str
    args: Tuple[object, ...] = ()


@dataclass
class ScriptConfig:
    file_path: Path
    base_width: int
    base_height: int
    name: str
    description: str
    actions: List[Action]


class ScriptEngine:
    def __init__(self, app: "MoneyApp") -> None:
        self.app = app
        self.worker: Optional[threading.Thread] = None
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.running_lock = threading.Lock()
        self.is_running = False
        self.pause_event.set()

    def start(self, config: ScriptConfig, run_times: int) -> bool:
        with self.running_lock:
            if self.is_running:
                return False
            self.is_running = True

        self.stop_event.clear()
        self.pause_event.set()
        self.worker = threading.Thread(
            target=self._run_script, args=(config, run_times), daemon=True
        )
        self.worker.start()
        return True

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.set()
        self.app.set_status("正在停止脚本...")

    def toggle_pause(self) -> None:
        if not self.is_running:
            self.app.set_status("当前没有正在执行的脚本。")
            return

        if self.pause_event.is_set():
            self.pause_event.clear()
            self.app.set_paused(True)
            self.app.set_status("脚本已暂停，按 F9 继续。")
        else:
            self.pause_event.set()
            self.app.set_paused(False)
            self.app.set_status("脚本已继续执行。")

    def _finish(self) -> None:
        with self.running_lock:
            self.is_running = False
        self.pause_event.set()
        self.stop_event.clear()
        self.app.on_script_finished()

    def _run_script(self, config: ScriptConfig, run_times: int) -> None:
        try:
            scale = self.app.validate_and_get_scale(config)
            if scale is None:
                return

            if not config.actions:
                self.app.show_error("当前脚本配置没有动作内容，无法执行。")
                return

            for current_round in range(1, run_times + 1):
                if self.stop_event.is_set():
                    break
                self.app.set_status(f"执行中：第 {current_round}/{run_times} 次")
                self._execute_actions(config.actions, scale)

            if self.stop_event.is_set():
                self.app.set_status("脚本已结束。")
            else:
                self.app.set_status("脚本执行完成。")
        except Exception as exc:  # noqa: BLE001
            self.app.show_error(f"执行脚本时发生错误：{exc}")
        finally:
            self._finish()

    def _execute_actions(
        self, actions: List[Action], scale: Tuple[float, float], start_index: int = 0
    ) -> int:
        index = start_index
        while index < len(actions):
            self._wait_if_paused_or_stopped()
            if self.stop_event.is_set():
                return len(actions)

            action = actions[index]
            if action.kind == "loop_start":
                repeat = int(action.args[0])
                loop_body, next_index = self._collect_loop_body(actions, index + 1)
                for _ in range(repeat):
                    self._execute_actions(loop_body, scale, 0)
                    if self.stop_event.is_set():
                        break
                index = next_index
                continue

            self._execute_action(action, scale)
            index += 1
        return index

    def _collect_loop_body(
        self, actions: List[Action], start_index: int
    ) -> Tuple[List[Action], int]:
        loop_body: List[Action] = []
        depth = 1
        index = start_index
        while index < len(actions):
            action = actions[index]
            if action.kind == "loop_start":
                depth += 1
            elif action.kind == "loop_end":
                depth -= 1
                if depth == 0:
                    return loop_body, index + 1
            loop_body.append(action)
            index += 1
        raise ValueError("LOOP_START 没有找到匹配的 LOOP_END")

    def _execute_action(self, action: Action, scale: Tuple[float, float]) -> None:
        sx, sy = scale
        kind = action.kind
        args = action.args

        if kind == "key":
            key_name = str(args[0]).lower()
            pyautogui.press("space" if key_name == "空格" else key_name)
        elif kind == "move":
            x = float(args[0]) * sx
            y = float(args[1]) * sy
            self._smooth_move(int(round(x)), int(round(y)))
        elif kind == "click":
            button = str(args[0]).lower()
            pyautogui.click(button=button)
        elif kind == "wait":
            self._interruptible_sleep(float(args[0]))
        elif kind == "loop_end":
            return
        else:
            raise ValueError(f"未知动作类型：{kind}")

    def _wait_if_paused_or_stopped(self) -> None:
        while not self.pause_event.is_set():
            if self.stop_event.is_set():
                return
            time.sleep(0.05)

    def _interruptible_sleep(self, seconds: float) -> None:
        end_time = time.perf_counter() + seconds
        while time.perf_counter() < end_time:
            self._wait_if_paused_or_stopped()
            if self.stop_event.is_set():
                return
            remaining = end_time - time.perf_counter()
            time.sleep(min(0.05, max(0.0, remaining)))

    def _smooth_move(self, target_x: int, target_y: int) -> None:
        start_x, start_y = pyautogui.position()
        dx = target_x - start_x
        dy = target_y - start_y
        distance = math.hypot(dx, dy)
        if distance < 1:
            pyautogui.moveTo(target_x, target_y)
            return

        speed = random.uniform(1800.0, 2400.0)
        total_time = max(0.2, distance / speed)
        step_interval = 0.01
        steps = max(1, int(total_time / step_interval))
        jitter = min(16.0, max(4.0, distance * 0.03))
        angle = math.atan2(dy, dx)
        perp_x = -math.sin(angle)
        perp_y = math.cos(angle)
        phase = random.uniform(0, math.pi)

        for step in range(1, steps + 1):
            self._wait_if_paused_or_stopped()
            if self.stop_event.is_set():
                return

            progress = step / steps
            base_x = start_x + dx * progress
            base_y = start_y + dy * progress
            wave = math.sin(progress * math.pi + phase)
            offset_scale = math.sin(progress * math.pi)
            offset = wave * jitter * offset_scale * 0.35
            noise = random.uniform(-1.2, 1.2) * offset_scale
            x = base_x + perp_x * offset + noise
            y = base_y + perp_y * offset + noise
            pyautogui.moveTo(int(round(x)), int(round(y)))
            time.sleep(step_interval)

        pyautogui.moveTo(target_x, target_y)


class MoneyApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("990x540")
        self.root.minsize(946, 500)
        self._setup_styles()

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

        self.engine = ScriptEngine(self)
        self.configs = self.load_configs()
        self.mode_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪，按 F10 开始或点击开始按钮。")
        self.hotkey_var = tk.StringVar(value="热键：F9 暂停/继续，F10 开始/结束")
        self.run_times_var = tk.StringVar(value="1")
        self.script_name_var = tk.StringVar(value="")
        self.paused = False
        self.hotkey_listener: Optional[keyboard.Listener] = None

        self._build_ui()
        self._bind_hotkeys()

        mode_names = list(self.configs.keys())
        if mode_names:
            self.mode_var.set(mode_names[0])
            self._on_mode_change()

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        style.configure("TLabel", font=UI_FONT_BODY)
        style.configure("TButton", font=UI_FONT_BODY)
        style.configure("TRadiobutton", font=UI_FONT_BODY)
        style.configure("TLabelframe", font=UI_FONT_BODY)
        style.configure("TLabelframe.Label", font=UI_FONT_BODY)
        style.configure("TEntry", font=UI_FONT_BODY)

    def load_configs(self) -> Dict[str, ScriptConfig]:
        configs: Dict[str, ScriptConfig] = {}
        if not CONFIG_DIR.exists():
            raise FileNotFoundError(f"配置目录不存在：{CONFIG_DIR}")

        for file_path in sorted(CONFIG_DIR.glob("*.txt")):
            config = self.parse_config(file_path)
            configs[config.name] = config
        return configs

    def parse_config(self, file_path: Path) -> ScriptConfig:
        raw_lines = file_path.read_text(encoding="utf-8").splitlines()
        metadata: Dict[str, str] = {}
        action_lines: List[str] = []
        in_actions = False

        index = 0
        while index < len(raw_lines):
            line = raw_lines[index].strip()
            if not line:
                index += 1
                continue

            if line.startswith("#"):
                index += 1
                continue

            if in_actions:
                action_lines.append(line)
                index += 1
                continue

            if not line.startswith("@"):
                raise ValueError(
                    f"配置头格式错误：{file_path.name} 中的 `{line}` 需要写成标签格式"
                )

            tag_line = line[1:].strip()
            if not tag_line:
                index += 1
                continue

            if tag_line.lower() == "actions":
                in_actions = True
                index += 1
                continue

            parts = tag_line.split(None, 1)
            key = parts[0].strip().lower()

            if len(parts) == 1:
                if key != "description":
                    raise ValueError(
                        f"配置标签缺少内容：{file_path.name} 中的 `{line}`"
                    )

                desc_lines: List[str] = []
                index += 1
                while index < len(raw_lines):
                    next_line = raw_lines[index].rstrip()
                    next_stripped = next_line.strip()
                    if next_stripped.startswith("@"):
                        break
                    if next_stripped.startswith("#"):
                        index += 1
                        continue
                    desc_lines.append(next_stripped)
                    index += 1

                while desc_lines and not desc_lines[0]:
                    desc_lines.pop(0)
                while desc_lines and not desc_lines[-1]:
                    desc_lines.pop()

                value = "\n".join(desc_lines)
                if not value:
                    raise ValueError(
                        f"配置标签缺少内容：{file_path.name} 中的 `{line}`"
                    )
            else:
                value = parts[1].strip()

            if key == "description" and key in metadata:
                metadata[key] = f"{metadata[key]}\n{value}"
            else:
                metadata[key] = value

            if len(parts) != 1:
                index += 1

        missing_keys = [
            key for key in ("resolution", "name", "description") if key not in metadata
        ]
        if missing_keys:
            raise ValueError(
                f"配置文件缺少标签 {', '.join(missing_keys)}：{file_path.name}"
            )

        base_width, base_height = self.parse_resolution(metadata["resolution"])
        name = metadata["name"]
        description = metadata["description"]
        actions = self.parse_actions(action_lines)

        return ScriptConfig(
            file_path=file_path,
            base_width=base_width,
            base_height=base_height,
            name=name,
            description=description,
            actions=actions,
        )

    def parse_resolution(self, text: str) -> Tuple[int, int]:
        if "x" not in text.lower():
            raise ValueError(f"分辨率格式错误：{text}")
        left, right = text.lower().split("x", 1)
        return int(left), int(right)

    def parse_actions(self, lines: List[str]) -> List[Action]:
        actions: List[Action] = []
        loop_depth = 0
        for line in lines:
            if line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue

            command = parts[0].upper()
            if command == "KEY" and len(parts) >= 2:
                actions.append(Action("key", (" ".join(parts[1:]),)))
            elif command == "MOVE" and len(parts) == 3:
                actions.append(Action("move", (float(parts[1]), float(parts[2]))))
            elif command == "CLICK" and len(parts) == 2:
                actions.append(Action("click", (parts[1],)))
            elif command == "WAIT" and len(parts) == 2:
                actions.append(Action("wait", (float(parts[1]),)))
            elif command == "LOOP_START" and len(parts) == 2:
                loop_depth += 1
                actions.append(Action("loop_start", (int(parts[1]),)))
            elif command == "LOOP_END":
                loop_depth -= 1
                if loop_depth < 0:
                    raise ValueError(f"{line} 缺少对应的 LOOP_START")
                actions.append(Action("loop_end"))
            elif command == "EMPTY":
                continue
            else:
                raise ValueError(f"无法识别的配置命令：{line}")

        if loop_depth != 0:
            raise ValueError("循环块没有完整闭合")
        return actions

    def validate_and_get_scale(self, config: ScriptConfig) -> Optional[Tuple[float, float]]:
        actual_w, actual_h = pyautogui.size()
        base_ratio = config.base_width / config.base_height
        actual_ratio = actual_w / actual_h

        if abs(base_ratio - 16 / 9) > RATIO_TOLERANCE:
            self.show_error(
                f"配置文件分辨率不是 16:9：{config.base_width}x{config.base_height}"
            )
            return None

        if abs(actual_ratio - 16 / 9) > RATIO_TOLERANCE:
            self.show_error(
                f"当前屏幕比例不是 16:9，检测到 {actual_w}x{actual_h}，脚本已停止。"
            )
            return None

        return actual_w / config.base_width, actual_h / config.base_height

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(main_frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="作者：静默之光").grid(row=0, column=0, sticky="w")
        link = tk.Label(
            header,
            text=BILIBILI_URL,
            fg="#1a73e8",
            cursor="hand2",
            font=UI_FONT_LINK,
        )
        link.grid(row=0, column=1, sticky="w", padx=(12, 0))
        link.bind("<Button-1>", self._open_bilibili_link)

        left_panel = ttk.LabelFrame(main_frame, text="赚钱模式", padding=12)
        left_panel.grid(row=1, column=0, sticky="nsw", padx=(0, 12))

        for name in self.configs:
            rb = ttk.Radiobutton(
                left_panel,
                text=name,
                value=name,
                variable=self.mode_var,
                command=self._on_mode_change,
            )
            rb.pack(anchor="w", pady=4)

        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        info_frame = ttk.LabelFrame(right_panel, text="脚本说明", padding=12)
        info_frame.grid(row=0, column=0, sticky="ew")
        info_frame.columnconfigure(0, weight=1)

        ttk.Label(
            info_frame, textvariable=self.script_name_var, font=UI_FONT_TITLE
        ).grid(row=0, column=0, sticky="w")

        self.desc_text = tk.Text(
            info_frame, height=5, wrap=tk.WORD, state=tk.DISABLED, font=UI_FONT_BODY
        )
        self.desc_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        control_frame = ttk.LabelFrame(right_panel, text="控制面板", padding=12)
        control_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        control_frame.columnconfigure(1, weight=1)

        ttk.Label(control_frame, text="执行次数：").grid(row=0, column=0, sticky="w")
        ttk.Entry(control_frame, textvariable=self.run_times_var, width=12).grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(control_frame, textvariable=self.hotkey_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Label(control_frame, textvariable=self.status_var, foreground="#0b8043").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(16, 0))
        ttk.Button(button_frame, text="开始 / 结束 (F10)", command=self.toggle_start_stop).pack(
            side=tk.LEFT
        )
        ttk.Button(button_frame, text="暂停 / 继续 (F9)", command=self.toggle_pause).pack(
            side=tk.LEFT, padx=(10, 0)
        )

    def _bind_hotkeys(self) -> None:
        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            if key == keyboard.Key.f9:
                self.root.after(0, self.toggle_pause)
            elif key == keyboard.Key.f10:
                self.root.after(0, self.toggle_start_stop)

        self.hotkey_listener = keyboard.Listener(on_press=on_press)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    def _open_bilibili_link(self, event: tk.Event) -> None:
        _ = event.widget
        webbrowser.open(BILIBILI_URL)

    def _on_mode_change(self) -> None:
        config = self.get_selected_config()
        if config is None:
            return
        self.script_name_var.set(config.name)
        self._set_description(config.description)
        if not config.actions:
            self.set_status("当前模式尚未配置动作。")
        else:
            self.set_status("就绪，按 F10 开始或点击开始按钮。")

    def _set_description(self, content: str) -> None:
        self.desc_text.configure(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", content)
        self.desc_text.configure(state=tk.DISABLED)

    def get_selected_config(self) -> Optional[ScriptConfig]:
        return self.configs.get(self.mode_var.get())

    def set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def show_error(self, text: str) -> None:
        self.root.after(0, lambda: messagebox.showerror("错误", text))

    def on_script_finished(self) -> None:
        self.paused = False

    def toggle_start_stop(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
            return

        config = self.get_selected_config()
        if config is None:
            self.show_error("请先选择一个脚本模式。")
            return
        if not config.actions:
            self.show_error("当前模式还没有配置脚本内容。")
            return

        try:
            run_times = int(self.run_times_var.get())
            if run_times <= 0:
                raise ValueError
        except ValueError:
            self.show_error("执行次数必须是大于 0 的整数。")
            return

        started = self.engine.start(config, run_times)
        if started:
            self.set_status("脚本已启动，按 F9 暂停/继续，F10 结束。")

    def toggle_pause(self) -> None:
        self.engine.toggle_pause()


def main() -> None:
    root = tk.Tk()
    app = MoneyApp(root)

    def on_close() -> None:
        app.engine.stop()
        if app.hotkey_listener is not None:
            app.hotkey_listener.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

# StreamCap 速度字段接入 · 任务总结

> 修改日期：2026-10-21（补全部署）
> 修改人：鲸鱼娘 🐋
> 工作区：`D:\抖音\修改\StreamCap`

---

## 一、目标

在 StreamCap 直播录制功能中，为 `StreamData` 和 `Recording` 模型新增视频采集实时信息字段：

- `video_resolution`（分辨率，如 `1920x1080`）
- `video_fps`（帧率）
- `source_bitrate`（源码率，kbps）
- `current_write_speed`（当前写入速度，KB/s）

并在 UI 的 **录制卡片** 和 **录制设置页** 正确显示这些字段。

---

## 二、已完成的工作

### 2.1 `stream_manager.py` — 核心实现 ✅

**文件：** `app/core/recording/stream_manager.py`

- 合并了 `rewrite_sm.py` 的完整内容（907行），替换了原有的 `update_stream_stats` + `stop_recording_notify` + `end_message_push` 区域。
- 新增方法：`update_stream_stats()`、`_probe_stream()`、`_get_robust_fps()`、`_get_bitrate_from_probe()`、`_set_stream_preview()`。
- `update_stream_stats()` 末尾新增 `self.recording.update()`，每轮将 `video_resolution`、`video_fps`、`source_bitrate`、`current_write_speed` 同步到 Recording 对象。
- `python -m py_compile` 验证通过。

### 2.2 `recording_model.py` — 模型字段 ✅

**文件：** `app/models/recording/recording_model.py`

新增字段 `video_resolution`、`video_fps`、`source_bitrate`、`current_write_speed`，`__init__` / `to_dict` / `from_dict` 三处同步更新。

### 2.3 UI 录制卡片 `recording_card.py` ✅

**文件：** `app/ui/components/business/recording_card.py`

- `_create_card_components()`：新增 `resolution_label`、`fps_label`、`bitrate_label` 三个 Text 组件，与 `status_label` 一起展示在 title_row 中；同时修改 `speed` 从 `stream_manager._stream_stats` 获取实时值。
- `update_card()`：新增分辨率/帧率/源码率的更新逻辑，响应 Recording 数据变化。
- `python -m py_compile` 验证通过 ✅

### 2.4 UI 录制设置页 `recording_dialog.py` ✅

**文件：** `app/ui/components/business/recording_dialog.py`

第 431 行 `"speed": "X KB/s"` → `"speed": "0 KB/s"`（初始化占位值，启动后由 stream_manager 填充实际值）。

### 2.5 清理临时文件 ✅

删除所有临时 fix 脚本共 13 个：

- `fix_final.py`、`fix_final2.py`、`fix_for_body.py`、`fix_all_split.py`
- `fix_newline_split.py`、`fix_split.py`、`fix_trunc.py`、`find_split.py`、`verify_fix.py`
- `fix_speed_indent.py`、`add_info_labels.py`、`add_return_labels.py`、`add_update_labels.py`

---

## 三、当前数据流

```
stream_manager.update_stream_stats()
  → _probe_stream()        → stream_info.video_resolution
  → _get_robust_fps()      → stream_info.video_fps
  → _get_bitrate_from_probe() → stream_info.source_bitrate
  → 文件大小统计
  → _stream_stats.fps / bitrate / res / last_write_speeds
  → self.recording.update() 同步到 Recording 对象
→ StreamData 返回 UI
→ recording_card 卡片：
    · title_row 显示：标题 | 状态标签 | 分辨率 | 帧率 | 源码率
    · 速度行显示：实时写入速度 KB/s
```

---

## 四、关键教训（给后续维护）

1. **Windows 上字符串替换 `\\n` → `\\\\n` 极易被 shell 吃掉**，应直接用二进制操作（`bytes.replace`）或 Python 脚本文件，不要用 bash 拼接。
2. **多重替换脚本最好写成一次性文件 + 执行 + 删除**，避免残留。
3. **合并大文件前先用 `git diff --stat` 确认行号偏移量**，防止新旧函数行号错位。
4. `await` 必须在 async 函数内，补方法时别忘了加 `async def`。
5. **ops_replace/ops_edit_file 对 CRLF 文件的缩进替换容易因字节级不匹配失败** — 反复失败时改用 Python 脚本直接读二进制（`rb/wb` 模式）、按字节替换。
6. **修复缩进损坏时先 python 脚本确认实际字节，再动手改** — 避免凭文本肉眼判断导致漏改/多改。
7. **UI 新增字段优先用二进制脚本改文件，再用 py_compile 验证** — 避免多次尝试导致文件损坏。

---

## 五、总结

| 模块 | 状态 |
|------|------|
| `stream_manager.py` 核心实现 | ✅ 完成（含 Recording 同步） |
| `recording_model.py` 模型字段 | ✅ 完成 |
| UI 录制卡片 `recording_card.py` | ✅ 完成（分辨率/帧率/源码率/速度全显示） |
| UI 录制设置页 `recording_dialog.py` | ✅ 完成（占位值替换） |
| 语法验证 | ✅ 通过 |
| 临时文件清理 | ✅ 完成（13 个脚本全部删除） |

> 任务全部完成 ✅
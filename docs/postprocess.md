# PostProcess 数据后处理指南

`EasyTeleop.Components.PostProcess.DataPostProcessor` 会把采集阶段写入 `datasets/temp/<session_id>` 的临时文件整理成可直接用于训练或回放的 `.hdf5` 数据集。本指南对 README 中的简要说明进行了补充，方便排查问题或在自定义脚本中复用该流程。

## 输入数据要求

后处理默认在 `datasets/temp` 中查找会话目录。每个会话至少需要：

- `metadata.json`：记录会话的基础信息（时间范围、连接的设备等）。
- `frames/camera_0`：主时间轴来源，文件名需形如 `frame_<timestamp>.png`/`.jpg`。
- `arm_*/poses.csv`、`joints.csv`、`end_effector.csv`（可选）：双臂的位姿、关节与末端执行器数据，索引列会在后处理阶段自动转换成向量维度。

> 临时目录的完整格式说明见 `docs/data_format.md`。

## 运行方式

仓库提供了一个简单入口：

```bash
# 处理 temp 目录下的全部会话
uv run run/run_postprocess.py

# 显式指定输入 / 输出目录，只处理单个会话
uv run run/run_postprocess.py `
  --temp_dir datasets/temp `
  --output_dir datasets/hdf5 `
  --session demo_001
```

### 参数说明

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--temp_dir` | 原始会话所在目录。 | `datasets/temp` |
| `--output_dir` | `.hdf5` 输出目录，不存在时会自动创建。 | `datasets/hdf5` |
| `--session` | 只处理指定的会话 ID。 | _空_（处理全部） |
| `--latest` | 仅处理最近修改的会话，与 `--session` 互斥。 | _空_ |
| `--list` | 只列出检测到的会话并退出。 | _空_ |

如果需要在自定义脚本中调用，可直接实例化 `DataPostProcessor(temp_dir, output_dir)`，再按需调用 `process_session_to_hdf5(session_id)` 或 `process_all_sessions()`。

## 处理流程概览

1. **扫描会话**：`find_sessions` 会过滤掉没有 `metadata.json` 的目录，避免误处理其他文件夹。
2. **加载数据**：
   - 图像：支持 PNG/JPG，缺失时自动使用 224×224 黑色占位图。
   - 状态：按时间戳读取 `pose/joint/end_effector` CSV，并根据索引建立向量。
3. **构建时间轴**：使用 `camera_0` 的帧时间戳作为主时间轴。
4. **同步/插值**：借助 `scipy.interpolate.interp1d` 将状态数据对齐到图像时间戳，少量数据点会复制最近值或填零。
5. **写入 HDF5**：
   - 图像存入 `/episodes/.../observations/images`，类型为 `vlen uint8`，与 `view_hdf5.py` 兼容。
   - 状态与动作分别写入 `/observations/state/arm_#/` 与 `/actions/arm_#/`。
   - 元信息保存在 `/metadata`、`/info` 分组，方便后续统计与可视化。

## 常见问题 & 排查

- **提示 “No camera_0 data found”**：采集阶段至少要有一个目录命名为 `camera_0`，否则无法构建主时间轴。
- **输出帧数明显偏少**：检查 `frame_<timestamp>.png` 是否完整写入，或者是否手动移动过帧文件导致时间戳缺失。
- **状态维度不正确**：CSV 中的 `index` 列会决定向量长度；缺少的索引会被填 0。
- **如何快速验收结果？**：运行 `uv run run/view_hdf5.py --path datasets/hdf5/<session>.hdf5` 可直观查看图像与状态曲线。

完善以上内容后，基本就能在不同场景中复用或定制后处理流程了。

# 多平台 AI 互动助手（本地版）

这是一个面向 Windows 的本地桌面程序，用于管理安卓设备、平台账号、关键词、目标作品画像、AI 筛选、回复草稿与发布记录。

当前版本：`0.1.0-dev`

## 当前进度

- 原生 PySide6 桌面界面
- SQLite 本地数据库与版本迁移
- 程序文件和用户数据分离
- 数据库自动备份
- ADB 设备发现与解析
- 抖音、小红书、快手、哔哩哔哩统一插件接口
- 文字、图片、语音回复能力模型
- Windows GitHub Actions 自动测试和打包

平台搜索、内容提取和实际发布仍处于适配阶段。界面不会把未实现功能显示为“已完成”。

## 本地运行

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m huifu
```

默认数据目录：

```text
%LOCALAPPDATA%\HuifuAI
```

测试时可以设置 `HUIFU_DATA_DIR` 将数据保存到其他位置。

## 测试

```powershell
pytest
```

## Windows 打包

```powershell
python -m pip install -e ".[build]"
pyinstaller --noconfirm --clean build/huifu.spec
```

生成文件位于 `dist/HuifuAI/`。仓库中的 GitHub Actions 也会自动生成 Windows 构建产物。

## 安全边界

- 平台账号在安卓 App 中由用户自行登录。
- 不在数据库中保存平台账号密码。
- 不绕过验证码、平台限制或安全验证。
- 只有重新核验成功的任务才记为发布成功。
- 发布结果不明确时不会自动重复提交。


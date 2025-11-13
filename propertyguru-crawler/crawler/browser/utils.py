"""
浏览器工具函数
提供公共的配置和工具函数
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# JavaScript 脚本常量 - 用于禁用媒体功能
DISABLE_MEDIA_JS = """
// 禁用媒体设备 API
Object.defineProperty(navigator, 'mediaDevices', {
    get: () => undefined
});
Object.defineProperty(navigator, 'getUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'webkitGetUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'mozGetUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'msGetUserMedia', {
    get: () => undefined
});

// 阻止 video 和 audio 元素加载
(function() {
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
        const element = originalCreateElement.call(document, tagName);
        if (tagName.toLowerCase() === 'video' || tagName.toLowerCase() === 'audio') {
            element.remove();
            return originalCreateElement.call(document, 'div');
        }
        return element;
    };

    // 阻止现有视频/音频元素加载
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeName === 'VIDEO' || node.nodeName === 'AUDIO') {
                    node.remove();
                }
            });
        });
    });
    observer.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true
    });
})();
"""

# 需要阻止的媒体文件扩展名
BLOCKED_MEDIA_URLS = [
    "*.mp4",
    "*.webm",
    "*.ogg",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.flv",
    "*.mkv",
    "*.m4v",
    "*.3gp",
]


def configure_performance_options(options: Any) -> None:
    """
    配置性能优化选项（禁用图片、CSS、字体等）
    公共函数，供所有浏览器类使用

    Args:
        options: Chrome选项对象
    """
    # Chrome preferences 配置
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.media_stream": 2,
        "profile.managed_default_content_settings.media_stream_mic": 2,
        "profile.managed_default_content_settings.media_stream_camera": 2,
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.autoplay": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Chrome 命令行参数
    performance_args = [
        "--blink-settings=imagesEnabled=false",
        "--disable-extensions",
        "--disable-plugins",
        "--mute-audio",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--hide-scrollbars",
        "--metrics-recording-only",
        "--no-first-run",
        "--safebrowsing-disable-auto-update",
        "--disable-ipc-flooding-protection",
    ]
    for arg in performance_args:
        options.add_argument(arg)


def setup_media_blocking_cdp(cdp_func: Callable[[str, dict[str, Any] | None], Any]) -> None:
    """
    通过 CDP 设置媒体阻止功能
    公共函数，供所有浏览器类使用

    Args:
        cdp_func: CDP命令执行函数，接受 (cmd, params) 参数
    """
    try:
        # 注入 JavaScript 禁用媒体 API
        cdp_func("Page.addScriptToEvaluateOnNewDocument", {"source": DISABLE_MEDIA_JS})

        # 启用 Network 域并阻止媒体资源
        try:
            cdp_func("Network.enable", {})
            cdp_func("Network.setBlockedURLs", {"urls": BLOCKED_MEDIA_URLS})
        except Exception:
            pass

        # 禁用媒体权限
        try:
            for permission_name in ["camera", "microphone"]:
                cdp_func(
                    "Browser.setPermission",
                    {
                        "origin": "https://*",
                        "permission": {"name": permission_name},
                        "setting": "denied",
                    },
                )
        except Exception:
            pass

    except Exception:
        pass

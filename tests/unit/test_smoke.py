"""M0 冒烟测试:验证包可安装、可导入,工具链工作正常。"""

from oncall_agent import __version__


def test_package_importable():
    assert __version__ == "0.1.0"

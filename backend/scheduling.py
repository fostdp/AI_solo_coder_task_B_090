# -*- coding: utf-8 -*-
"""
重构说明:
- 原模块名: scheduling.py
- 新模块名: fleet_scheduler.py
- 迁移日期: 2026-06-16
- 说明: 本文件为向后兼容层，所有功能已迁移至 fleet_scheduler.py
       导入符号保持不变，外部代码无需修改
"""

from fleet_scheduler import *
from fleet_scheduler import __all__

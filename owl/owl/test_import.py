# 测试导入路径
import sys
print("Python路径：")
for p in sys.path:
    print(f"  - {p}")
print("\n当前工作目录：")
import os
print(os.getcwd())
print("\n正在导入的app模块：")
from owl import app
print(f"app模块路径: {app.__file__}")

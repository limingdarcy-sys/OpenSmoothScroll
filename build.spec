# -*- mode: python ; coding: utf-8 -*-
# OpenSmoothScroll - PyInstaller 打包配置（安全精簡版）
# 只排除確定不會用到的大型第三方套件，保留所有標準庫

block_cipher = None

# 僅排除確定不需要的大型第三方套件
EXCLUDES = [
    # 科學計算（完全不需要）
    'numpy', 'scipy', 'pandas', 'matplotlib', 'sklearn', 'skimage',
    'cv2', 'opencv', 'torch', 'tensorflow', 'keras', 'sympy',
    'statsmodels', 'seaborn', 'plotly', 'bokeh',
    # 網路框架（完全不需要）
    'flask', 'django', 'fastapi', 'uvicorn', 'tornado', 'twisted',
    'aiohttp', 'httpx', 'requests', 'urllib3',
    # 資料庫（完全不需要）
    'sqlalchemy', 'pymysql', 'psycopg2', 'redis', 'pymongo',
    # 開發工具
    'pytest', 'unittest', 'lib2to3', 'setuptools', 'pip',
    # 不需要的 GUI
    'turtle', 'turtledemo', 'idlelib',
    # 不需要的環境管理
    'ensurepip', 'venv',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

# 過濾掉不需要的大型 DLL（僅排除 OpenSSL）
filtered_binaries = []
for item in a.binaries:
    name = item[0].lower()
    if 'libcrypto' in name or 'libssl' in name:
        continue
    filtered_binaries.append(item)
a.binaries = filtered_binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenSmoothScroll',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',  # 指定應用程式圖示
)

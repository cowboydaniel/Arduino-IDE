from setuptools import setup, find_packages

setup(
    name="arduino-ide-modern",
    version="0.1.0",
    description="A modern Arduino IDE with advanced debugging, intelligent code completion, and professional tools",
    author="Arduino IDE Modern Team",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.7.0",
        "pyserial>=3.5",
        "pygments>=2.18.0",
        "pyqtgraph>=0.13.0",
        "GitPython>=3.1.0",
        "requests>=2.32.0",
        "jedi>=0.19.0",
        "packaging>=24.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "arduino-ide=arduino_ide.main:main",
        ],
    },
)

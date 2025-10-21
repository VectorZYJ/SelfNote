## MacOS
pyinstaller --windowed --onefile --icon="icon.icns" --add-data="icon.icns:." src_macos.py

## Windows
pyinstaller --windowed --onefile --icon="icon.ico" --add-data="icon.ico;." src_windows.py
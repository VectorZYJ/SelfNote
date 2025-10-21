## MacOS
pyinstaller --windowed --onefile --icon="icons/icon.icns" --add-data="icons/icon.icns:." src/src_mac.py

## Windows
pyinstaller --windowed --onefile --icon="icons/icon.ico" --add-data="icons/icon.ico;." src/src_win.py
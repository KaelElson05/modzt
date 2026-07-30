<img width="1380" height="933" alt="Screenshot 2026-01-11 102521" src="https://github.com/user-attachments/assets/97c97829-bb3a-4c69-8abf-6a4ff563e594" />


# ModZT - Mod Manager/Launcher for Zoo Tycoon and Zoo Tycoon 2.
![GitHub all releases](https://img.shields.io/github/downloads/kaelelson05/modzt2/total.svg)

**ModZT** is a mod manager and launcher for *Zoo Tycoon* and *Zoo Tycoon 2* built with **Python**.  
It features threaded background tasks, automatic path detection, persistent settings, and a database for mods and bundles. 

---

<img width="1611" height="901" alt="image" src="https://github.com/user-attachments/assets/dc083eec-a100-4e05-b4c6-42e459179e66" />


Features of the mod manager include:
  - Add, enable/disable, remove mods
  - Track mod folders and load order
  - Detect and resolve file conflicts

  - Group mods into named bundles
  - Export/import bundles easily

  - Auto-detect both games in common installation paths, or user-specified path
  - Persistent settings
  - Theme and window size saved between sessions
  - XInput controller support (expanding to PlayStation controllers soon)

  - Threaded background tasks with progress bar
  - Dark/light themes


---

## Keyboard Shortcuts

- Ctrl+A - Select all mods
- Ctrl+Z - Undo last action
- Escape - Deselect all mods
- Delete - Uninstall selected mod(s)
- Enter - Enable selected mod(s)

## Building

### Requirements
- Python **3.13**
- Dependencies:
  ```bash
  pip install ttkbootstrap

### Run
python modzt.py

### Build
pyinstaller --onefile --noconsole --icon=assets/modzt.ico modzt.py

## Notice
If you run into any bugs, please report them on Github Issues!

This project is not affiliated with Microsoft, Xbox Game Studios, or Blue Fang Games.

---

## License

```text
MIT License

Copyright (c) 2026 Songstorm Studios

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.



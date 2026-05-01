cd /Users/sam/python/xtouch
source .venv/bin/activate

if [ "$1" == "no_menu" ]; then
	/usr/bin/env python3 ctrl_mix/app.py
else
	/usr/bin/env python3 menu_bar.py
fi

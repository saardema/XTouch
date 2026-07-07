
cd ~/python/ctrl_mix
source .venv/bin/activate

if [ "$1" = "no_menu" ]; then
	exec python3 ctrl_mix/app.py
else
	exec python menu_bar.py
fi

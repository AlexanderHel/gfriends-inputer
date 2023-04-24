	# If you can't run this script, please execute the following command in PowerShell.
	# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
	
	# bugfix：set submodules find path
	$Env:PYTHONPATH=$pwd.path
	$PYTHONPATH=$pwd.path
	mkdir build
	mkdir __pycache__
	
	pyinstaller --collect-submodules "Lib" `
		--collect-all "opencv-python" `
		--collect-data "alive_progress" `
		--collect-data "aip" `
		--add-data "config.ini;." `
		--onefile "Gfriends Inputer.py"
	
	
	rmdir -Recurse -Force build
	rmdir -Recurse -Force __pycache__
	rmdir -Recurse -Force "Gfriends Inputer.spec"
	
	echo "[Make]Finish"
	pause
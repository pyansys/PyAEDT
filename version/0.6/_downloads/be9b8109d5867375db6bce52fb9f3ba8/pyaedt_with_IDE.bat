@echo off
set current_dir=%~dp0
setlocal enabledelayedexpansion
set argCount=0
for %%x in (%*) do (
   set /a argCount+=1
   set "argVec[!argCount!]=%%~x"
)

set args=%1 %2 %3 %4 %5 %6
set update_pyaedt=n
set install_pyaedt=n
set install_spyder=n

for /L %%i in (1,1,%argCount%) do (
	if [!argVec[%%i]!]==[-f] set install_pyaedt=y
	if [!argVec[%%i]!]==[--force-install] set install_pyaedt=y
	if [!argVec[%%i]!]==[-u] set update_pyaedt=y
	if [!argVec[%%i]!]==[--update] set update_pyaedt=y
	if [!argVec[%%i]!]==[-p] (
		set /A usepython=%%i+1
	)
	if [!argVec[%%i]!]==[-w] (
		set /A usewheel=%%i+1
	)
	if [!argVec[%%i]!]==[-s] set install_spyder=y

)
if NOT [%usepython%]==[] (
	set pythonpyaedt="!argVec[%usepython%]!"
	echo Python Path has been specified.
)
if NOT [%usewheel%]==[] (
	set wheelpyaedt="!argVec[%usewheel%]!"
	if [%usepython%]==[] (
		echo ----------------------------------------------------------------------
		echo WheelHouse has been specified. Make sure you are using version 3_7.
		echo ----------------------------------------------------------------------

	) ELSE (
	echo ----------------------------------------------------------------------------------------------
	echo WheelHouse has been spefified. Make sure you are using the same version of Python interpreter.
	echo ----------------------------------------------------------------------------------------------

	)
)


set env_vars=ANSYSEM_ROOT232 ANSYSEM_ROOT231 ANSYSEM_ROOT222 ANSYSEM_ROOT221 ANSYSEM_ROOT212
set /A choice_index=1
for %%c in (%env_vars%) do (
	set env_var_name=%%c
	if defined !env_var_name! (
		set root_var[!choice_index!]=!env_var_name!
		set version=!env_var_name:ANSYSEM_ROOT=!
		set versions[!choice_index!]=!version!
		set version_pretty=20!version:~0,2! R!version:~2,1!
		echo [!choice_index!] !version_pretty!
		set /A choice_index=!choice_index!+1
	)
)
REM If choice_index wasn't incremented then it means none of the variables are installed
if [%choice_index%]==1 (
	echo AEDT 2021 R2 or later must be installed.
	pause
	EXIT /B
)

set /p chosen_index="Select Version to Install PyAEDT for (number in bracket): "
if [%chosen_index%] == [] set chosen_index=1

set chosen_root=!root_var[%chosen_index%]!
set version=!versions[%chosen_index%]!
echo Selected %version% at !%chosen_root%!.

set aedt_path=potato
if [%specified_python%]==[y] (
	aedt_path=!argVec[%python_path_index%]!
) else (
	set aedt_path=!%chosen_root%!\commonfiles\CPython\3_7\winx64\Release\python
	echo Built-in Python is !aedt_path!.
)
set aedt_path=!aedt_path:"=!

echo %aedt_path%



set pyaedt_install_dir=%APPDATA%\pyaedt_env_ide\v%version%
echo %pyaedt_install_dir%
if NOT exist "%pyaedt_install_dir%" (
	set install_pyaedt=y
)
setlocal enableDelayedExpansion

if [%install_pyaedt%]==[y] (
	if exist "%pyaedt_install_dir%" (
		echo Removing existing PyAEDT environment.
		@RD /S /Q "%pyaedt_install_dir%"
	)
	echo Installing PyAEDT environment in "%pyaedt_install_dir%".

	cd "%APPDATA%"

	if [%pythonpyaedt%] == [] (
	"%aedt_path%\python.exe" -m venv "%pyaedt_install_dir%" --system-site-packages
	) ELSE (
		"%pythonpyaedt%\python.exe" -m venv "%pyaedt_install_dir%"
	)
	call "%pyaedt_install_dir%\Scripts\activate.bat"
	if NOT [%wheelpyaedt%]==[] (
		echo Installing PyAEDT from local wheels %arg1%.
		pip install --no-cache-dir --no-index --find-links=%wheelpyaedt% pyaedt
	) ELSE (
		IF EXIST %current_dir%.git (
			echo Installing PyAEDT from local clone "%current_dir%".
		) ELSE (
			echo Installing PyAEDT from pip.
		)

		python -m pip install --upgrade pip
		pip --default-timeout=1000 install wheel

		IF EXIST %current_dir%.git (
			pushd %current_dir%
			pip install .
			popd
		) ELSE (
			pip --default-timeout=1000 install pyaedt
		)

		pip --default-timeout=1000 install jupyterlab -I
		if [%install_spyder%]==[y] pip --default-timeout=1000 install spyder
		pip --default-timeout=1000 install ipython -U
		pip --default-timeout=1000 install ipyvtklink
	)
	if [%pythonpyaedt%]==[] (
		if %version% geq 231 pip uninstall -y pywin32
	)

	call python "%pyaedt_install_dir%\Lib\site-packages\pyaedt\misc\aedtlib_personalib_install.py" --version=%version%
)
if [%update_pyaedt%]==[y] (
	echo Updating PyAEDT.
	"%pyaedt_install_dir%\Scripts\pip" install pythonnet  -U
	"%pyaedt_install_dir%\Scripts\pip" install pyaedt --no-deps -U
	call "%pyaedt_install_dir%\Scripts\python" "%pyaedt_install_dir%\Lib\site-packages\pyaedt\misc\aedtlib_personalib_install.py" --version=%version%

)


cmd /k "%pyaedt_install_dir%\Scripts\activate.bat"

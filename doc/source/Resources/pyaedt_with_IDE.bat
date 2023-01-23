@echo off
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
	    echo WheelHouse has been spefified. Make sure you are using version 3_7
	 	echo ----------------------------------------------------------------------

	) ELSE (
	echo ----------------------------------------------------------------------------------------------
	echo WheelHouse has been spefified. Make sure you are using the same version of Python interpreter.
	echo ----------------------------------------------------------------------------------------------

	)
)

if NOT exist "%APPDATA%\pyaedt_env_ide\" (
    set install_pyaedt=y
)

set env_vars=ANSYSEM_ROOT231 ANSYSEM_ROOT231 ANSYSEM_ROOT222 ANSYSEM_ROOT221 ANSYSEM_ROOT212
setlocal enableextensions enabledelayedexpansion
set latest_env_var_present=
for %%c in (%env_vars%) do (
    set env_var_name=%%c
    if defined !env_var_name! (
        set latest_env_var_present=!env_var_name!
        GOTO :FOUND_ENV_VAR
    )
)
endlocal
echo AEDT 2021 R2 or later must be installed.
pause
EXIT /B

:FOUND_ENV_VAR
endlocal && set aedt_var=%latest_env_var_present%
set version=%aedt_var:ANSYSEM_ROOT=%
set version_pretty=20%version:~0,2% R%version:~2,1%
set cmd=call echo %%%aedt_var%%%
for /f "delims=" %%i in ('%cmd%') do set aedt_path=%%i
echo Found AEDT %version_pretty% at %aedt_path%

set /p run=Python or Jupyter?(0=InstallOnly, 1=Jupyter, 2=Console, 3=Spyder(pip only))
if [%run%] == [] set run=0
if %run%==3 set install_spyder=y

setlocal enableDelayedExpansion

if [%install_pyaedt%]==[y] (
    if exist "%APPDATA%\pyaedt_env_ide\" (
        echo Removing existing Pyaedt Environment
        @RD /S /Q "%APPDATA%\pyaedt_env_ide\"
    )
    echo Installing Pyaedt Environment in "%APPDATA%\pyaedt_env_ide\"

    cd "%APPDATA%"
    if [%pythonpyaedt%] == [] (
    "%aedt_path%\commonfiles\CPython\3_7\winx64\Release\python\python.exe" -m venv "%APPDATA%\pyaedt_env_ide"
    ) ELSE (
        "%pythonpyaedt%\python.exe" -m venv "%APPDATA%\pyaedt_env_ide"
    )
    if NOT [%wheelpyaedt%]==[] (
        echo Installing Pyaedt from local wheels %arg1%
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install --no-cache-dir --no-index --find-links=%wheelpyaedt% pyaedt
    ) ELSE (
        echo Installing Pyaedt from pip
        "%APPDATA%\pyaedt_env_ide\Scripts\python.exe" -m pip install --upgrade pip
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install wheel
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install pyaedt
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install jupyterlab
        if [%install_spyder%]==[y] "%APPDATA%\pyaedt_env_ide\Scripts\pip" install spyder
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install ipython -U
        "%APPDATA%\pyaedt_env_ide\Scripts\pip" install ipyvtklink
    )
    call "%APPDATA%\pyaedt_env_ide\Scripts\python" "%APPDATA%\pyaedt_env_ide\Lib\site-packages\pyaedt\misc\aedtlib_personalib_install.py" %aedt_var%
)
if [%update_pyaedt%]==[y] (
    echo Updating Pyaedt
    "%APPDATA%\pyaedt_env_ide\Scripts\pip" install pyaedt -U
)
if %run%==1 (
     echo Launching Jupyter Lab
    "%APPDATA%\pyaedt_env_ide\Scripts\jupyter.exe" lab
) else ( if %run%==3 (
    echo Launching Spyder
    "%APPDATA%\pyaedt_env_ide\Scripts\spyder.exe"
    ) else ( if %run%==2 (
    "%APPDATA%\pyaedt_env_ide\Scripts\ipython.exe"
    ) else (
	echo Activating Pyaedt environment
	cmd /k "%APPDATA%\pyaedt_env_ide\Scripts\activate.bat"
	)
    )
)

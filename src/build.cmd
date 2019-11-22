@echo off

rem ############################################################################
if exist "dist" (rmdir /S /Q dist)
if exist "build" (rmdir /S /Q build)

REM mkdir build_output
REM IF %ERRORLEVEL% NEQ 0 (
REM     echo "Failed creating build_output dir"
REM     echo %ERRORLEVEL%
REM     GOTO FAIL
REM )
REM mkdir build_output\bin
REM IF %ERRORLEVEL% NEQ 0 (
REM     echo "Failed creating build_output\bin dir"
REM     echo %ERRORLEVEL%
REM     GOTO FAIL
REM )
REM mkdir build_output\data
REM IF %ERRORLEVEL% NEQ 0 (
REM     echo "Failed creating build_output\data dir"
REM     echo %ERRORLEVEL%
REM     GOTO FAIL
REM )
REM mkdir build_output\out
REM IF %ERRORLEVEL% NEQ 0 (
REM     echo "Failed creating build_output\out dir"
REM     echo %ERRORLEVEL%
REM     GOTO FAIL
REM )

rem ############################################################################
echo Building exe
pyinstaller gitup.py
IF %ERRORLEVEL% NEQ 0 (
    echo %ERRORLEVEL%
    GOTO FAIL
)
REM copy dist\cxptest_gui.exe build_output\bin\cxptest_gui.exe
REM IF %ERRORLEVEL% NEQ 0 (
REM     echo %ERRORLEVEL%
REM     GOTO FAIL
REM )

:DO_COPY

rem ############################################################################
echo Copying key file
copy  .\user.config .\dist\gitup\user.config
IF %ERRORLEVEL% NEQ 0 (
    echo %ERRORLEVEL%
    GOTO FAIL
)

rem ############################################################################
:PASS
echo PASS
GOTO :DONE

:FAIL
echo !!!!!!!! Building SSG Failed !!!!!!!!
GOTO DONE

:DONE
echo Cleaning up
rmdir /q /s build
REM rmdir /q /s dist
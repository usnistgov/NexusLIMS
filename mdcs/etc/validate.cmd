@ECHO off
set junxhome=%~dp0
set junxjar=%junxhome%\lib\junx.jar
set cp=%junxjar%

java -classpath %cp% ncsa.xml.validation.Validate %*

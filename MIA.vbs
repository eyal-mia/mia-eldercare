' MIA - silent launcher.
' Double-click this file to start MIA. Nothing appears on screen; the app
' starts in the background and the browser opens automatically once it is
' ready. To stop MIA, end the "python.exe" (Streamlit) task, or just re-run
' this file (it frees the port and restarts).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = scriptDir
' window style 0 = hidden, False = do not wait
sh.Run "cmd /c " & """" & scriptDir & "\run.bat" & """", 0, False

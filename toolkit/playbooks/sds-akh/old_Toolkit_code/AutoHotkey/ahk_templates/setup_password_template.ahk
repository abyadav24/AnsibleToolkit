; Include the INI library
;#Include <IniFile>

; Define the path to the INI file
iniFilePath := ""

; [Conf] Default password
setup_default_pw := "hsds-setup"
; [INI-file] Read variables
IniRead, host, %1%, ilo, host
IniRead, user, %1%, ilo, user
IniRead, pw, %1%, ilo, pw
IniRead, setup_pw, %1%, node, setup_pw
; irc_open
irc_open (host user pw)
    Run "C:\Program Files\Google\Chrome\Application\chrome.exe" "-new-window" "https://%host%/irc.html"
    WinWaitActive iLO
    Sleep 10 * 1000
   	Send %user%
	Send {Tab}
    Send %pw%{Enter}
    Sleep 10 * 1000

; [iLO] Open iLO remote console
;irc_open(ilo_host, ilo_user, ilo_pw)
; [Console] Log in
Send, {Down}
Send, {Enter}
Sleep, 5 * 1000
; [Console] Password
Send, %setup_default_pw%{Enter}
Sleep, 5 * 1000
; [Console] Current password
Send, %setup_default_pw%{Enter}
Sleep, 5 * 1000
; [Console] New password
Send, %setup_pw%{Enter}
Sleep, 5 * 1000
; [Console] Retype new password
Send, %setup_pw%{Enter}
Sleep, 5 * 1000
; [Console] Logout
Send, {Down 6}
Send, {Enter}
Sleep, 5 * 1000
; [iLO] Close iLO remote console
irc_close()
{
    WinClose iLO
}
irc_close()
Exit
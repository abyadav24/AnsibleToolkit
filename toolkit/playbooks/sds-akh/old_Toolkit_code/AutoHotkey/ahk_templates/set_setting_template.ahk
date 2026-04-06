; Include the INI library
;#Include <IniFile>

; Define the path to the INI file
iniFilePath := ""

; [INI-file] Read variables
IniRead, ilo_host, %1%, ilo, host
IniRead, ilo_user, %1%, ilo, user
IniRead, ilo_pw, %1%, ilo, pw
IniRead, setup_pw, %1%, node, setup_pw
IniRead, hostname, %1%, node, hostname
IniRead, ipv4address, %1%, controlnw, ipv4address
IniRead, subnetmask, %1%, controlnw, subnetmask
IniRead, mtu, %1%, controlnw, mtu
IniRead, route_count, %1%, controlnw, route_count
IniRead, route_destination1, %1%, controlnw, route_destination1
IniRead, route_gateway1, %1%, controlnw, route_gateway1
;route_destinations := []
;route_gateways := []
;Loop, %route_count%
;{
;    IniRead, route_destination, %1%, controlnw, route_destination%A_Index%
;    IniRead, route_gateway, %1%, controlnw, route_gateway%A_Index%
;    route_destinations.Push(route_destination)
;    route_gateways.Push(route_gateway)
;}
; irc_open
irc_open (ilo_host ilo_user ilo_pw)
    Run "C:\Program Files\Google\Chrome\Application\chrome.exe" "-new-window" "https://%ilo_host%/irc.html"
    WinWaitActive iLO
	Sleep, 5 * 1000
   	Send %ilo_user%
	Send {Tab}
    Send %ilo_pw%{Enter}
    Sleep, 5 * 1000

; [iLO] Open iLO remote console
;irc_open(ilo_host, ilo_user, ilo_pw)

; [Console] Log in
Send, {Down}
Send, {Enter}
Sleep, 5 * 1000

; [Console] Password
Send, %setup_pw%{Enter}
Sleep, 5 * 1000
; [Console] Set setting
Send, {Enter}
Sleep, 5 * 1000

; [Console] Storage node name
Send, {Enter}
Sleep, 5 * 1000
Send, %hostname%{Enter}
Sleep, 5 * 1000
Send, {Down 2}
Send, {Enter}
Sleep, 5 * 1000
Send, {Enter}
Sleep, 5 * 1000
; [Console] IP address
Send, {Enter}
Sleep, 5 * 1000
Send, %ipv4address%
Sleep, 5 * 1000
Send, {Down 2}
Sleep, 5 * 1000
; [Console] Subnet mask
Send, {Enter}
Sleep, 5 * 1000
Send, %subnetmask%{Enter}
Sleep, 5 * 1000
; [Console] MTU
Send, {Down}
Send, {Enter}
Sleep, 5 * 1000
Send, %mtu%{Enter}
Sleep, 5 * 1000

; [Console] Routing table
Send, {Down 2}
Send, {Enter}
Sleep, 5 * 1000
Send, %route_count%{Enter}
Sleep, 5 * 1000
; [Console] OK
Send, {Down 3}
Send, {Enter}
Sleep, 5 * 1000

; [Console] Route
; [Console] Destination
Send, {Enter}
Sleep, 5 * 1000
Send, %route_destination1%{Enter}
Sleep, 5 * 1000

; [Console] Gateway
Send, {Down}
Send, {Enter}
Sleep, 5 * 1000
Send, %route_gateway1%{Enter}
Sleep, 5 * 1000
; [Console] OK
Send, {Down 3}
Send, {Enter}
Sleep, 5 * 1000

; [Console] Next
Send, {Enter}
Sleep, 5 * 1000

; [Console] Submit
Send, {Enter}
Sleep, 5 * 1000
; [Console] OK
Send, {Down}
Send, {Enter}
Sleep, 15 * 1000
; [iLO] Close iLO remote console
irc_close()
{
    WinClose iLO
}
irc_close()
Exit


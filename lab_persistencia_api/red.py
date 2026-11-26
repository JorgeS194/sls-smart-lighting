import network
from time import sleep

def conectar_wifi(ssid="Wokwi-GUEST", clave=""):
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True
    wlan.active(True)
    wlan.connect(ssid, clave)
    for _ in range(60):
        if wlan.isconnected():
            print("Wi-Fi OK. IP:", wlan.ifconfig()[0])
            return True
        sleep(0.5)
    print("Sin Wi-Fi")
    return False

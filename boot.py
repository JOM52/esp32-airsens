# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(esp.LOG_DEBUG) #'LOG_DEBUG', 'LOG_ERROR', 'LOG_INFO', 'LOG_NONE', 'LOG_VERBOSE', 'LOG_WARNING'
# import webrepl
# webrepl.start(password="mablonde")
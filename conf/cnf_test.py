conf = {}

conf['mqtt']={}
conf['mqtt']['broker_id'] = '192.168.1.123'
conf['mqtt']['topic'] = 'airsens_test'

conf['wifi'] = {}
conf['wifi']['wan'] = 'jmb-home'
conf['wifi']['pa'] = 'lu-mba01'

conf['central'] = {}
conf['central']['name'] = 'jmb-airsens-ttgo_01'
conf['central']['advertise_interval_ms'] = '250'

conf['sensor'] = {}
conf['sensor']['type'] = 'BME680'
conf['sensor']['uc'] = 'WROOM'
conf['sensor']['id'] = 'w9'
conf['sensor']['t_deepsleep_ms'] = '15000'
conf['sensor']['ubat_100'] = '4.2'
conf['sensor']['ubat_0'] = '3.5'
conf['sensor']['r1'] = '100000'
conf['sensor']['r2'] = '33000'

print(conf)

f = open('cnf_test.txt','w')
for key, value in conf.items():
    f.write('%s:%s\n' % (key, value))
    
    
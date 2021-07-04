import signal
import sys
import logging
from sh import cat, ip, egrep, cut, sleep, ping, neofetch, ifconfig, nomad, sudo, consul, sed

signal.signal(signal.SIGINT, signal.default_int_handler)
logging.basicConfig(level=logging.DEBUG, filename='/home/max/starty.log', format='%(asctime)s %(levelname)s:%(message)s')
server = nomad.agent.bake('-config', '/etc/nomad.d/nomad.hcl', '-config', '/etc/nomad.d/server/server.hcl')
client = nomad.agent.bake('-config', '/etc/nomad.d/nomad.hcl', '-config', '/etc/nomad.d/client/client.hcl')


print("""
 __  __            _                           
|  \/  | __ ___  _(_)_ __ ___  _   _ _ __ ___  
| |\/| |/ _` \ \/ / | '_ ` _ \| | | | '_ ` _ \ 
| |  | | (_| |>  <| | | | | | | |_| | | | | | |
|_|  |_|\__,_/_/\_\_|_| |_| |_|\__,_|_| |_| |_|                                          
 _____  __  __ _      _                       
| ____|/ _|/ _(_) ___(_) ___ _ __   ___ _   _ 
|  _| | |_| |_| |/ __| |/ _ \ '_ \ / __| | | |
| |___|  _|  _| | (__| |  __/ | | | (__| |_| |
|_____|_| |_| |_|\___|_|\___|_| |_|\___|\__, |
                                        |___/ 
""")

logging.debug("Starting script...")


def checkConn(ip):
    logging.debug("Checking ip...")
    for i in range(5):
        try:
            ping('-c', '1', ip, _fg=True)
            return True
        except:
            sleep('5')
    return False


def compareIp():
    logging.debug("Comparing ip...")
    #ip a s eth0 | egrep -o 'inet [0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | cut -d' ' -f2
    curIp = str(cut(egrep(ip('a', 's', 'eth0'), '-o', 'inet [0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'), '-d', ' ', '-f2')).strip()
    masterNetworkCfg = cat('/etc/systemd/network/000-master.network').split('\n')
    for i in range(len(masterNetworkCfg)):
        if masterNetworkCfg[i] == '[Address]':
            masterIp = masterNetworkCfg[i+1].split('=')[1].strip()
            logging.debug("Master ip found, breaking the loop...")
            break 
    if curIp==masterIp:
        logging.debug("Master IP == cur IP...")
        return True, masterIp
    logging.debug("Master IP != cur IP...")
    return False, masterIp


while True:
    try:
        check, masterIp = compareIp()
        if check:
            logging.debug("Starting server...")
            with sudo:
                sed('-i', f's/#advertise_addr = "127.0.0.1"/advertise_addr = "{masterIp}"/', '/etc/consul.d/consul.hcl')
                consul('agent', "-config-file", "/etc/consul.d/consul.hcl", "-log-file", "/home/max/", _bg=True)
                #changing consul ip in nomad cfg
                sed('-i', f's/127.0.0.1/{masterIp}/', '/etc/nomad.d/nomad.hcl')
                server(_out=sys.stdout)
                sleep(10)
        else:
            check = checkConn(masterIp)
            if check:
                with sudo:
                    logging.debug("Starting client...")
                    #changing consul ip
                    sed('-i', f's/127.0.0.1/{masterIp}/', '/etc/nomad.d/nomad.hcl')
                    client('-servers', masterIp, _out=sys.stdout)
                    sleep(10)
            else:
                logging.debug("Something wrong...")
                print('Something wrong...')
                print('Try to start manualy...')
                print('Press alt+f2 to start inreractive prompt...')
                print('Here soe envs for you:')
                neofetch(_fg=True)
                ifconfig(_fg=True)
                sleep(120, _fg=True)
    except Exception as e:
        logging.exception('Here some shit happend:', e)
        sleep(10)

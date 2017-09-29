import time
import csv
import codecs
import HTML
from zabbix.api import ZabbixAPI
from datetime import timedelta
from datetime import datetime
from itertools import repeat

def zabbix_dane_tabelka(IP):
    hID = []
    dane_z_zabbix = {'hostname':{}, 'lan':{}, 'loop':{}, 'last_clock_loop':{}}
    _ = {}

    zapi = ZabbixAPI(url='https://pit-zabbix.net.pp', user='***', password='***')
    result = zapi.do_request('hostinterface.get', {'filter': {'ip':IP}, 'limit':'100'})
    result = result['result']

    hID.extend(repeat('', len(IP)))

    for i in enumerate(result):
        hID[IP.index(i[1]['ip'])] = i[1]['hostid']

    result = zapi.do_request('host.get', {'filter': {'hostid':hID}, 'limit':'100'})
    result = result['result']

    for e in enumerate(hID):
        for x in enumerate(hID):
            if result[x[0]].get('hostid', '') == e[1]:
                dane_z_zabbix['hostname'][hID[e[0]]] = 'Netia' if result[x[0]]['name'].find('Netia') != -1 else 'T-Mobile'
                break

    result = zapi.do_request('item.get', {'filter': {'hostid':hID, 'value_type':'3', 'name':['Ping Loopback (ICMP Echo) -{HOST.DNS}', 'Ping LAN (ICMP Echo)','Ping Loopback (ICMP Echo)']}, 'limit':'100'})
    result = result['result']

    for e in enumerate(result):
        for x in enumerate(hID):
            if result[e[0]]['hostid'] == x[1] and result[e[0]]['name'] == 'Ping LAN (ICMP Echo)':
                dane_z_zabbix['lan'][x[1]] = result[e[0]].get('lastvalue', '')
                break
            if result[e[0]]['hostid'] == x[1] and ((result[e[0]]['name'] == 'Ping Loopback (ICMP Echo) -{HOST.DNS}') or (result[e[0]]['name'] == 'Ping Loopback (ICMP Echo)')):
                dane_z_zabbix['loop'][x[1]] = result[e[0]].get('lastvalue', -1)
                result3 = zapi.do_request('trigger.get', {'filter': {'hostid':x[1], 'description':'OUT,T-DUIiS:Ping-Brak komunikacji z adresem LAN oraz Loopback (5m) -Niezalezny od EJP'}, 'limit':'1'})
                dane_z_zabbix['last_clock_loop'][x[1]] = result3['result'][0].get('lastchange', '')
                break

    del result, result3
    return hID, dane_z_zabbix

def raportWAN():
    reader = csv.reader(codecs.open('query.csv', 'rU', 'utf-16-le'))
    header_temp, temp_table = [], []
     
    for row in iter(reader):
        temp_table.append(row[0:2] + row[5:11] + ['']*3)

    del reader

    header_temp=temp_table[0][0:8] + ['Operator wg Zabbix', 'Status Zabbix<br>(Lan+Loopback)', 'GSM<br>(Lan vs Loopback)']
    header_temp[1] = 'Data rejestracji<br>Incydentu WAN'
    header_temp[5] = 'Data przekazania<br>zgłoszenia do Netii'
    header_temp[6] = 'Numer zgłoszenia<br>awarii w Netii'
    
    del temp_table[0]

    temp_czas = ''
    temp_IP = [temp_table[i[0]][2] for i in enumerate(temp_table)]
    value = zabbix_dane_tabelka(temp_IP)

    for i, t in enumerate(temp_table):
        t[0] = HTML.link(t[0], 'https://servicedesk.net.pp/SD_Operator.WebAccess/wd/search/search.rails?s=' + t[0])
        t[2] = HTML.link(t[2], 'https://pit-zabbix.net.pp/latest.php?filter_set=1&hostids[]=' + value[0][i]) + '&nbsp' + HTML.link('(TR)', 'https://pit-zabbix.net.pp/search.php?search=' + t[2])
        try:
            t[8] = value[1]['hostname'][value[0][i]]
        except:
            pass
        
        try:
            temp_czas = datetime.fromtimestamp(int(value[1]['last_clock_loop'][value[0][i]])).strftime('%Y-%m-%d %H:%M:%S')
        except:
            temp_czas = ''
            pass

        delta = datetime.now() - datetime.fromtimestamp(int(value[1]['last_clock_loop'][value[0][i]]))
        if value[1]['lan'].get(value[0][i], '') == '1':
            t[9] = '<font color="green"><b>OK</b><br>(Status od: {})<br><b>{} dni</b></font>'.format(temp_czas, delta.days)
        else:
            t[9] = '<font color="red"><b>DOWN</b><br>(Status od: {})<br><b>{} dni</b></font>'.format(temp_czas, delta.days)

        if value[1]['loop'].get(value[0][i], '') == '0' and value[1]['lan'].get(value[0][i], '') == '1':
            t[10] = 'Prawdopodobny modem GSM<br>(Loop=Down, LAN=OK)'

    with open('query.html', 'w+', encoding='utf-8') as html_file:
        html_file.write('<script src="sorttable.js"></script>')
        html_file.write('<link type="text/css" rel="stylesheet" href="zab.css">')
        html_file.write('<h1>Plik query.csv załadowano.</h1><h2><br>Import zakończony</h2>')
        html_file.write(HTML.table(temp_table, header_row=header_temp, attribs={'class':'sortable'}))

raportWAN()

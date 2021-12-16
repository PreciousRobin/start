import mysql.connector
import random
import asyncio
from pythonping import ping

HOST = ''
PORT = 5001

master_ip = '10.84.15.10'
slave_ips = ['10.84.15.11', '10.84.15.12']

mode = 'direct hit'

# MySQL - open connections and slaves
while True:
    try:
        master_connection = mysql.connector.connect(user='proxy', password='password', host=master_ip, database='project', connection_timeout=60)
        break
    except mysql.connector.Error as err:
        pass

slave_connections = []

for slave_ip in slave_ips:
    while True:
        try:
            slave_connections.append(mysql.connector.connect(user='proxy', password='password', host=slave_ip, database='project', connection_timeout=60))
            break
        except mysql.connector.Error as err:
            pass

connections = slave_connections + [master_connection]

def process_request(request):
    global mode
    if request == 'read':
        connection = select_connection()
        read_operation(connection)
        return 'Read operation completed'

    if request == 'direct hit':
        mode = 'direct hit'
        return 'Proxy mode changed to \'direct hit\''
    if request == 'random':
        mode = 'random'
        return 'Proxy mode changed to \'random\''
    if request == 'ping':
        mode = 'ping'
        return 'Proxy mode changed to \'ping\''

    if request == 'print':
        return mode

    return 'Request not recognized'

def select_connection():
    if mode == 'direct hit':
        return master_connection
    if mode == 'random':
        return random.choice(connections)
    if mode == 'ping':
        responses = {}

        for con in connections:
            response = ping(con.server_host)
            responses[con.server_host]=response.rtt_avg

        fastest_host = min(responses, key=responses.get)

        con = list(filter(lambda connection: connection.server_host == fastest_host, connections))[0]
        return con

    return master_connection

def read_operation(connection):
    select_query = "SELECT user FROM mysql.user"
    with connection.cursor() as cursor:
        cursor.execute(select_query)
        result = cursor.fetchall()
        for row in result:
            print(row)

async def handle_requests(reader, writer):
    while True:
        data = await reader.read(1024)

        if not data:
            break

        request = data.decode()

        response = process_request(request)

        data = response.encode()
        writer.write(data)
        await writer.drain()

    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(
        handle_requests, '', PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

asyncio.run(main())
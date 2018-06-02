import asyncio
import json
import os
import struct
import sys
import time
from plexapi.myplex import MyPlexAccount

######################################Credits####################################
# JonnyWong16 for beeing himself												#
# JonnyWong16 for writing the original script									#
# Script https://gist.github.com/JonnyWong16/0d8ec676d3d8416f562b63af140c09e7	#
# Me for knowing to google														#
#################################################################################


### EDIT SETTINGS ###

PLEX_SERVER = "SERVER_NAME"
PLEX_USERNAME = 'PLEX_USERNAME'
PLEX_PASSWORD = 'PLEX_PASSWORD'
PLEX_HOME_USER_OVERRIDE = ''  # Username override if you are using a Managed User logged in using the admin account

### OPTIONAL SETTINGS ###

DISCORD_CLIENT_ID = '409127705980829707'

### CODE BELOW ###

PREVIOUS_STATE = None
PREVIOUS_SESSION_KEY = None
PREVIOUS_RATING_KEY = None


class DiscordRPC:
    def __init__(self, client_id):
        if sys.platform == 'linux' or sys.platform == 'darwin':
            self.ipc_path = (os.environ.get('XDG_RUNTIME_DIR', None) or os.environ.get('TMPDIR', None) or
                             os.environ.get('TMP', None) or os.environ.get('TEMP', None) or '/tmp') + '/discord-ipc-0'
            self.loop = asyncio.get_event_loop()
        elif sys.platform == 'win32':
            self.ipc_path = r'\\?\pipe\discord-ipc-0'
            self.loop = asyncio.ProactorEventLoop()
        self.sock_reader: asyncio.StreamReader = None
        self.sock_writer: asyncio.StreamWriter = None
        self.client_id = client_id

    async def read_output(self):
        print("reading output")
        data = await self.sock_reader.read(1024)
        code, length = struct.unpack('<ii', data[:8])
        print(f'OP Code: {code}; Length: {length}\nResponse:\n{json.loads(data[8:].decode("utf-8"))}\n')

    def send_data(self, op: int, payload: dict):
        payload = json.dumps(payload)
        data = self.sock_writer.write(struct.pack('<ii', op, len(payload)) + payload.encode('utf-8'))

    async def handshake(self):
        if sys.platform == 'linux' or sys.platform == 'darwin':
            self.sock_reader, self.sock_writer = await asyncio.open_unix_connection(self.ipc_path, loop=self.loop)
        elif sys.platform == 'win32':
            self.sock_reader = asyncio.StreamReader(loop=self.loop)
            reader_protocol = asyncio.StreamReaderProtocol(self.sock_reader, loop=self.loop)
            self.sock_writer, _ = await self.loop.create_pipe_connection(lambda: reader_protocol, self.ipc_path)
        self.send_data(0, {'v': 1, 'client_id': self.client_id})
        data = await self.sock_reader.read(1024)
        code, length = struct.unpack('<ii', data[:8])
        print(f'OP Code: {code}; Length: {length}\nResponse:\n{json.loads(data[8:].decode("utf-8"))}\n')

    def send_rich_presence(self, activity):
        current_time = time.time()
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "activity": activity,
                "pid": os.getpid()
            },
            "nonce": f'{current_time:.20f}'
        }
        print("sending data")
        sent = self.send_data(1, payload)
        self.loop.run_until_complete(self.read_output())

    def close(self):
        self.sock_writer.close()
        self.loop.close()

    def start(self):
        self.loop.run_until_complete(self.handshake())

    def clear(self,pid=os.getpid()):
        current_time = time.time()
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": pid,
                "activity": None
            },
            "nonce": '{:.20f}'.format(current_time)
        }
        self.send_data(1, payload)
        return self.loop.run_until_complete(self.read_output())

def clear_rich_presence():
    # The Discord rich presence payload
    activity = {
        'details': 'Nothing is playing',
        'assets': {
            'large_text': 'Plex',
            'large_image': 'plex_logo',
        },
    }

    # Set Discord rich presence
    #RPC.clear()
    RPC.send_rich_presence(activity)


def process_alert(data):
    if data.get('type') == 'playing':
        session_data = data.get('PlaySessionStateNotification', [])[0]
        state = session_data.get('state', 'stopped')
        session_key = session_data.get('sessionKey', None)
        rating_key = session_data.get('ratingKey', None)
        view_offset = session_data.get('viewOffset', 0)

        if session_key and session_key.isdigit():
            session_key = int(session_key)
        else:
            return

        if rating_key and rating_key.isdigit():
            rating_key = int(rating_key)
        else:
            return

        global PREVIOUS_STATE
        global PREVIOUS_SESSION_KEY
        global PREVIOUS_RATING_KEY

        # Clear the rich presence if the session is stopped
        if state == 'stopped' and PREVIOUS_SESSION_KEY == session_key and PREVIOUS_RATING_KEY == rating_key:
            PREVIOUS_STATE = None
            PREVIOUS_SESSION_KEY = None
            PREVIOUS_RATING_KEY = None
            RPC.clear()
            #clear_rich_presence()
            return
        elif state == 'stopped':
            return

        # If Plex server admin, make sure the alert is for the current user
        if plex_admin:
            for session in plex.sessions():
                if session.sessionKey == session_key:
                    if PLEX_HOME_USER_OVERRIDE and session.usernames[0].lower() == PLEX_HOME_USER_OVERRIDE.lower():
                        break
                    if not PLEX_HOME_USER_OVERRIDE and session.usernames[0].lower() == PLEX_USERNAME.lower():
                        break
                    else:
                        return

        # Skip if the session key and state hasn't changed
        if PREVIOUS_STATE == state and PREVIOUS_SESSION_KEY == session_key and PREVIOUS_RATING_KEY == rating_key:
            return

        # Save the session
        PREVIOUS_STATE = state
        PREVIOUS_SESSION_KEY = session_key
        PREVIOUS_RATING_KEY = rating_key
        metadata = plex.fetchItem(rating_key)

        # Format Discord rich presence text based on media type
        media_type = metadata.type

        if media_type == 'movie':
            title = metadata.title
            subtitle = str(metadata.year)
        elif media_type == 'episode':
            title = f'{metadata.grandparentTitle} - {metadata.title}'
            subtitle = f'S{metadata.parentIndex} · E{metadata.index}'
        elif media_type == 'track':
            title = f'{metadata.grandparentTitle} - {metadata.title}'
            subtitle = metadata.parentTitle
        else:
            return

        # The Discord rich presence payload
        activity = {
            'details': title,
            'state': subtitle,
            'assets': {
                'large_text': 'Plex',
                'large_image': 'plex_logo',
                'small_text': state.capitalize(),
                'small_image': state
            },
        }

        # Set the timestamp
        if state == 'playing':
            current_time = int(time.time())
            start_time = current_time - view_offset / 1000
            activity['timestamps'] = {'start': start_time}

        # Set Discord rich presence
        RPC.send_rich_presence(activity)


if __name__ == "__main__":
    account = MyPlexAccount(PLEX_USERNAME, PLEX_PASSWORD)
    plex = account.resource(PLEX_SERVER).connect()
    plex_admin = (account.email == plex.myPlexUsername or account.username == plex.myPlexUsername)
    plex.startAlertListener(process_alert)

    RPC = DiscordRPC(DISCORD_CLIENT_ID)  # Send the client ID to the rpc module
    RPC.start()  # Start the RPC connection
    clear_rich_presence()  # Clear rich presence
    time.sleep(10)  # Delay to make sure initial state is set

    try:
        while True:
            time.sleep(3600)
            continue
    except KeyboardInterrupt:
        print("Exiting Discord RPC")
        RPC.close()

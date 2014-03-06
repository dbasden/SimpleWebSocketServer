#!/usr/bin/env python

'''send/receive lines from stdin/stdout to a websocket

    wscat [ <websocket port> ]

    e.g.
        send a message to every connected client every second with
        vmstat output

            vmstat 1 | wscat 5555

        get messages from clients and write them to a file while showing
        them on stdin

            wscat | tee rxed_messages

        doing both

            vmstat 1 | wscat | tee rxed_messages
'''

from SimpleWebSocketServer import *
import sys
import os
import fcntl


class WSCatSocket(WebSocket):
    def handleMessage(self):
        d = self.data if self.data is not None else ''
        print >> self.server.outfile, d

class WSCatServer(SimpleWebSocketServer):
    def __init__(self, *args, **argd):
        SimpleWebSocketServer.__init__(self, *args, **argd)

        # Get a linebuffered stdout
        self.outfile = os.fdopen(sys.stdout.fileno(),'w',1)

        # Get a non-blocking, linebuffered stdin
        self.infile = os.fdopen(sys.stdin.fileno(),'r',1)
        fd = self.infile.fileno()
        fn = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fn | os.O_NONBLOCK)

    def broadcastMessage(self,message):
        for client in self.connections.itervalues():
            if client == self: continue
            try:
                client.sendMessage(message)
            except Exception as e:
                print >> sys.stderr, e

    def serveforever(self):
        while True:
            try:
                l = None
                l = self.infile.readline()
                if l != '':
                    sys.stderr.write('sending: '+l)
                    self.broadcastMessage(l)
                    continue
            except: 
                pass
            finally:
                # Always serve websockets to avoid starvation on lots of 
                # stdin traffic, but don't block if we just had a successful
                # stdin read lest there still be more waiting
                self.serveonce(0 if l else 0.1)

            if l == '':
                # feof on stdin. Wait for all clients to exit before closing
                while len(self.listeners) > 1:
                    self.serveonce(1)
                return 
            
if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 10204

    WSCatServer('',port,WSCatSocket).serveforever()

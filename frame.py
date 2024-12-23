import json
import struct
import socket
import logging

PACK_FMT_STR = '!BBHLH6s'

class frame:
    def creat(reqId, msgType, msg={}):
        msgLen = 0
        jsonStr = json.dumps(msg)
        if (msg != {}):
            msgLen = len(jsonStr)
        rawMsg = struct.pack(PACK_FMT_STR, 0x5A, 0x01, reqId, msgLen,msgType, b'\x00\x00\x00\x00\x00\x00')

        if (msg != {}):
            rawMsg += bytearray(jsonStr,'ascii')
        return rawMsg
class tranmit:
    def sendAPI(headerAPI:socket.socket,code_api:int,jsonstring:dict):
        try:
            headerAPI.send(frame.creat(1,code_api,jsonstring))
        except socket.error:
            logging.error("SEND FRAME TO AMR ERROR")
            return None
        dataall = b''
        data = b''
        try:    
            data = headerAPI.recv(16)
        except socket.timeout:
            logging.error("TIME OUT RECT FRAME TO AMR")
            return None
        if(len(data) < 16):
            logging.error("PACK HEAD ERROR")
            return None
        else:
            header = struct.unpack(PACK_FMT_STR, data)
            jsonDataLen = header[3]
            backReqNum = header[4]
        dataall += data
        data = b''
        readSize = 1024
        try:
            while (jsonDataLen > 0):
                recv = headerAPI.recv(readSize)
                data += recv
                jsonDataLen -= len(recv)
                if jsonDataLen < readSize:
                    readSize = jsonDataLen
            data = json.loads(data)
            return data
        except Exception as e:
            return None

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import re

from google_api_manager import *

class MessageDataDictList(list):

    def __init__(self,parent=None):
        # super(RowDataList, self).__init__(parent)
        list.__init__(self)
        print "MessageDataList init"

        self.credentials = get_credentials()
        http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('gmail', 'v1', http=http)

        # 添付ファイルのあるメッセージのみ抽出
        # threads = service.users().threads().list(userId="me",maxResults=10,q="from:urikake2@misumi.co.jp").execute().get("threads",[])
        print "now getting messages..."
        messages = self.service.users().messages().list(userId="me",maxResults=10,q="from:urikake2@misumi.co.jp has:attachment").execute()["messages"]
        for i in range( len(messages) ):
            message_data_dict = MessageDataDict( messages[i], self.service )
            self.append(message_data_dict)

class MessageDataDict(dict):

    def __init__(self, message, service, parent=None):
        dict.__init__(self)
        print "MessageDataDict init"

        for key in ["orderdate","duedate","price"]:
            self[key] = None

        self.__service = service
        self.id = message["id"]
        self.payload = self.__service.users().messages().get(userId="me",id=self.id).execute()["payload"]
        self.attachment_parts = filter(lambda x: x["filename"] != "", self.payload["parts"])# 添付ファイルのあるpartのみ抽出 2-4番目をとるのでもいいかも

        self.receiver = base64.urlsafe_b64decode(self.payload["parts"][0]["body"]["data"].encode("ASCII")).split("\n")[1]
        self.receive_date = filter(lambda x: x["name"] == "Date", self.payload["headers"])[0]["value"]# 受信日

        self.__estimate = None
        self.__invoice = None
        self.__bill = None

        self.__estimate_path = None

    def get_attachment_data(self,basename):
        print("MessageData.get_attachment_data()")
        if self.__estimate is None:
            for attachment_part in self.attachment_parts:
                if attachment_part["filename"].encode("utf-8") == basename + ".pdf":
                    return self.__service.users().messages().attachments().get(userId="me",messageId=self.id,id=attachment_part["body"]["attachmentId"]).execute()["data"]
            return false
        return self.__estimate

    def get_estimate_data(self):
        return self.get_attachment_data("御見積書")
        
    def get_invoice_data(self):
        return self.get_attachment_data("納品書")

    def get_bill_data(self):
        return self.get_attachment_data("御請求書")
        
    def set_values(self):
        print "set_values()"
        order_data_dict = dict()
        
        self.create_estimate()                
        os.system("pdftotext -upw 160398 " + self.estimate_path().encode("utf-8"))# textファイルへ変換        
        file_text = open(self.estimate_path().replace(".pdf",".txt")).read()# listへ変換

        date_list = re.split("\D",re.findall("発行日.*\n",file_text)[0])
        while "" in date_list: date_list.remove("")
        self["orderdate"] = reduce(lambda x,y: x + "/" + y,date_list)# from estimate
        self["duedate"] = reduce(lambda x,y: x + "/" + y,date_list)# from invoice
        
        self["price"] = re.findall("[,0-9]+\n",file_text)[4].replace("\n","")

    def estimate_path(self):
        if self.__estimate_path is None:
            self.__estimate_path = os.path.join("/tmp", self.id + self.attachment_parts[0]["filename"])
        return self.__estimate_path

    def create_estimate(self):
        if not os.path.exists(self.estimate_path()):
            file_data = base64.urlsafe_b64decode(self.get_estimate_data().encode('UTF-8'))
            f = open(self.estimate_path(), 'w')
            f.write(file_data)
            f.close()

    def open_estimate(self):
        estimate_path = self.estimate_path()
        self.create_estimate()
        os.system("gnome-open " + estimate_path.encode("utf-8"))

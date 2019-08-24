import requests,json,threading
from sseclient import SSEClient
class AuthenticationError(Exception):
    pass
class HASS:
    def __init__(self,config,client):
        self.config=config
        self.headers={'Authorization': "Bearer " + config["token"]}
        self.api=config["address"]+"/api/"
        self.states={}
        tmp=self.__test_auth()
        if not tmp[0]:
            raise AuthenticationError(tmp[1])
        self.getstates()
        with open("config.json",encoding='UTF-8') as f:
            j=json.loads(f.read())
        with open("config.json","w",encoding='UTF-8') as f:
            j["hass"]["setname"] = self.states
            f.write(json.dumps(j,indent=4,ensure_ascii=False))
        threading.Thread(target=self.__event,args=(client,)).start()
    def __test_auth(self):
        tmp=requests.get(self.api,headers=self.headers)
        if tmp.status_code == 401:
            return [False,"认证错误，请检查令牌是否有效"]
        elif tmp.status_code == 200 or tmp.status_code == 201:
            return [True,""]
        else:
            temp = requests.get(self.api.split("/api/")[0] + "api/", headers=self.headers)
            if temp.status_code == 401:
                return [False, "认证错误，请检查令牌是否有效"]
            elif temp.status_code == 200or temp.status_code == 201:
                self.api = self.api.split("/api/")[0] + "api/"
                return [True, ""]
            else:
                return [False, "网络错误，请检查是否能连通"]
    def getstates(self):
        states = json.loads(requests.get(self.api+"states",headers=self.headers).text)
        for state in states:
            if state["entity_id"] in self.config["setname"].keys():
                self.states[state["entity_id"]] = self.config["setname"][state["entity_id"]].replace("的","")
            else:
                try:
                    self.states[state["entity_id"]] = state["attributes"]["friendly_name"].replace("的","")
                except:
                    self.states[state["entity_id"]] = state["entity_id"]
    def turn_on(self,entity_id):
        domain=entity_id.split(".")[0]
        self.setstate(domain,"turn_on",{"entity_id": entity_id})
        state = self.getstate(entity_id)
        if state["entity_id"]==entity_id and state["state"] != "off":
            return True
        return False
    def turn_off(self,entity_id):
        domain = entity_id.split(".")[0]
        self.setstate(domain,"turn_off",{"entity_id": entity_id})
        state = self.getstate(entity_id)
        if state["entity_id"]==entity_id and state["state"] == "off":
            return True
        return False
    def getstate(self,entity_id):
        tmp=requests.get(self.api+"states/"+entity_id,headers=self.headers)
        if tmp.status_code == 404:
            return None
        return json.loads(tmp.text)
    def setstate(self,domain,service,data:dict):
        try:
            rtn=json.loads(requests.post(self.api+"services/"+domain+"/"+service,json=data,headers=self.headers).text)
        except:
            return None
        return rtn
    def __event(self,client):
        messages = SSEClient(self.api+'stream', headers=self.headers)
        for message in messages:
            if message.data=="ping":
                continue
            msg=json.loads(message.data)
            if msg["event_type"] == "state_changed":
                if "motion" in msg["data"]["entity_id"]:
                    if msg["data"]["new_state"]["state"] == "on":
                        client.send_text_message(self.states[msg["data"]["entity_id"]]+"被触发了")
                elif msg["data"]["new_state"]["state"] == "on":
                    if msg["data"]["old_state"]["state"] == "unavailable":
                        client.send_text_message(self.states[msg["data"]["entity_id"]] + "可用了")
                        continue
                    client.send_text_message(self.states[msg["data"]["entity_id"]] + "被打开了")
                elif msg["data"]["new_state"]["state"] == "off":
                    if msg["data"]["old_state"]["state"] == "unavailable":
                        client.send_text_message(self.states[msg["data"]["entity_id"]] + "可用了")
                        continue
                    client.send_text_message(self.states[msg["data"]["entity_id"]] + "被关闭了")
                elif msg["data"]["new_state"]["state"] == "unavailable":
                    client.send_text_message(self.states[msg["data"]["entity_id"]] + "不可用")
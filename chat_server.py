#coding:utf-8
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import redis
import json
import urlparse
# name_record_obj.set(username,self.uid)
# Create the tornadoredis.Client instance
# and use it for redis channel subscriptions
# define("port", default=8787, help="run on the given port", type=int)

# class Application(tornado.web.Application):
#     def __init__(self):
#         handlers = [
#             (r"/send", ChatSocketHandler),
#         ]
#         settings = dict(
#             cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
#             template_path=os.path.join(os.path.dirname(__file__), "."),
#             static_path=os.path.join(os.path.dirname(__file__), "."),
#             xsrf_cookies=True,
#         )
#         tornado.web.Application.__init__(self, handlers, **settings)
chat_record_obj = ChatRecord.get(get_area_id())

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = {}
    cache = []
    cache_size = 30
    # content_record = []
    def open(self):
        appMod.pier.clear()
        uid = self.get_argument('uid','')
        if uid:
            all_say = all_other_say(uid,chat_record_obj)
            all_xx = ChatSocketHandler.cache[-10:]+all_say[-10:]
            data = {'type':'chat','content':all_xx}
            ChatSocketHandler.waiters[uid] = self
            self.write_message(json.dumps(data))
            self.write_message(json.dumps(self.get_friend_list(uid)))

    def on_close(self):
        appMod.pier.clear()
        for uid,class_mod in ChatSocketHandler.waiters.items():
            if class_mod == self:
                ChatSocketHandler.waiters.pop(uid)
                break

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, content_dict,message_type="chat"):
        listener = content_dict['listener']
        uid = content_dict['uid']
        if listener == "world":
            listeners = cls.waiters.keys()
            if content_dict not in cls.cache:
                cls.update_cache(content_dict)
        elif listener == 'guild':
            user_property_obj = UserProperty.get(uid)
            guild_id = user_property_obj.guild_id
            if guild_id:
                guild_obj = Guild.get(guild_id)
                listeners = [key.split(":")[-1] for key in guild_obj.member.keys()]
            else:
                listeners = []
        elif listener.isdigit():
            listeners = [listener,uid]
        else:
            listeners = []

        for uid in listeners:
            try:
                data = {'type':message_type,'content':[content_dict][:20]}
                return_data = json.dumps(data)
                if uid in cls.waiters:
                    cls.waiters[uid].write_message(return_data)
                if listener != 'world':
                    all_say = all_other_say(uid,chat_record_obj)
                    all_say.append(content_dict)
                    chat_record_obj.set(uid,json.dumps(all_say[-10:]))
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        appMod.pier.clear()
        # all_message = dict(urlparse.parse_qsl(message))
        all_message = json.loads(message)

        if all_message.get("content") and all_message['content'].get('say'):
            all_message['content']['say'] = replace_sense_word(all_message['content']['say'])
        uid = all_message['content']['uid']
        can_send = True
        if all_message['type'] == 'chat':
            if all_message['content']['listener'] == 'world':
                user_gift_obj = UserGift.get_instance(uid)
                waiter_times = user_gift_obj.popular*5
                # waiter_times = 0
                if waiter_times<0:
                    data = {'type':'error','content':{"rc":14,'wait_time':abs(waiter_times)}}
                    self.write_message(json.dumps(data))
                    can_send = False
                user_property_obj = UserProperty.get(uid)
                if user_property_obj.lv<40 and user_property_obj.property_info['taskToken']<80:
                    data = {'type':'error','content':{'msg':u'主角要大于40级或者活跃点大于80'}}
                    self.write_message(json.dumps(data))
                    can_send = False
                # if all_message['content']['area_id'] != get_area_id():
                #     can_send = False
            if can_send:
                ChatSocketHandler.send_updates(all_message['content'],all_message['type'])
        elif all_message['type'] == 'friend_list':
            self.write_message(json.dumps(self.get_friend_list(uid)))

    def get_friend_list(self,uid,message_type="friend_list"):
        appMod.pier.clear()
        user_friend_obj = UserFriend.get_instance(uid)
        data = {'type':message_type,'content':[]}
        online_friend = set(user_friend_obj.get_friend_ids())&set(ChatSocketHandler.waiters.keys())
        for fid in user_friend_obj.friends:
            user_property_obj = UserProperty.get(fid)
            if fid in online_friend:
                online = True
            else:
                online = False
            tmp_data = {'name':user_property_obj.username,\
                        'lv':user_property_obj.lv,\
                        'uid':user_property_obj.uid,\
                        'leader_id':user_property_obj.leader_id,\
                        'avatar_info':user_property_obj.get_avatar_info(),
                        'online':online,\
                        }
            data['content'].append(tmp_data)
        return data

def all_other_say(uid,chat_record_obj):
    all_say = chat_record_obj.get_value(uid)
    if not all_say:
        all_say = []
    else:
        all_say = json.loads(all_say)
    chat_record_obj.set(uid,json.dumps([]))
    return all_say


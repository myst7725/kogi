import re
import json
import requests
from .utils import listfy, zen2han, remove_suffixes
from .parse_error import parse_error_message
from .logger import send_log

DUMMY = 'rhOcswxkXzMbhlkKQJfytbfxAPVsblhRHX'

REMOVED_SUFFIXES = [
    '.', '。', '?', '？', '！',
    '何', '何ですか', '何でしょうか',
    'が知りたい', 'がしりたい', 'がわからない', 'が分からない',
]


def startswith(text, prefixes):
    for prefix in prefixes:
        if text.startswith(prefix):
            return True
    return False


def remove_tai(s):
    if s.endswith('したい'):
        return s[:-3]+'する'
    if s.endswith('きたい'):
        return s[:-3]+'く'
    if s.endswith('ちたい'):
        return s[:-3]+'つ'
    if s.endswith('にたい'):
        return s[:-3]+'ぬ'
    if s.endswith('りたい'):
        return s[:-3]+'る'
    if s.endswith('みたい'):
        return s[:-3]+'む'
    if s.endswith('いたい'):
        return s[:-3]+'う'
    if s.endswith('ぎたい'):
        return s[:-3]+'ぐ'
    if s.endswith('びたい'):
        return s[:-3]+'ぶ'
    return s[:-2]+'る'


HINT = {
    'abc231_a': '難しいことはありません.'
}


class Chatbot(object):
    slots: dict

    def __init__(self, slots=None):
        self.slots = {} if slots is None else slots

    def get(self, key, value=''):
        return self.slots.get(key, value)

    def response(self, text):
        text = zen2han(text)
        text = remove_suffixes(text, REMOVED_SUFFIXES)
        if startswith(text, ('デバッグ', 'わん')):
            return f'{self.slots}'
        if startswith(text, ('変数', '困った', 'デバッグ')):
            return self.response_variables()
        if text.endswith('には'):
            text = text[:-2]
            return self.response_translate(text)
        if text.endswith('たい'):
            text = remove_tai(text)
            return self.response_translate(text)
        if text.endswith('って') or text.endswith('とは'):
            text = text[:-2]
            return self.response_desc(text)
        if startswith(text, ('原因', '理由', 'なぜ', 'なんで', 'どうして')):
            if 'reason' in self.slots:
                return self.slots['reason']
            else:
                return self.response_vow(text)
        if startswith(text, ('ヒント', '助けて', 'たすけて')):
            if 'context' in self.slots and self.slots['context'] in HINT:
                return HINT[self.slots['context']]
            else:
                return 'ノー ヒント！'
        if startswith(text, ('解決', 'どう', 'お手上げ')):
            if 'solution' in self.slots:
                return self.slots['solution']
            elif 'hint' in self.slots:
                return self.slots['hint']
            elif 'reason' in self.slots:
                return self.slots['reason']
            return self.response_vow(text)
        return self.response_code(text)

    def response_vow(self, text):
        return "わん"

    def response_translate(self, text):
        return response_translate(text)

    def response_desc(self, text):
        return response_translate(text)

    def response_variables(self, name=None):
        ss = ['変数を全部、表示するよ']
        for stack in self.get('stacks'):
            if 'vars' not in stack:
                continue
            vars = stack['vars']
            if name is None:
                for n in vars.keys():
                    if n.startswith('_') or n in SKIP_IDS:
                        continue
                    v = vars[n]
                    ty = type(v).__name__
                    if ty in ('module', 'function'):
                        continue
                    ss.append(render_value(n, ty, vars[n]))
            elif name in vars:
                v = vars[name]
                ss.append(render_value(name, type(v).__name__, v))
        return ss

    def response_code(self, text):
        return self.response_vow(text)


API_URL = "https://api-inference.huggingface.co/models/kkuramitsu/kogi-mt5-test"
headers = {"Authorization": f"Bearer hf_{DUMMY}"}


def response_translate(text):
    if len(text) > 80:
        return 'ぐるるるる'
    payload = {"inputs": text}
    response = requests.post(API_URL, headers=headers, json=payload)
    output = response.json()
    print(text, type(output), output)
    if isinstance(output, (list, tuple)):
        output = output[0]
    if 'generated_text' in output:
        return output['generated_text']
    return 'ねむねむ。まだ、起きられない！'


SKIP_IDS = set([
    'In', 'Out', 'get_ipython', 'exit', 'quit'
])


def render_value(name, typename, value):
    head = f'<b>{name}: {typename}型</b>'
    if hasattr(value, '__len__'):
        v = len(value)
        head += f' <tt>len({name})={v}</tt>'
    body = f'<pre>{repr(value)}</pre>'
    if hasattr(value, '_repr_html_'):
        body = value._repr_html_()
    return f'{head}<br/>{body}'


def get_chatbot_webui():
    import traceback
    from IPython.display import display, HTML
    from google.colab import output
    from .html import BOT_ICON, BOT_HTML, CLEAR_HTML, YOUR_ICON, USER_HTML, CHAT_CSS, CHAT_HTML

    def _display_bot(bot_text, chatbot):
        with output.redirect_to_element('#output'):
            bot_name = chatbot.get('bot_name', 'コギー')
            bot_icon = chatbot.get('bot_icon', BOT_ICON)
            for text in listfy(bot_text):
                text = text.replace('\n', '<br/>')
                display(HTML(BOT_HTML.format(bot_icon, bot_name, text)))
        if 'バイバイ' in bot_text:
            display(HTML(CLEAR_HTML))

    def _display_you(your_text, chatbot):
        with output.redirect_to_element('#output'):
            your_name = chatbot.get('your_name', 'あなた')
            your_icon = chatbot.get('your_icon', YOUR_ICON)
            for text in listfy(your_text):
                text = text.replace('\n', '<br/>')
                display(HTML(USER_HTML.format(your_icon, your_name, text)))

    def debug_log():
        try:
            send_log()
        except Exception as e:
            print(e)

    def _display_chat(chatbot):
        display(HTML(CHAT_CSS))
        display(HTML(CHAT_HTML))

        def ask(your_text):
            your_text = your_text.strip()
            if 'ありがとう' in your_text or 'バイバイ' in your_text:
                display(HTML(CLEAR_HTML))
            try:
                _display_you(your_text, chatbot)
                bot_text = chatbot.response(your_text)
                if bot_text is not None:
                    _display_bot(bot_text, chatbot)
            except Exception as e:
                _display_bot('バグりました。\nエラーレポートを頂けると早く回復できます', chatbot)
                traceback.print_exc()

        output.register_callback('notebook.ask', ask)
        output.register_callback('notebook.log', debug_log)

    def kogi_say(msg, chatbot=None):
        send_log(right_now=True)
        if chatbot is None:
            chatbot = Chatbot()
        _display_chat(chatbot)
        _display_bot(msg, chatbot)

    return kogi_say


kogi_say = get_chatbot_webui()


def exception_dialog(code, emsg, stacks):
    lines = [stack['line'].strip() for stack in stacks]
    slots = parse_error_message(code, emsg, lines)
    slots['lines'] = lines
    slots['stacks'] = stacks
    if hasattr(get_ipython(), '_run_cell_context'):
        context = get_ipython()._run_cell_context
        if context is not None:
            slots['context'] = context
    chatbot = Chatbot(slots=slots)
    if 'translated' in slots:
        kogi_say(slots['translated'], chatbot)
    else:
        kogi_say('にゃん', chatbot)

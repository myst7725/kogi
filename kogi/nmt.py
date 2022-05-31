# translate
import IPython
from IPython.display import display, HTML
import os

#from kogi.libnmt.transformer import load_transformer_nmt
from .logger import log, send_log, print_nop

TRANSLATE_CSS_HTML = '''
<style>
.parent {
  background-color: #edebeb;
  width: 100%;
  height: 150px;
}
textarea {
  width: 100%; 
  box-sizing: border-box;  /* ※これがないと横にはみ出る */
  height:120px; 
  font-size: large;
  outline: none;           /* ※ブラウザが標準で付加する線を消したいとき */
  resize: none;
}
.box11{
//    padding: 0.5em 1em;
//    margin: 2em 0;
    color: #5d627b;
    background: white;
    border-top: solid 5px #5d627b;
    box-shadow: 0 3px 5px rgba(0, 0, 0, 0.22);
}
.box18{
  //padding: 0.2em 0.5em;
  //margin: 2em 0;
  color: #565656;
  background: #ffeaea;
  //background-image: url(https://2.bp.blogspot.com/-u7NQvQSgyAY/Ur1HXta5W7I/AAAAAAAAcfE/omW7_szrzao/s800/dog_corgi.png);
  background-size: 150%;
  background-repeat: no-repeat;
  background-position: top right;
  background-color:rgba(255,255,255,0.8);
  background-blend-mode:lighten;
  //box-shadow: 0px 0px 0px 10px #ffeaea;
  border: dashed 2px #ffc3c3;
  //border-radius: 8px;
}
.box16{
    //padding: 0.5em 1em;
    //margin: 2em 0;
    background: -webkit-repeating-linear-gradient(-45deg, #f0f8ff, #f0f8ff 3px,#e9f4ff 3px, #e9f4ff 7px);
    background: repeating-linear-gradient(-45deg, #f0f8ff, #f0f8ff 3px,#e9f4ff 3px, #e9f4ff 7px);
}
.box24 {
    position: relative;
    padding: 0.5em 0.7em;
    margin: 2em 0;
    background: #6f4b3e;
    color: white;
    font-weight: bold;
}
.box24:after {
    position: absolute;
    content: '';
    top: 100%;
    left: 30px;
    border: 15px solid transparent;
    border-top: 15px solid #6f4b3e;
    width: 0;
    height: 0;
}
// loader
.loader {
  align-items: center;
  background: #fff;
  bottom: 0;
  display: flex;
  justify-content: center;
  left: 0;
  position: fixed;
  right: 0;
  top: 0;
  z-index: 999;
  &::after {
    animation: loader 0.5s linear infinite;
    border: 1px solid orange;
    border-radius: 50%;
    border-right: 1px solid rgba(orange, 0.2);
    border-top: 1px solid rgba(orange, 0.2);
    content: "";
    height: 70px;
    width: 70px;
  }
}

@keyframes loader {
  0% {
    transform: rotate(0);
  }

  100% {
    transform: rotate(360deg);
  }
}

body {
  font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
}

main{
  line-height: 1.6;
  max-width: 500px;
  margin: 0 auto;
  padding: 25px;
  h1{
    font-size: 32px;
    font-weight: bold;
  }
  p{
    font-size: 16px;
    margin-top: 30px;
  }
}
</style>
<div class="parent">
<div style="float: left; width: 48%; text-align: right;">
<label class="box24" for="input">INPUT</label>
<textarea id="input" class="box16" readonly></textarea>
</div>
<div style="float: left; width: 48%; text-align: right;">
<label class="box24" for="outout">OUTOUT</label>
<textarea id="output" class="box18 python" readonly></textarea>
</div>
</div>
<div id="js-loader" class="loader"></div>
<script>
const loader = document.getElementById('js-loader');
window.addEventListener('load', () => {
  const ms = 4000;
  loader.style.transition = 'opacity ' + ms + 'ms';
  
  const loaderOpacity = function(){
    loader.style.opacity = 0;
  }
  const loaderDisplay = function(){
    loader.style.display = "none";
  }
  // setTimeout(loaderOpacity, 1);
  // setTimeout(loaderDisplay, ms);
  // デモ用
  setTimeout(loaderOpacity, 1000);
  setTimeout(loaderDisplay, 1000 + ms);
});
</script>
'''

TRANSLATE_SCRIPT = '''
<script>
    var timer = null;
    var logtimer = null;
    var inputPane = document.getElementById('input');
    inputPane.disabled = false;
    inputPane.addEventListener('input', (e) => {
        var text = e.srcElement.value;
        if(timer !== null) {
            clearTimeout(timer);
        }
        if(logtimer !== null) {
            clearTimeout(logtimer);
        }
        timer = setTimeout(() => {
            timer = null;
            (async function() {
                const result = await google.colab.kernel.invokeFunction('notebook.Convert', [text], {});
                const data = result.data['application/json'];
                const textarea = document.getElementById('output');
                textarea.textContent = data.result;
            })();
        }, 600);  // 何も打たななかったら600ms秒後に送信
        logtimer = setTimeout(() => {
            // logtimer = null;
            google.colab.kernel.invokeFunction('notebook.Logger', [], {});
        }, 60*1000*5); // 5分に１回まとめて送信
    });
</script>
'''

def load_mt5(model_id, qint8=True, device='cpu', print=print):
    print('loading kogi ai')
    os.system('pip install -q sentencepiece transformers')
    import torch
    from transformers import MT5ForConditionalGeneration, MT5Tokenizer
    model = MT5ForConditionalGeneration.from_pretrained(model_id)
    tokenizer = MT5Tokenizer.from_pretrained(model_id, is_fast=True)

    if qint8:
        model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )

    if isinstance(device, str):
        device = torch.device(device)
    model.to(device)

    def gready_search(s: str, max_length=128, beam=1) -> str:
        input_ids = tokenizer.encode_plus(
            s,
            add_special_tokens=True,
            max_length=max_length,
            padding="do_not_pad",
            truncation=True,
            return_tensors='pt').input_ids.to(device)
        greedy_output = model.generate(input_ids, max_length=max_length)
        return tokenizer.decode(greedy_output[0], skip_special_tokens=True)

    return gready_search

def translate(model_id, load_nmt=load_mt5, beam=1, device='cpu', qint8=True, input='日本語', output='Python', print = print):
    display(HTML(TRANSLATE_CSS_HTML.replace('INPUT', input).replace('OUTPUT', output)))
    nmt = load_nmt(model_id, qint8=qint8, device=device, print=print)
    cached = {'':''}

    def convert(text):
        try:
            ss = []
            for line in text.split('\n'):
                if line not in cached:
                    translated = nmt(line, beam=beam)
                    print(line, '=>', translated)
                    cached[line] = translated
                    log(
                        type='realtime-nmt',
                        input=line, output=translated,
                    )
                else:
                    translated = cached[line]
                ss.append(translated)
            text = '\n'.join(ss)
            return IPython.display.JSON({'result': text})
        except Exception as e:
            print(e)

    try:
        from google.colab import output
        output.register_callback('notebook.Convert', convert)
        output.register_callback('notebook.Logger', send_log)
    except Exception as e:
        print(e)
    display(HTML(TRANSLATE_SCRIPT))

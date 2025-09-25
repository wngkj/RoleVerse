import pyaudio
import subprocess
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import dashscope

dashscope.api_key = "sk-e81dd3320ee3459289354ef0ae816852"

process = None
final_text = None
stop = False


class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global process
        print('RecognitionCallback open.')

        # 使用 PyAudio 代替 arecord 进行音频录制
        p = pyaudio.PyAudio()

        # 配置音频流
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=3200)

        process = stream

    def on_close(self) -> None:
        global process
        print('RecognitionCallback close.')
        if process:
            process.stop_stream()
            process.close()
            process = None

    def on_event(self, result: RecognitionResult) -> None:
        global final_text, stop
        sentence = result.get_sentence()

        # 如果返回的 sentence 是字典类型并且 'end_time' 不为 None，表示识别结束
        if isinstance(sentence, dict) and sentence.get('end_time') is not None:
            print('Final sentence: ', sentence.get('text'))
            final_text = sentence.get('text')
            stop = True
        print('RecognitionCallback sentence: ', sentence)


def start_speech_recognition():
    global final_text, stop
    final_text = None
    stop = False
    callback = Callback()
    recognition = Recognition(model='paraformer-realtime-v2',
                              format='pcm',
                              sample_rate=16000,
                              callback=callback)
    recognition.start()

    try:
        while not stop:
            if process:
                # 从 PyAudio 流中读取音频数据
                data = process.read(3200)
                if not data:
                    break
                recognition.send_audio_frame(data)
            else:
                print("Process is None.")
                break
    except KeyboardInterrupt:
        print("程序被手动中断")
    finally:
        recognition.stop()
        if process:
            process.stop_stream()
            process.close()

    return final_text


# 调用示例
if __name__ == "__main__":
    result_text = start_speech_recognition()
    print("识别结果: ", result_text)

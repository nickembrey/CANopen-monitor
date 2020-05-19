import threading
from .frame_data import FrameData
from canard.hw.socketcan import SocketCanDev
from queue import Queue, Full, Empty


class TheMagicCanBus:
    def __init__(self, device_names=[], block=True, timeout=0.1):
        # Bus things
        self.devs = []
        self.frames = Queue()

        # Threading things
        self.stop_listening = threading.Event()
        self.block = block
        self.timeout = timeout
        self.threads = []

        for name in device_names:
            self.start(name)

    def start(self, dev_name):
        dev = SocketCanDev(dev_name)
        dev.start()
        self.devs.append(dev)
        dev_listener = threading.Thread(target=self.listen,
                                        args=[dev])
        dev_listener.setDaemon(True)
        dev_listener.start()
        self.threads.append(dev_listener)

    def stop(self, dev):
        self.devs.remove(dev)

    def stop_all(self):
        # Remove all devices from the device table
        for dev in self.devs:
            self.stop(dev)

        self.stop_listening.set()

        print('waiting for '
              + str(len(self.threads))
              + ' bus-threads to close.')
        if(len(self.threads) > 0):
            for thread in self.threads:
                thread.join()
            print('all bus threads closed gracefully!')
        else:
            print('no child bus threads were spawned!')

    def listen(self, dev):
        try:
            while not self.stop_listening.is_set():
                self.frames.put([dev.recv(), dev.ndev], block=self.block)
        except Full:
            pass
        except OSError:
            self.stop(dev)

    def receive(self):
        try:
            res = self.frames.get(block=self.block, timeout=self.timeout)
            return FrameData(res[0], res[1])
        except Empty:
            return None

    def running(self):
        return list(filter(lambda x: x.running, self.devs))

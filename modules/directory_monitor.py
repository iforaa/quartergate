import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class DirectoryMonitor:
    def __init__(self, base_directory, callback, debounce_time=2.0):
        """
        Initialize the monitor for a specific base directory.
        :param base_directory: The base directory to monitor.
        :param callback: Function to call with the list of new files.
        :param debounce_time: Time (in seconds) to wait before calling the callback.
        """
        self.base_directory = base_directory
        self.callback = callback
        self.debounce_time = debounce_time
        self.observer = Observer()
        self.new_files = set()
        self.lock = threading.Lock()
        self.timer = None

    def start(self):
        """
        Start monitoring the directory.
        """
        event_handler = NewFileHandler(self.new_file_detected)
        self.observer.schedule(event_handler, self.base_directory, recursive=True)
        self.observer.start()
        print(f"Started monitoring {self.base_directory}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Stop monitoring the directory.
        """
        self.observer.stop()
        self.observer.join()
        print("Stopped monitoring")

    def new_file_detected(self, file_path):
        """
        Called when a new file is detected. Debounces the processing.
        :param file_path: Path of the new file.
        """
        with self.lock:
            self.new_files.add(file_path)
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.debounce_time, self.process_new_files)
            self.timer.start()

    def process_new_files(self):
        """
        Collects the batched new files and calls the callback.
        """
        with self.lock:
            files_to_process = list(self.new_files)
            self.new_files.clear()
        self.callback(files_to_process)


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        """
        Initialize the file event handler.
        :param callback: Callback function to call on file creation.
        """
        self.callback = callback

    def on_created(self, event):
        """
        Called when a new file or directory is created.
        :param event: The event object containing information about the change.
        """
        if not event.is_directory:
            self.callback(event.src_path)

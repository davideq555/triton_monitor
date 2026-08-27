import gzip
import logging
import logging.config
import logging.handlers
import os
import queue
from pathlib import Path

class NonBlockingLoggingEngine:

  def __init__(self, log_file_path="logs/app.log", formatter=None):
    self.log_file_path = Path(log_file_path)
    self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    self.log_queue = queue.Queue(-1)
    self.rotating_handler = logging.handlers.RotatingFileHandler(
        filename=self.log_file_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    if formatter:
      self.rotating_handler.setFormatter(formatter)

    self._setup_gzip_rotation()

    self.queue_handler = logging.handlers.QueueHandler(self.log_queue)

    self.listener = logging.handlers.QueueListener(
        self.log_queue, self.rotating_handler, respect_handler_level=True
    )

  def _setup_gzip_rotation(self):

    def rotator(source, dest):
      with open(source, "rb") as f_in:
        with gzip.open(dest, "wb", compresslevel=9) as f_out:
          f_out.writelines(f_in)
      os.remove(source)

    def namer(default_name):
      return default_name + ".gz"

    self.rotating_handler.rotator = rotator
    self.rotating_handler.namer = namer

  def start(self):
    self.listener.start()

  def stop(self):
    self.listener.stop()

def get_async_logger(name="AsyncPipelineLogger", formatter=None):
  
  engine = NonBlockingLoggingEngine(formatter=formatter)
  engine.start()

  logger = logging.getLogger(name)
  logger.setLevel(logging.INFO)
  logger.handlers.clear()
  logger.addHandler(engine.queue_handler)
  logger.propagate = False

  return logger, engine

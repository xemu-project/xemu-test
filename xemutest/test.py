#!/usr/bin/env python3

import subprocess
import shutil
import logging
import os
import signal
import time
import platform
import sys
from typing import Optional

from pyfatx import Fatx


if platform.system() == 'Windows':
	import pywinauto.application


log = logging.getLogger(__file__)


class Test:
	"""
	Test provides a basic framework that:
	- Starts FFMPEG to record footage of xemu while it runs
	- Launches xemu with an test XBE loaded from a disc image
	- Waits for xemu to shutdown or timeout
	- Inspect the filesystem for test results

	Tester runs in current working directory and will generate some working files.
	"""

	def __init__(self, private_path: str, results_path: str):
		cur_dir = os.getcwd()
		if platform.system() == 'Windows':
			self.xemu_path = os.path.join(cur_dir, 'xemu.exe')
		else:
			self.xemu_path = 'xemu'

		test_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
		if not os.path.isdir(test_data_path):
			raise FileNotFoundError('Test data was not installed with the package. You need to build it.')

		self.flash_path         = os.path.join(private_path, 'bios.bin')
		self.mcpx_path          = os.path.join(private_path, 'mcpx.bin')
		self.hdd_path           = os.path.join(cur_dir, 'test.img')
		self.mount_path         = os.path.join(cur_dir, 'xemu-hdd-mount')
		self.iso_path           = os.path.join(test_data_path, 'tester.iso')
		self.results_in_path    = os.path.join(self.mount_path, 'results')
		self.results_out_path   = results_path
		self.video_capture_path = os.path.join(self.results_out_path, 'capture.mp4')
		self.timeout            = 60

		if platform.system() == 'Windows':
			self.app: Optional[pywinauto.application.Application] = None
			self.record_x: int = 0
			self.record_y: int = 0
			self.record_w: int = 0
			self.record_h: int = 0

	def prepare_roms(self):
		log.info('Preparing ROM images')
		# Nothing to do here yet

	def prepare_hdd(self):
		log.info('Preparing HDD image')
		disk_size = 8*1024*1024*1024
		if os.path.exists(self.hdd_path):
			if os.path.getsize(self.hdd_path) != disk_size:
				raise FileExistsError('Target image path exists and is not expected size')
			Fatx.format(self.hdd_path)
		else:
			Fatx.create(self.hdd_path, disk_size)

	def prepare_config(self):
		config = ( '[system]\n'
                  f'flash_path = {self.flash_path}\n'
                  f'bootrom_path = {self.mcpx_path}\n'
                  f'hdd_path = {self.hdd_path}\n'
                   'shortanim = true\n'
                   '[misc]\n'
                   'check_for_update = false\n'
                  )
		log.info('Prepared config file:\n%s', config)
		with open('xemu.ini', 'w') as f:
			f.write(config)

	def launch_video_capture(self):
		log.info('Launching FFMPEG (capturing to %s)', self.video_capture_path)
		if platform.system() == 'Windows':
			c = ['ffmpeg.exe', '-loglevel', 'error', '-framerate', '60',
				'-video_size', f'{self.record_w}x{self.record_h}', '-f', 'gdigrab', '-offset_x', f'{self.record_x}', '-offset_y', f'{self.record_y}', '-i', 'desktop',
				'-c:v', 'libx264', '-pix_fmt', 'yuv420p',
				self.video_capture_path, '-y']
		else:
			c = ['ffmpeg', '-loglevel', 'error',
				 '-video_size', '640x480', '-f', 'x11grab', '-i', os.getenv("DISPLAY"),
				 '-c:v', 'libx264', '-preset', 'fast', '-profile:v', 'baseline', '-pix_fmt', 'yuv420p',
				 self.video_capture_path, '-y']
		self.ffmpeg = subprocess.Popen(c, stdin=subprocess.PIPE)

	def terminate_video_capture(self):
		log.info('Shutting down FFMPEG')
		self.ffmpeg.communicate(b'q\n', timeout=5)

	def launch_xemu(self):
		log.info('Launching xemu...')

		if platform.system() == 'Windows':
			c = [self.xemu_path, '-config_path', './xemu.ini', '-dvd_path', self.iso_path]
		else:
			c = [self.xemu_path, '-config_path', './xemu.ini', '-dvd_path', self.iso_path, '-full-screen']
		start = time.time()
		xemu = subprocess.Popen(c)

		if platform.system() == 'Windows':
			self.app = pywinauto.application.Application()
			self.app.connect(process=xemu.pid)
			main_window = self.app.window(title_re=r'^xemu \| v.+')
			if main_window is None:
				raise Exception('Failed to find main xemu window...')

			target_width = 640
			target_height = 480

			rect = main_window.client_area_rect()
			cx, cy, cw, ch = rect.left, rect.top, rect.width(), rect.height()
			rect = main_window.rectangle()
			x, y, w, h = rect.left, rect.top, rect.width(), rect.height()

			main_window.move_window(0, 0,
				                    target_width + (w-cw),
				                    target_height + (h-ch))
			rect = main_window.client_area_rect()
			x, y, w, h = rect.left, rect.top, rect.width(), rect.height()
			log.info('xemu window is at %d,%d w=%d,h=%d', x, y, w, h)
			self.record_x = x
			self.record_y = y
			self.record_w = w
			self.record_h = h

		self.launch_video_capture()

		while True:
			status = xemu.poll()
			if status is not None:
				log.info('xemu exited %d', status)
				break
			now = time.time()
			if (now - start) > self.timeout:
				log.info('Timeout exceeded. Terminating.')
				xemu.kill()
				xemu.wait()
				break
			time.sleep(1)

		self.terminate_video_capture()

	def mount_hdd(self):
		log.info('Mounting HDD image')
		if os.path.exists(self.mount_path):
			shutil.rmtree(self.mount_path)
		os.makedirs(self.mount_path, exist_ok=True)

		# FIXME: Don't need to run here
		subprocess.run([sys.executable, '-m', 'pyfatx', '-x', self.hdd_path], check=True, cwd=self.mount_path)

	def copy_results(self):
		log.info('Copying test results...')
		shutil.copytree(self.results_in_path, self.results_out_path, dirs_exist_ok=True)

	def unmount_hdd(self):
		log.info('Unmounting HDD image')
		# Nothing to do

	def analyze_results(self):
		with open(os.path.join(self.results_out_path, 'results.txt')) as f:
			assert(f.read().strip() == 'Success')

	def run(self):
		os.makedirs(self.results_out_path, exist_ok=True)
		self.prepare_roms()
		self.prepare_hdd()
		self.prepare_config()
		self.launch_xemu()
		self.mount_hdd()
		self.copy_results()
		self.unmount_hdd()
		self.analyze_results()

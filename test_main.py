#!/usr/bin/env python3

import subprocess
import shutil
import logging
import os
import signal
import time

logging.basicConfig(level=logging.INFO)
_l = logging.getLogger(__file__)

class Test:
	def __init__(self):
		self.flash_path         = '/work/private/bios.bin'
		self.mcpx_path          = '/work/private/mcpx.bin'
		self.blank_hdd_path     = '/work/xbox_hdd.qcow2'
		self.hdd_path           = '/tmp/test.img'
		self.mount_path         = '/tmp/xemu-hdd-mount'
		self.iso_path           = '/work/test-xbe/tester.iso'
		self.results_in_path    = os.path.join(self.mount_path, 'results')
		self.results_out_path   = '/work/results'
		self.video_capture_path = os.path.join(self.results_out_path, 'capture.mp4')
		self.timeout            = 60

	def prepare_roms(self):
		_l.info('Preparing ROM images')
		# TODO

	def prepare_hdd(self):
		_l.info('Preparing HDD image')
		subprocess.run(f'qemu-img convert {self.blank_hdd_path} {self.hdd_path}'.split(), check=True)

	def prepare_config(self):
		config = ('[system]\n'
                  f'flash_path = {self.flash_path}\n'
                  f'bootrom_path = {self.mcpx_path}\n'
                  f'hdd_path = {self.hdd_path}\n'
                  'shortanim = true\n'
                  )
		_l.info('Prepared config file:\n%s', config)
		with open('xemu.ini', 'w') as f:
			f.write(config)

	def launch_ffmpeg(self):
		_l.info('Launching FFMPEG (capturing to %s)', self.video_capture_path)
		c = ('/usr/bin/ffmpeg -loglevel error '
			 f'-video_size 640x480 -f x11grab -i {os.getenv("DISPLAY")} '
			 f'-c:v libx264 -preset fast -profile:v baseline -pix_fmt yuv420p '
			 f'{self.video_capture_path} -y')
		self.ffmpeg = subprocess.Popen(c.split())

	def terminate_ffmpeg(self):
		_l.info('Shutting down FFMPEG')
		self.ffmpeg.send_signal(signal.SIGINT)
		for _ in range(10):
			self.ffmpeg.poll()
			if self.ffmpeg.returncode is not None:
				_l.info('FFMPEG exited %d', self.ffmpeg.returncode)
				break
			time.sleep(0.1)
		self.ffmpeg.poll()
		if self.ffmpeg.returncode is None:
			_l.warning('Terminating FFMPEG')
			self.ffmpeg.terminate()

	def launch_xemu(self):
		_l.info('Launching xemu...')
		c = (f'timeout {self.timeout} '
			 f'xemu -config_path ./xemu.ini -dvd_path {self.iso_path} '
			 '-full-screen')
		subprocess.run(c.split())

	def mount_hdd(self):
		_l.info('Mounting HDD image')
		os.makedirs(self.mount_path, exist_ok=True)
		subprocess.run(f'fatxfs {self.hdd_path} {self.mount_path}'.split(), check=True)

	def copy_results(self):
		_l.info('Copying test results...')
		shutil.copytree(self.results_in_path, self.results_out_path, dirs_exist_ok=True)

	def unmount_hdd(self):
		_l.info('Unmounting HDD image')
		subprocess.run(f'fusermount -u {self.mount_path}'.split())

	def analyze_results(self):
		with open(os.path.join(self.results_out_path, 'results.txt')) as f:
			assert(f.read().strip() == 'Success')

	def run(self):
		os.makedirs(self.results_out_path, exist_ok=True)
		self.prepare_roms()
		self.prepare_hdd()
		self.prepare_config()
		self.launch_ffmpeg()
		self.launch_xemu()
		self.terminate_ffmpeg()
		self.mount_hdd()
		self.copy_results()
		self.unmount_hdd()
		self.analyze_results()

def main():
	test = Test()
	test.run()

if __name__ == '__main__':
	main()

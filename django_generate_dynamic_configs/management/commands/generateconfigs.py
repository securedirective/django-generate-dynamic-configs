import os
import sys
import pwd
import grp
from django.conf import settings
from django.template import Context, Template
from django.core.management.base import BaseCommand

class Command(BaseCommand):
	help = "Generate configuration files dynamically from templates using Django's settings as template context. To use, create a definition file with a list of output_file=template_file lines. Each template file and the definition file itself will be run through Django's template engine. Optionally, add DYNCONF_DEF_FILE to your settings file to specify the full path to the definition file (defaults to '{CONF_DIR}/dynamic_configs.conf')."

	def _get_default_context(self):
		# Context that all templates will receive
		uid = os.getuid()
		gid = os.getgid()
		return Context({
			'settings': settings,
			'venv': os.environ['VIRTUAL_ENV'],
			'username': pwd.getpwuid(uid).pw_name,
			'uid': uid,
			'groupname': grp.getgrgid(gid).gr_name,
			'gid': gid,
		})


	def _generate_config_file(self, output_file, template_file, context):
		# If the filenames are not already absolute paths, assume the default directory
		if not os.path.isabs(output_file):
			output_file = os.path.join(self.default_dir, output_file)
		if not os.path.isabs(template_file):
			template_file = os.path.join(self.default_dir, template_file)

		# Load the template file
		with open(template_file, 'r') as file:
			contents = file.read()
		self.stdout.write("Loaded template: {}".format(template_file))

		# Render the template
		output = Template(contents).render(context)

		# Load existing output file if it exists
		existing_output = None
		try:
			with open(output_file, 'r') as file:
				existing_output = file.read()
		except:
			pass

		# Render the new output file, but only write it to disk if it has changed
		if output != existing_output:
			with open(output_file, 'w') as file:
				file.write(output)
			self.stdout.write("    Updated: {}".format(output_file))
		else:
			self.stdout.write("    No change: {}".format(output_file))


	def handle(self, *args, **options):
		# Find the definitions file
		try:
			definition_file = settings.DYNCONF_DEF_FILE
		except:
			# If not found, choose a default
			definition_file = os.path.join(settings.CONF_DIR, 'dynamic_configs.conf')

		# Choose a default directory, in case an entry in the definitions is a relative path
		self.default_dir = os.path.dirname(os.path.abspath(definition_file))

		# Get the context that will be given to all templates
		context = self._get_default_context();

		# Load the definitions and process them through the template engine
		with open(definition_file, 'r') as file:
			contents = file.read()
		output = Template(contents).render(context)
		self.stdout.write("Loaded definition file: {}".format(definition_file))

		# Loop through each line
		lines = output.split("\n")
		num_configs = 0
		for line in lines:
			# Skip any that aren't key=value format
			line = line.strip()
			if line.startswith('#') or len(line) == 0:
				continue
			parts = line.split('=')
			if len(parts) != 2:
				continue
			self._generate_config_file(parts[0].strip(), parts[1].strip(), context)
			num_configs += 1

		if num_configs==0:
			self.stderr.write("No dynamic configs defined")
